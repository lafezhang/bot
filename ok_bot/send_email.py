
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import json
import threading
import traceback

account_qq = {"userName":"451618645@qq.com", "pwd":"romerbnnmhazbiae", "host":"smtp.qq.com"}
account_163 = {"userName":"lafezhang@163.com", "pwd":"zhang1987", "host":"smtp.163.com"}

try_accounts = [account_qq, account_163]

def SendEmailWithAccount(subject, message, sender_account):
    try:
        message = message.replace('\n','<br/>')
        msg = MIMEText(message, 'html', 'utf-8')
        msg['Content-Type'] = 'Text/HTML'
        msg['Subject'] = Header(subject, 'utf-8')
        msg['To'] = "zhang"
        msg['From'] = sender_account['userName']
        smtp = smtplib.SMTP_SSL(sender_account['host'], 465)
        smtp.login(sender_account['userName'], sender_account["pwd"])
        with open('email_cfg.json') as d:
            cfg = json.load(d)
            recievers = cfg["email_recievers"]

        smtp.sendmail(sender_account['userName'], recievers, msg.as_string())
        smtp.close()
        return True
    except Exception as e:
        print(e)

    return False



def SendEmail(subject, message):

    temp_accounts = try_accounts[0:]
    for account in temp_accounts:
        if SendEmailWithAccount(subject, message, account):
            return
        else:
            try_accounts.append(try_accounts[0])
            try_accounts.pop(0)






