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
import ok_api

parser = argparse.ArgumentParser(description='use -t= test folder -s= test symbol -c -bt')
parser.add_argument('-t', type=str, default=None)
parser.add_argument('-s', type=str, default=None)
parser.add_argument('-capture', action='store_true', default=False)
parser.add_argument('-bt', action='store_true', default=False)
args = parser.parse_args()

test_folder = args.t
test_symbol = args.s
capture_mode = args.capture
back_test = args.bt

def mkdir(path):
    folder = os.path.exists(path)
    if not folder:  # 判断是否存在文件夹如果不存在则创建为文件夹
        os.makedirs(path)  # makedirs 创建文件时如果路径不存在会创建这个路径


def notify(message, ts, title=None):
    if test_folder or back_test:
        print("%s: %s" % (time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(ts)), message))
    else:
        t = title
        if not title:
            t = message
        Notification.log_and_email(message, t)


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
    def dispatch_end(self):
        for h in self.handlers:
            h.onEnd()


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

class MessageSourceKline(MessageSource):

    def start(self, params = None):
        symbols = set()
        for h in self.handlers:
            symbols = symbols.union(h.get_cfg_symbols_set())

        apikey = '52928f7e-a6ea-4cc5-b6fb-458cc150dd2b'
        secretkey = 'BB1F6ACEC90BCD53A25FEFA2250D14CF'
        okcoinRESTURL = 'www.okb.com'  # 请求注意：国内账号需要 修改为 www.okcoin.cn

        # 现货API
        okcoinSpot = ok_api.OKCoinSpot(okcoinRESTURL, apikey, secretkey)
        klines = {}
        start = 0
        end = 0
        for s in symbols:
            while True:
                try:
                    kline = okcoinSpot.kline(s, "1min", 2000, 0)
                    break
                except Exception as e:
                    print(e)
                    time.sleep(5)

            kline_dict = {}
            for kk in kline:
                kk[0] = kk[0]/1000
                kline_dict[kk[0]] = kk

            if start == 0:
                start = kline[0][0]
            if end == 0:
                end = kline[-1][0]

            klines[s] = kline_dict

        t = start
        while t < end:

            order_time = time.strftime("%H:%M:%S", time.localtime(t))
            for s, kline in klines.items():
                if t in kline:
                    kk = kline[t]

                    orders = [
                        ['0', str(kk[1]), str(float(kk[5]) / 4), order_time, "bid"],
                        ['0', str(kk[2]), str(float(kk[5]) / 4), order_time, "bid"],
                        ['0', str(kk[3]), str(float(kk[5]) / 4), order_time, "bid"],
                        ['0', str(kk[4]), str(float(kk[5]) / 4), order_time, "bid"]
                    ]

                    self.dispatch_deal_msg(orders, s, t)

            t += 60

        self.dispatch_end()

        pass

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

def run_back_test():
    handlers = [
        Handlers.HengpanAlertHandler(notify, True)
                ]
    ss = MessageSourceKline(handlers)
    ss.start()

def run():
    while 1:
        try:

            handlers = [Handlers.VolumeAlertHandler(notify),
                            Handlers.DepthDiffAlertHandler(notify),
                            Handlers.HengpanAlertHandler(notify, 3000, True),
                            Handlers.HengpanAlertHandler(notify, 1000, True),
                            Handlers.HengpanAlertHandler(notify, 0,True)]

            ws = MessageSourceWebSocket(handlers)
            ws.start()
        except Exception as e:
            print(e)
    pass

if __name__ == '__main__':

    if back_test:
        run_back_test()
    elif test_folder:
        run_test(test_folder)
    else:
        run()

