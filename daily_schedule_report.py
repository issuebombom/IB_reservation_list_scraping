from src import notion_api
from src import scraper
from src.slack_api import SlackAPI
from src.logger import get_logger
from config import ENV
from datetime import datetime as dt
from datetime import timedelta


def run(start_date, end_date, driver):
    logger = get_logger("daily_schedule_report")
    logger.info(f"=====START DAILY REPORT SCRAPE=====")

    # 스케줄 스크린샷 생성 (보류)
    # screenshot_file_path = f'./screenshot/schedule_screenshot_{start_date[:7]}.png'
    # scraper.get_schedule_screenshot(driver, screenshot_file_path, quit=True)

    notion_properties = notion_api.get_notion_properties_by_date(start_date, end_date, NOTION_API_HEADERS, NOTION_DATA_SOURCE_ID)
    subject, prompt = slack_daliy_schedule_report_bot.search_event_result_alarm_prompt(notion_properties)
    slack_daliy_schedule_report_bot.slack_alarm_bot(subject, prompt)

    logger.info(f"일일 리포트 슬랙 전송 완료 -> {subject}")


if __name__ == "__main__":
    NOTION_API_KEY = ENV["NOTION_API_KEY"]
    NOTION_DATABASE_ID = ENV["NOTION_DATABASE_ID"]
    NOTION_DATA_SOURCE_ID = ENV["NOTION_DATA_SOURCE_ID"]
    NOTION_API_VERSION = ENV["NOTION_API_VERSION"]
    NOTION_API_HEADERS = {
        "Authorization": "Bearer " + NOTION_API_KEY,
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }

    # 봇 생성
    slack_daliy_schedule_report_bot = SlackAPI(ENV["SLACK_TODAY_CHANNEL_ID"], ENV["SLACK_BOT_TOKEN"])

    # driver 획득
    driver = scraper.gw_login(ENV["GW_TARGET_URL"], ENV["GW_COMPANY_ID"], ENV["GW_USER_ID"], ENV["GW_USER_PW"])
    # 오늘 날짜를 기준으로 오늘 ~ 내일을 스크랩 범위로 설정
    today = dt.now()
    start_date = today.strftime("%Y-%m-%d")
    end_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    run(start_date, end_date, driver)
