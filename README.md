# Event schedule scrape & alert

행사 스케줄을 수집하여 데이터베이스에 저장 후 시각적으로 필요한 정보를 빠르게 파악할 수 있도록 구성하고, 오늘의 행사, 변동사항 등 필요한 정보를 정기적으로 알림을 받도록 하기위해 제작한 도구입니다.

## 목적

1. 자사에서 사용하는 행사 예약 관리 페이지의 UI적 한계점을 보완하여 주요 행사 정보를 보기 쉽게 정리하기 위함
2. 오늘의 행사 및 행사의 변동 사항 등 주요 정보를 알림 기능을 적용하여 사전에 파악하고, 이에 대응하기 위함

## 프로세스

### 관리 페이지에 등록된 월별 행사 정보를 획득

> - 로그인 후 세션 ID 획득
> - 행사 정보 POST Requests
> - 수집 데이터 전처리

### Notion API를 활용하여 데이터베이스 형태로 저장

> - 이전 저장 데이터와 수집 데이터 간 비교
> - API에서 요구하는 body 형식 적용
> - 신규 등록 정보일 경우 노션 데이터베이스 저장
> - 변경 사항 있을 경우 update
>   <img width="465" alt="스크린샷 2024-07-06 오후 2 32 14" src="https://github.com/issuebombom/IB_reservation_list_scraping/assets/79882498/30c6e2b6-fd77-4a33-bac3-253318475b01">

### Slack API를 활용하여 필요한 정보를 알림 받음 (행사, 로그 관련)

> - 신규 등록 정보 및 변경 사항 수집 및 슬랙 API로 메시지 생성 및 전송
> - contab으로 스케줄 실행
>   <img width="1175" alt="스크린샷 2024-07-06 오후 2 31 49" src="https://github.com/issuebombom/IB_reservation_list_scraping/assets/79882498/7f8bfc40-ec78-4549-8748-0fae2110680a">

### 로깅

> - 각 API 요청에 대한 에러 발생 시 로깅
> - 아래 함수를 각 API 요청 함수에 데코레이터로 적용
> - 에러 내용을 슬랙 알림으로 전송

```python
def wrapped_logging(func):
    def wrapper(*args):
        logger = get_logger(name=func.__name__)
        identifier = args[0]

        try:
            return func(*args)

        except Exception as e:
            message = f"{identifier} | {type(e).__name__} | {e} |\ntraceback:\n{"".join(traceback.format_tb(e.__traceback__))}"
            logger.info(message)

            # 슬랙 알림봇 전달
            subject = f'{type(e).__name__}가 발생했습니다.'
            slack_log_bot.slack_alarm_bot(subject, message)

            return False

    return wrapper
```

### 슬랙 API 양식 작성
> - 일반 문자열 방식으로 아래 형식과 같이 작성 시 코드 상에서 적용한 줄바꿈 및 탭 간격이 그대로 반영됨
> - textwrap 모듈을 사용하면 아래와 같이 문자열을 작성할 때 가독성을 높일 수 있음
> - 실제 코드 상에서 보여지는 문자열 형태와 동일한 결과를 얻을 수 있음

```python
import textwrap

changed = textwrap.dedent(
                    f"""\
                        > {name_match[props['item']]}
                        > `변경 전`  {previous_value}
                        > `변경 후`  {updated_value}

                    """
                )
```
