from src import logger
import requests
import json
import textwrap


# Notion API가 요구하는 JSON 형태를 만듭니다.
def set_properties(page_values):
    page = {
        "이름": {"title": [{"text": {"content": page_values["event_name"]}}]},
        "날짜": {
            "date": {
                "start": page_values["start_time"],
                "end": page_values["end_time"],
                "time_zone": "Asia/Seoul",
            }
        },
        "장소": {"select": {"name": page_values["place"]}},
        "예약상태": {"select": {"name": page_values["status"]}},
        "행사타입": {"select": {"name": page_values["type"]}},
        "매니저": {"select": {"name": page_values["manager"]}},
        "행사번호": {"number": page_values["event_number"]},
    }

    # 참조사항이 있는 경우 추가
    if page_values["reference"]:
        page["특이사항"] = {"rich_text": None}

        # rich text 추가
        page["특이사항"]["rich_text"] = [{"type": "text", "text": {"content": text, "link": None}} for text in page_values["reference"]]

    return page


# 행사 ID로 조회 후 결과가 있을 경우 ID를 리턴 / 없으면 False를 리턴
@logger.wrapped_logging
def get_notion_properties_by_event_id(event_id, headers, database_id):
    query_url = f"https://api.notion.com/v1/databases/{database_id}/query"

    query = {
        "filter": {
            "and": [
                {
                    "property": "행사번호",
                    "number": {
                        "equals": event_id,
                    },
                }
            ]
        }
    }

    data = json.dumps(query)
    res = requests.post(query_url, headers=headers, data=data)
    res.raise_for_status()

    results = res.json()["results"]

    # 값이 있다면
    notion_properties = {}
    if results:
        notion_properties = {
            "page_id": results[0]["id"],
            "event_number": results[0]["properties"]["행사번호"]["number"],
            "event_name": results[0]["properties"]["이름"]["title"][0]["plain_text"],
            "start_time": results[0]["properties"]["날짜"]["date"]["start"].split(".")[0] + "Z",  # '2024-06-10T18:00:00Z'
            "end_time": results[0]["properties"]["날짜"]["date"]["end"].split(".")[0] + "Z",  # '2024-06-10T18:00:00Z'
            "place": results[0]["properties"]["장소"]["select"]["name"],
            "status": results[0]["properties"]["예약상태"]["select"]["name"],
            "manager": results[0]["properties"]["매니저"]["select"]["name"],
            "reference": [obj["plain_text"] for obj in results[0]["properties"]["특이사항"]["rich_text"]],  # list
        }

        return notion_properties

    return False


# 신규 페이지 생성
@logger.wrapped_logging
def notion_create_page(database_id, headers, page_values):

    create_url = "https://api.notion.com/v1/pages"

    new_page = {
        "parent": {"database_id": database_id},
        "properties": set_properties(page_values),
    }

    data = json.dumps(new_page)
    res = requests.post(create_url, headers=headers, data=data)
    res.raise_for_status()
    # print(res, f"[New] 페이지 생성 완료 - {page_values['event_name']} | {page_values['start_time']}")


# 특정 페이지를 업데이트
@logger.wrapped_logging
def notion_update_page(page_id, headers, page_values):

    update_url = f"https://api.notion.com/v1/pages/{page_id}"

    update_page = {"properties": set_properties(page_values)}

    data = json.dumps(update_page)
    res = requests.patch(update_url, headers=headers, data=data)
    res.raise_for_status()
    # print(res, f"페이지 업데이트 완료")


# 날짜를 기준으로 행사를 조회하는 쿼리
def get_notion_properties_by_date(start_date, end_date, headers, database_id):

    query_url = f"https://api.notion.com/v1/databases/{database_id}/query"

    query = {
        "filter": {
            "and": [
                {
                    "property": "날짜",
                    "date": {"on_or_after": start_date, "time_zone": "Asia/Seoul"},
                },
                {
                    "property": "날짜",
                    "date": {"on_or_before": end_date, "time_zone": "Asia/Seoul"},
                },
                {"property": "예약상태", "select": {"does_not_equal": "CXL"}},
                {"property": "상태", "formula": {"string": {"does_not_equal": "종료"}}},
            ]
        },
        "sorts": [{"property": "날짜", "direction": "ascending"}],
    }

    data = json.dumps(query)
    res = requests.post(query_url, headers=headers, data=data)
    res.raise_for_status()

    results = res.json()["results"]

    # 값이 있다면
    notion_properties = {
        "search_start_date": start_date,  # str 검색날짜(시작)
        "search_end_date": end_date,  # str 검색날짜(끝)
        "properties": [],
    }
    if results:
        for result in results:
            notion_properties["properties"].append(
                {
                    "start_search_date": start_date,  # str 검색날짜(시작)
                    "end_search_date": end_date,  # str 검색날짜(끝)
                    "event_number": result["properties"]["행사번호"]["number"],
                    "event_name": result["properties"]["이름"]["title"][0]["plain_text"],
                    "start_time": result["properties"]["날짜"]["date"]["start"].split(".")[0] + "Z",  # '2024-06-10T18:00:00Z'
                    "end_time": result["properties"]["날짜"]["date"]["end"].split(".")[0] + "Z",  # '2024-06-10T18:00:00Z'
                    "place": result["properties"]["장소"]["select"]["name"],
                    "status": result["properties"]["상태"]["formula"]["string"],  # '일주일 내', '오늘', '내일'
                    "manager": result["properties"]["매니저"]["select"]["name"],
                    "reference": textwrap.shorten(
                        " ".join([obj["plain_text"] for obj in result["properties"]["특이사항"]["rich_text"]]), width=50, placeholder="...(생략)"
                    ),  # list
                    "notion_public_link": result["public_url"],
                }
            )

    return notion_properties  # list
