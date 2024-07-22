from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from src import logger
from datetime import datetime as dt
import time
import requests
import json


def gw_login(wings_target_url, company_id, user_id, password):

    # Chrome WebDriver 경로 설정 (적절한 경로로 변경하세요)
    # chrome_driver_path = '/path/to/chromedriver'

    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 브라우저를 표시하지 않음
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("window-size=1920,1080")

    # WebDriver 서비스 설정

    # NOTE: chromedriver 설치를 x86환경에서 arm64 아키텍처로 자동설치하는 문제 발생
    # service = Service(ChromeDriverManager().install())
    service = ChromeService(ChromeDriverManager().install())

    # WebDriver 객체 생성
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # 웹사이트 열기
    driver.get(wings_target_url)  # 로그인 페이지 URL로 변경하세요

    # 로그인 폼에 데이터 입력
    company_input = driver.find_element(By.ID, "company")  # 올바른 필드 이름으로 변경하세요
    username_input = driver.find_element(By.ID, "username")  # 올바른 필드 이름으로 변경하세요
    password_input = driver.find_element(By.NAME, "userpw")  # 올바른 필드 이름으로 변경하세요

    company_input.send_keys(company_id)
    username_input.send_keys(user_id)  # 사용자 이름 입력
    password_input.send_keys(password)  # 비밀번호 입력
    password_input.send_keys(Keys.RETURN)  # 로그인 제출

    # 로그인 처리를 기다림 (적절한 방법으로 대기 시간을 설정하거나 조건을 설정하세요)
    time.sleep(5)  # 예시로 5초 대기

    return driver

def get_cookies(driver: WebDriver, quit: bool=False):
    # 쿠키 가져오기
    cookies = driver.get_cookies()
    cookies_dict = {}
    for cookie in cookies:
        cookies_dict[cookie["name"]] = cookie["value"]
        # print(f"Name: {cookie['name']}, Value: {cookie['value']}")

    # WebDriver 종료
    if quit:
        driver.quit()

    return cookies_dict


@logger.wrapped_logging
def get_schedule(session_id, search_date):
    URL = "https://wingspms.sanhait.com/pms/biz/sc03_2100_V50/searchListMonthlyEventSchedule.do"

    headers = {
        "referer": "https://wingspms.sanhait.com/pms",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }

    # 쿠키에서 SID 획득
    cookies = {"JSESSIONID": session_id, "WMONID": "mTAbNtSvVLH"}

    data = {
        "BSNS_CODE": 11,
        "STD_DATE": search_date,
        "CHK_OPT": "'QTN', 'WAT', 'TEN', 'DEF', 'ACT', 'CXL'",  # TEN: 가계약, DEF: 확정예약, ACT: 종료
    }
    res = requests.post(URL, headers=headers, data=data, cookies=cookies)
    res.raise_for_status()

    schedules = json.loads(res.text)
    return schedules


# 각 행사의 참조사항을 가져온다.
@logger.wrapped_logging
def get_reference_preview(fnc_name_org, fnc_rsvn_no, event_no, session_id):
    REFERENCE_URL = "https://wingspms.sanhait.com/pms/biz/sc02_0403/searchReservationReferencePreview.do"

    headers = {
        "referer": "https://wingspms.sanhait.com/pms",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }

    cookies = {
        "JSESSIONID": session_id,
    }

    data = {
        "BSNS_CODE": 11,  # 11 고정인 듯
        "FNC_RSVN_NO": fnc_rsvn_no,
        "EVENT_NO": event_no,
    }

    # NOTE: 예약상태가 CXL 되면 참조사항 접근 불가 처리됨
    res = requests.post(REFERENCE_URL, headers=headers, data=data, cookies=cookies)
    res.raise_for_status()  # ok가 아닐 경우 raise -> wrapped_logging으로 이동
    preview = json.loads(res.text)

    # 참조등록 정보 가져오기 (빈 값일 경우 [''] 출력)
    if preview["rows"]:
        return [row["TEXT"].strip() + "\n" for row in preview["rows"]]
    else:
        return [""]

def get_schedule_screenshot(driver: WebDriver, file_path: str, quit: bool=True):
    """로그인 후 스케줄 스크린샷
    """
    # 별표 클릭
    driver.find_element(By.ID, "btnCat").click()
    time.sleep(0.5)

    # 연회 달력 클릭
    driver.find_element(By.CSS_SELECTOR, "#treeView1 > li > ul > li:nth-child(2) > span.m_txt").click()
    time.sleep(0.5)

    # iframe 전환
    iframe = driver.find_element(By.CSS_SELECTOR, 'iframe')
    driver.switch_to.frame(iframe)

    # ALL 클릭
    driver.find_element(By.ID, "frmS_All").click()

    # CXL 클릭(제외)
    driver.find_element(By.ID, "frmS_Cxl").click()

    # 오늘 날짜 시간 출력
    today = str(dt.now()).split()[0] # ex. 2024-07-12

    # 조회 날짜 선택
    script = f'document.getElementById("frmS_datePic").value = "{today[:7]}";'
    driver.execute_script(script)

    # 조회 버튼 클릭
    driver.find_element(By.ID, "comm_btn_find").click()
    time.sleep(1)

    # 크롬창 최대화
    driver.maximize_window()
    time.sleep(1)

    # 최하단으로 스크롤 (최하단에 위치한 태그를 지정해서 해당 태그가 보이도록 스크롤하는 방식
    low_element = driver.find_elements(By.CLASS_NAME, 'mv_row_container')[-1]
    # 해당 요소로 스크롤하기
    driver.execute_script("arguments[0].scrollIntoView(true);", low_element)

    # 스크린샷 캡처
    driver.save_screenshot(file_path)
    time.sleep(0.5)

    if quit:
        # 브라우저 닫기
        driver.quit()
