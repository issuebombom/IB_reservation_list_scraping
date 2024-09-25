from src import scraper, notion_api
from src.logger import get_logger
from src.slack_api import SlackAPI
from config import ENV
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
from tqdm import tqdm

# Wings 스케줄 수집 후 Notion 데이터베이스에 추가 및 업데이트
def run(start_date: int, end_date: int):

    logger = get_logger('main')

    # 슬랙 알람으로 전달할 변동사항을 담는다
    alarm_properties = {'changed': [], 'new': []}
    
    logger.info("=====START SCRAPE=====")
    # 스케줄 수집
    results = []
    for i in range(start_date, end_date + 1):
        result = scraper.get_schedule(GW_SCHEDULE_URL, GW_SCHEDULE_REFERER, SESSION_ID, i)
        results += result['rows']
    
    logger.info(f"총 수집된 스케줄의 개수: {len(results)}")

    # 데이터베이스 추가
    for row in tqdm(results, ncols=80, miniters=len(results) * 0.2): # 20% 단위로 표시
        values = {}
    
        # time 전처리
        start_time, end_time = row['EVENT_TIME'].split(sep='~')

        start_time_dt = dt.strptime(row['EVENT_DATE'] + start_time.replace(':', ''), '%Y%m%d%H%M')
        end_time_dt = dt.strptime(row['EVENT_DATE'] + end_time.replace(':', ''), '%Y%m%d%H%M')
        
        if start_time_dt < dt.now(): continue
        # test용: if start_time_dt < dt.strptime('2024-08-25', '%Y-%m-%d'): continue

        # exmaple) "2020-12-08T12:00:00Z"
        start_time = start_time_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time = end_time_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    
        values['event_name'] = row['FNC_NAME_ORG']
        values['start_time'] = start_time
        values['end_time'] =  end_time
        values['place'] = row['FNC_ROOM_NAME']
        values['type'] = row['FNC_TYPE_NAME'] # '결혼', '기타'...
        values['status'] = row['FNC_STATUS_CODE'] # 'ACT', '...'
        values['manager'] = row['SALE_MANAGER'] # sale manager
        values['event_number'] = int(row['EVENT_NO']) # 행사 번호 -> 고유ID로 활용
        values['reference'] = [''] # 참조 수집 전 init
        
        if values['status'] != 'CXL': # 취소된 행사는 참조사항에 접근 불가함
            values['reference'] = scraper.get_reference_preview(row['FNC_NAME_ORG'], int(row['FNC_RSVN_NO']), int(row['EVENT_NO']), GW_REFERENCE_URL, SESSION_ID)

        # 행사 번호를 통해 이미 노션에 등록 유무를 확인
        notion_properties = notion_api.get_notion_properties_by_event_id(values['event_number'], NOTION_API_HEADERS, NOTION_DATABASE_ID)
        
        # 노션에 이미 등재된 경우 업데이트
        if notion_properties:
            notion_api.notion_update_page(notion_properties['page_id'], NOTION_API_HEADERS, values)

            # 프로퍼티값에 변경점이 있다면 알림 발생
            changed_properties = []

            # 각 프로퍼티를 대조
            for prop_name in ['event_name', 'start_time', 'end_time', 'place', 'status', 'manager', 'reference']:
                
                previous_value = notion_properties[prop_name]
                updated_value = values[prop_name]
                
                if previous_value != updated_value:
                    changed_properties.append(
                        {
                            'item': prop_name, 
                            'previous_value': previous_value, 
                            'updated_value': updated_value
                        }
                    )

            # 변경점이 있다면 기록에 남김
            if changed_properties:
                alarm_properties['changed'].append(
                    {
                        'event_number': notion_properties['event_number'],
                        'event_name': values['event_name'],
                        'start_time': values['start_time'],
                        'place': values['place'],
                        'changed_properties': changed_properties,
                    }
                )

        else:
            # 데이터베이스에 신규 page 생성
            notion_api.notion_create_page(NOTION_DATABASE_ID, NOTION_API_HEADERS, values)

            # 신규 생성 내역 기록
            alarm_properties['new'].append(
                {
                    'event_number': values['event_number'],
                    'event_name': values['event_name'],
                    'place': values['place'],
                    'start_time': values['start_time'],
                    'end_time': values['end_time'],
                    'manager': values['manager'],
                    'reference': values['reference']
                }
            )

    logger.info(f"노션 데이터베이스 업데이트 완료")

    # 작업 완료 알림 전송
    subject = f'총 {len(results)}개의 스케줄이 업데이트 되었습니다.'
    prompt = f'수집 범위: {start_date}-{end_date}\n신규 등록된 행사: {len(alarm_properties['new'])}건\n내용 변경된 행사: {len(alarm_properties['changed'])}건'
    slack_log_bot.slack_alarm_bot(subject, prompt)

    logger.info("슬랙 로그 알람 전송 완료")

    # 슬랙 알림 전송
    # 변경사항 유무에 따른 알림 전송
    if alarm_properties['changed']:
        # 시간 오름차순 정렬
        sorted_changed = sorted(alarm_properties['changed'], key=lambda x: dt.strptime(x['start_time'], "%Y-%m-%dT%H:%M:%SZ"))
        subject, prompt = slack_schedule_bot.changed_alarm_prompt(sorted_changed)
        slack_schedule_bot.slack_alarm_bot(subject, prompt)
        
    # 신규 생성 내역 알림 전송
    if alarm_properties['new']:
        # 시간 오름차순 정렬
        sorted_new = sorted(alarm_properties['new'], key=lambda x: dt.strptime(x['start_time'], "%Y-%m-%dT%H:%M:%SZ"))
        subject, prompt = slack_schedule_bot.created_alarm_prompt(sorted_new)
        slack_schedule_bot.slack_alarm_bot(subject, prompt)

    logger.info("=====FINISHED SCRAPE=====")

if __name__ == "__main__":
    # 로그인 후 쿠키에서 세션ID 획득
    driver = scraper.gw_login(ENV["GW_TARGET_URL"], ENV['GW_COMPANY_ID'], 
                                  ENV['GW_USER_ID'], ENV['GW_USER_PW'])
    cookies = scraper.get_cookies(driver, quit=True)

    GW_SCHEDULE_URL = ENV["GW_SCHEDULE_URL"]
    GW_REFERENCE_URL = ENV["GW_REFERENCE_URL"]
    GW_SCHEDULE_REFERER = ENV["GW_SCHEDULE_REFERER"]

    SESSION_ID = cookies['JSESSIONID'] # update 필요
    NOTION_API_KEY = ENV['NOTION_API_KEY']
    NOTION_DATABASE_ID = ENV['NOTION_DATABASE_ID']

    NOTION_API_HEADERS = {
        "Authorization": "Bearer " + NOTION_API_KEY,
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    slack_schedule_bot = SlackAPI(ENV['SLACK_SCHEADULE_CHANNEL_ID'], ENV['SLACK_BOT_TOKEN'])
    slack_log_bot = SlackAPI(ENV['SLACK_LOG_CHANNEL_ID'], ENV['SLACK_BOT_TOKEN'])

    # 오늘 날짜를 기준으로 현재 달 ~ 다음 달을 스크랩 범위로 설정
    today = dt.now()
    start_date = int(today.strftime('%Y%m'))
    end_date = int((today + relativedelta(months=1)).strftime('%Y%m'))

    run(start_date, end_date)
