from send_email import SendEmail

import logging
import logging.handlers
import Utils
import os

LOG_ROOT = "logs"

Utils.mkdir(LOG_ROOT)

@Utils.singleton
class MyLogger(object):

    def __init__(self):
        file_name = Utils.time_str() + ".log"
        log_file_name = os.path.join(LOG_ROOT, file_name)

        file_handler = logging.FileHandler(log_file_name)
        console_handler = logging.StreamHandler()

        fmt = '%(asctime)s - %(message)s'
        formatter = logging.Formatter(fmt)  # 实例化formatter
        file_handler.setFormatter(formatter)  # 为handler添加formatter
        console_handler.setFormatter(formatter)

        logger = logging.getLogger('tst')  # 获取名为tst的logger
        logger.addHandler(file_handler)  # 为logger添加handler
        logger.addHandler(console_handler)

        logger.setLevel(logging.DEBUG)
        self.logger = logger

    def log(self, msg):
        self.logger.info(msg)


myLogger = MyLogger()

queue = []

def push_log_and_email_msg(msg):
    global queue
    queue.append(msg)

def flush_msg():
    global queue
    messages = queue
    queue = []
    for msg in messages:
        myLogger.log(msg)
        SendEmail(msg, msg)

def log(msg):
    myLogger.log(msg)

def log_and_email(msg, title="提醒"):
    log(msg)
    SendEmail(title, msg)


