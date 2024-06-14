from src import notion_api
from src.slack_api import SlackAPI
from src.logger import get_logger
from config import ENV
from datetime import datetime as dt
from datetime import timedelta


def run(start_date, end_date):
    logger = get_logger("daily_schedule_report")
    logger.info(f"=====START DAILY REPORT SCRAPE=====")

    notion_properties = notion_api.get_notion_properties_by_date(start_date, end_date, NOTION_API_HEADERS, NOTION_DATABASE_ID)
    subject, prompt = slack_daliy_schedule_report_bot.search_event_result_alarm_prompt(notion_properties)
    slack_daliy_schedule_report_bot.slack_alarm_bot(subject, prompt)

    logger.info(f"일일 리포트 슬랙 전송 완료 -> {subject}")


if __name__ == "__main__":
    NOTION_API_KEY = ENV["NOTION_API_KEY"]
    NOTION_DATABASE_ID = ENV["NOTION_DATABASE_ID"]
    NOTION_API_HEADERS = {"Authorization": "Bearer " + NOTION_API_KEY, "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

    # 봇 생성
    slack_daliy_schedule_report_bot = SlackAPI(ENV["SLACK_TODAY_CHANNEL_ID"], ENV["SLACK_BOT_TOKEN"])

    # 오늘 날짜를 기준으로 오늘 ~ 내일을 스크랩 범위로 설정
    today = dt.now()
    start_date = today.strftime("%Y-%m-%d")
    end_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")

    run(start_date, end_date)
