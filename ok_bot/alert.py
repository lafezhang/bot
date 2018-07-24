# -*- coding: utf-8 -*-
# author: 半熟的韭菜

from websocket import create_connection
import time
import threading
import os
import json
import sqlite3
import Notification
import argparse

import handlers as Handlers

parser = argparse.ArgumentParser(description='use -t= test folder -s= test symbol -c')
parser.add_argument('-t', type=str, default=None)
parser.add_argument('-s', type=str, default=None)
parser.add_argument('-capture', action='store_true', default=False)
args = parser.parse_args()

test_folder = args.t
test_symbol = args.s
capture_mode = args.capture

def mkdir(path):
    folder = os.path.exists(path)
    if not folder:  # 判断是否存在文件夹如果不存在则创建为文件夹
        os.makedirs(path)  # makedirs 创建文件时如果路径不存在会创建这个路径


def notify(message, ts):
    if test_folder:
        print("%s: %s" % (time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(ts)), message))
    else:
        Notification.log_and_email(message, message)


class PingThread(object):

    def __init__(self, ws):
        self.ws = ws

    def loop(self):
        try:
            while 1:
                self.ws.ping("{'event':'ping'}")
                time.sleep(25)
        except Exception as e:
            print(e)

        pass

    def start(self):
        t = threading.Thread(target=self.loop)
        t.start()

class MessageSource(object):

    def __init__(self, handlers):
        self.handlers = handlers


    def dispatch_deal_msg(self, msg, symbol, ts):
        for h in self.handlers:
            h.OnNewDeals(msg, symbol, ts)
    def dispatch_depth_msg(self, msg, symbol, ts):
        for h in self.handlers:
            h.OnNewDepth(msg, symbol, ts)


    def start(self, params):
        pass

class MessageSourceWebSocket(MessageSource):

    def start(self, params=None):
        while (1):
            try:
                ws = create_connection("wss://real.okex.com:10441/websocket")
                t = PingThread(ws)
                t.start()
                break
            except:
                Notification.log('connect ws error,retry...')
                time.sleep(5)

        symbols = set()
        for h in self.handlers:
            symbols = symbols.union(h.get_cfg_symbols_set())

        print("symbols", symbols)
        if capture_mode:
            self.handlers = [Handlers.CaptureHandler(notify)]

        for s in symbols:
            ws.send("""{'event':'addChannel','channel':'ok_sub_spot_%s_deals'}""" % s)
            ws.send("""{'event':'addChannel','channel':'ok_sub_spot_%s_depth'}""" % s)
        last_check_time = time.time()
        try:
            while (1):
                result = ws.recv()
                result_json = json.loads(result)
                t = time.time()
                if t - last_check_time > 30*60:
                    Notification.log("alive")
                    last_check_time = t

                for data in result_json:
                    if "channel" in data:
                        if data["channel"][-6:] == "_deals":
                            symbol = data["channel"][12:-6]
                            self.dispatch_deal_msg(data['data'], symbol, t)
                        elif data["channel"][-6:] == "_depth":
                            symbol = data["channel"][12:-6]
                            self.dispatch_depth_msg(data['data'], symbol, t)

            pass
        except Exception as e:
            Notification.log(e)

class MessageSourceDB(MessageSource):

    def start(self, params):
        db_file, symbol = params
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT *, strftime('%s',a.ts) as ts2 from message a")
        for row in cursor:
            message = json.loads(row[2])
            tp = row[1]
            ts = int(row[4])
            if tp == "deal":
                self.dispatch_deal_msg(message, symbol, ts)
            else:
                self.dispatch_depth_msg(message, symbol, ts)


def run_test(db_folder):
    for folder, dirs, files in os.walk(db_folder):
        for file in files:
            base_name, ext = os.path.splitext(file)
            if ext != ".db":
                continue
            if test_symbol and base_name != test_symbol:
                continue


            handlers = [ Handlers.VolumeAlertHandler(notify), Handlers.DepthDiffAlertHandler(notify), Handlers.HengpanAlertHandler(notify)]
            ss = MessageSourceDB(handlers)
            ss.start((os.path.join(folder, file), base_name))

    pass

def run():
    while 1:
        try:

            handlers = [Handlers.VolumeAlertHandler(notify),
                            Handlers.DepthDiffAlertHandler(notify),
                            Handlers.HengpanAlertHandler(notify)]

            ws = MessageSourceWebSocket(handlers)
            ws.start()
        except Exception as e:
            print(e)
    pass

if __name__ == '__main__':

    if test_folder:
        run_test(test_folder)
    else:
        run()

