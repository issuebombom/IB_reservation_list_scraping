import logging
import traceback
import os
from config import ENV
from src.slack_api import SlackAPI

slack_log_bot = SlackAPI(ENV['SLACK_LOG_CHANNEL_ID'], ENV['SLACK_BOT_TOKEN'])

def get_logger(name, dir_='./log', stream=False):
    
    """log 데이터 파일 저장
    
    Args:
        name(str): 로그 이름 지정
        dir_(str): 로그 파일을 저장할 경로 지정
        stream(bool): 콘솔에 로그를 남길지에 대한 유무
    
    Returns: logging.RootLogger
        
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)  # logging all levels
    logger.handlers.clear() # 중복 입력 방지
    
    formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
    stream_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(os.path.join(dir_, f'{name}.log'))

    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    if stream:
        logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger


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
