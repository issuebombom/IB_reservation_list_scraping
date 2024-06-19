from config import ENV
from datetime import datetime as dt
import textwrap
import requests
import ast


class SlackAPI:

    def __init__(self, channel_id, token):
        self.channel_id = channel_id
        self.token = token

    def slack_alarm_bot(self, subject, contents):

        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": "Bearer " + self.token,
            "Content-type": "application/json",
        }
        message_form = self.__create_post_message_form(subject, contents)

        res = requests.post(url, headers=headers, json=message_form)
        res.raise_for_status()
        result = res.json()
        return result

        # try:
        #     res = requests.post(url, headers=headers, json=message_form)
        #     res.raise_for_status()
        #     result = res.json()
        #     return result

        # # contents가 슬랙 메시지 형식에 맞지 않아 에러가 발생할 수 있음
        # except requests.exceptions.RequestException as e:
        #     error_title = f"{type(e).__name__}가 발생했습니다."
        #     error_message = f"{subject} |\n {type(e).__name__} |\nmessage: {e} |\ntraceback:\n{"".join(traceback.format_tb(e.__traceback__))}"
        #     error_form = self.__create_post_message_form(error_title, error_message)
        #     requests.post(url, headers=headers, json=error_form)

    # 변경사항에 대한 알람 prompt
    def changed_alarm_prompt(self, contents):

        name_match = {
            "event_number": "행사번호",
            "event_name": ":bookmark:  행사명",
            "start_time": ":alarm_clock:  시작 날짜",
            "end_time": ":alarm_clock:  종료 날짜",
            "place": ":house:  장소",
            "status": ":white_check_mark:  예약 상태",
            "reference": ":notebook:  참조 사항",
        }

        subject = f":dizzy:  총 {len(contents)}건의 행사 정보가 변경되었습니다.\n"

        prompt = ""
        for content in contents:
            event_number = content["event_number"]  # 노출이 불필요해 보여 안쓰고 있음
            event_name = content["event_name"]
            place = content["place"]
            start_time = dt.strftime(
                dt.strptime(content["start_time"], "%Y-%m-%dT%H:%M:%SZ"),
                "%m/%d %a %H:%M",
            )

            title = textwrap.dedent(
                f"""\
                    _*{event_name}*_ [{start_time}] `{place}`
                """
            )

            concat = ""
            for props in content["changed_properties"]:
                previous_value = self.__replace_list_to_str(props["previous_value"])
                updated_value = self.__replace_list_to_str(props["updated_value"])

                changed = textwrap.dedent(
                    f"""\
                        > {name_match[props['item']]}
                        > `변경 전`  {previous_value}
                        > `변경 후`  {updated_value}

                    """
                )
                concat += changed
            prompt += title + concat

        return subject, prompt

    # 신규 일정 등록 사항에 대한 알람
    def created_alarm_prompt(self, contents):
        subject = f":pushpin:  총 {len(contents)}건의 새로운 행사가 등록되었습니다.\n"

        prompt = ""
        for content in contents:
            event_number = content["event_number"]  # 일단 제외
            event_name = content["event_name"]
            place = content["place"]
            start_time = dt.strftime(
                dt.strptime(content["start_time"], "%Y-%m-%dT%H:%M:%SZ"),
                "%m/%d %a %H:%M",
            )
            end_time = dt.strftime(
                dt.strptime(content["end_time"], "%Y-%m-%dT%H:%M:%SZ"),
                "%m/%d %a %H:%M",
            )
            manager = content["manager"]
            reference = self.__replace_list_to_str(content["reference"])  # list to str

            prompt += textwrap.dedent(
                f"""\
                    _*{event_name}*_ [{start_time}]
                    > 장소: {place}
                    > 행사날짜: 
                    > {start_time} ~ {end_time}
                    > 담당자: {manager}
                    > 참조사항: 
                    > {textwrap.shorten(reference, width=50, placeholder="...(생략)")}
                """
            )

        return subject, prompt

    def search_event_result_alarm_prompt(self, contents):
        search_start_date = dt.strftime(
            dt.strptime(contents["search_start_date"], "%Y-%m-%d"),
            "%m/%d (%a)",
        )
        search_end_date = dt.strftime(
            dt.strptime(contents["search_end_date"], "%Y-%m-%d"),
            "%m/%d (%a)",
        )
        # ex) 오늘의 행사 목록 [6/11 Wed - 6/12 Thu]
        subject = f":pushpin:  TODAY 행사 목록 ({len(contents['properties'])}건)\n{search_start_date} - {search_end_date}\n"
        prompt = ""
        for content in contents["properties"]:
            event_number = content["event_number"]  # 일단 제외
            event_name = content["event_name"]
            place = content["place"]
            manager = content["manager"]
            reference = content["reference"]  # str
            status = content["status"]  # 오늘, 내일, 일주일 후
            notion_public_link = content["notion_public_link"] 
            start_time = dt.strftime(
                dt.strptime(content["start_time"], "%Y-%m-%dT%H:%M:%SZ"),
                "%m/%d %a %H:%M",
            )
            end_time = dt.strftime(
                dt.strptime(content["end_time"], "%Y-%m-%dT%H:%M:%SZ"),
                "%m/%d %a %H:%M",
            )
            # NOTE: 상태 formula가 UTC 시간 때문에 문제가 있음 -> notion formula에서 -09:00 강제 설정으로 해결
            prompt += textwrap.dedent(
                f"""\
                    > {status} `{' '.join(start_time.split(' ')[:-1])}({start_time.split(' ')[-1]}~{end_time.split(' ')[-1]})`
                    > _*{event_name}*_
                    > {place} | {manager}
                    > {reference if reference else '참조사항 없음'}

                """
            )

        return subject, prompt

    def __create_post_message_form(self, subject, contents):
        message_form = {
            "channel": self.channel_id,
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": subject}},
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f":robot_face:  *Updated at* {dt.now()}",
                        }
                    ],
                },
                {"type": "divider"},
                {"type": "section", "text": {"type": "mrkdwn", "text": contents}},
                {"type": "divider"},
            ],
        }

        return message_form

    # 참조사항의 경우 리스트를 반환하므로 이를 문자열로 변환하기 위한 수단
    def __replace_list_to_str(self, value):
        if isinstance(value, list):
            value = "".join(value).replace("\n", " ")  # 슬랙에서 좀 더 깔끔하게 보이려면 \n 제거해야 함

        return "없음" if value == "" else value
