#!/usr/bin/python
# -*- coding: utf-8 -*-
# encoding: utf-8
# 客户端调用，扫描指定币种集合

import Notification
from Notification import log

from ok_api import OKCoinSpot

import json
import os
import time
import Utils
import argparse
import threading

# parser = argparse.ArgumentParser(description='use -type=30min/4hour')
# parser.add_argument('-type', type=str, default = "30min")
# args = parser.parse_args()


# 初始化apikey，secretkey,url
apikey = '52928f7e-a6ea-4cc5-b6fb-458cc150dd2b'
secretkey = 'BB1F6ACEC90BCD53A25FEFA2250D14CF'
okcoinRESTURL = 'www.okb.com'  # 请求注意：国内账号需要 修改为 www.okcoin.cn

# 现货API
okcoinSpot = OKCoinSpot(okcoinRESTURL, apikey, secretkey)


def getAV(prices, length):
    size = len(prices)
    av = [sum(prices[0:length]) / length]
    head = length
    while head < size:
        v = av[-1]
        v -= (prices[head - length] / length)
        v += (prices[head] / length)
        av.append(v)
        head += 1
        pass
    return av

class Candle(object):
    def __init__(self, ts, open, high,low,close):
        self.ts = ts
        self.open = open
        self.close = close
        self.high = high
        self.low = low
        self.ma5 = None
        self.ma20 = None
        self.isCross = False # 是否是交汇点
        self.isPositiveSlop = False

    def ma_type(self):
        if self.ma5 > self.ma20:
            return 1
        return -1

    def is_green(self):
        return self.close >= self.open

    def is_red(self):
        return not self.is_green()
    def is_above_ma5(self):
        return self.close >= self.ma5


#表示一个交汇段
class TN(object):
    def __init__(self):
        #这个交汇段内的柱子
        self.candles = []

    def push_candle(self, candle):
        self.candles.append(candle)

    def start_price(self):
        return self.candles[0].close


    def check_buy_point(self, cfg):
        # print("检查交汇段:%s" % Utils.time_str(self.candles[0].ts))
        price = cfg["price"]
        for i in range(len(self.candles)):
            candle = self.candles[i]
            if candle.close >= self.start_price() * (1+price): #涨幅超过了阈值
                if i > cfg["k_count"]: # k线个数超过阈值
                    above_ma5_count = 0
                    green_count = 0
                    for j in range(i):
                        cc = self.candles[j]
                        if cc.is_green():
                            green_count += 1
                        if cc.is_above_ma5():
                            above_ma5_count += 1
                    above_ma5_ratio = above_ma5_count / i
                    green_ratio = green_count / i
                    # print("%s, ma5占比：%f, 绿珠子占比:%f" % (Utils.time_str(candle.ts), above_ma5_ratio, green_ratio))
                    if above_ma5_ratio >= cfg["above_ma5"] and green_ratio >= cfg["green_count"]: #绿珠子满足阈值
                        return candle
        return None

class Coin(object):

    def __init__(self, symbol, cfg ):
        self.cfg = cfg
        self.symbol = symbol
        self.count = 0
        self.buy_price = 0
        self.type = 0
        self.kline_checked = False
        self.last_checked_kline_ts = 0
        self.tns = []

    def check_kline(self, time_type, save_dir):
        self.type = 0
        self.kline_checked = False
        try:
            ori_kline = okcoinSpot.kline(self.symbol, time_type, 2000)
            self.kline_checked = True
            kline_ts = ori_kline[-1][0]
            if kline_ts == self.last_checked_kline_ts:
                return
            self.last_checked_kline_ts = kline_ts
        except:
            print("get kline error:" + self.symbol)
            return

        file = open(os.path.join(save_dir, self.symbol + ".kline"), 'w')
        file.write(json.dumps(ori_kline))
        file.close()

        price_array = [float(x[4]) for x in ori_kline]
        all_candles = []
        for i in range(19,len(price_array), 1):
            current_kline = ori_kline[i]
            current_candle = Candle(current_kline[0] / 1000, float(current_kline[1]),float(current_kline[2]),float(current_kline[3]),float(current_kline[4]))
            all_candles.append(current_candle)
            current_candle.ma5 = sum(price_array[i-4:i+1]) / 5
            current_candle.ma20 = sum(price_array[i-19:i+1]) / 20
            if i >= 20:
                last_candle = all_candles[-2]
                current_candle.isCross = (last_candle.ma_type() * current_candle.ma_type() == -1)
                # print(last_candle.ma_type() * current_candle.ma_type())
                current_candle.isPositiveSlop = current_candle.ma5 > last_candle.ma5
                # 如果当前蜡烛是一个交汇点，那么就肯定要开启一个新的交汇段，
                # 否则就表示当前蜡烛仍然处于上一个交汇段内
                if current_candle.isCross:
                    tn = TN()
                    tn.push_candle(current_candle)
                    self.tns.append(tn)
                elif self.tns:
                    tn = self.tns[-1]
                    tn.push_candle(current_candle)

        # 遍历所有的交汇段
        for tn in self.tns:
            buy_point = tn.check_buy_point(self.cfg)
            if buy_point:
                print("%s, 买入点 %s, 价格：%f" %(self.symbol, Utils.time_str(buy_point.ts), buy_point.close))





        # money = 10000
        # coin = 0
        #
        # buy_price = None
        # for i in range(20, len(price_array), 1):
        #     price = kline[i]["p"]
        #     ts = kline[i]['t']/1000
        #     if buy_price:
        #         if (price >= (buy_price * (1+self.zhiying))):
        #             money = coin * price * 0.998
        #             coin = 0
        #             print("%s,止盈卖出, 价格%f, 盈利%f" % (time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(ts)),price, price / buy_price - 1))
        #             buy_price = None
        #         elif (price <= (buy_price * ( 1- self.zhisun))):
        #             money = coin * price * 0.998
        #             coin = 0
        #             print("%s,止损卖出, 价格%f, 盈利%f" % (time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(ts)),price, price / buy_price - 1))
        #             buy_price = None
        #     elif is_buy_vector(tt[i]["ma5"], tt[i]["ma20"]) and not is_buy_vector(tt[i-1]["ma5"], tt[i-1]["ma20"]):
        #         buy_price = price
        #         coin = money / price * 0.998
        #         money = 0
        #         print("%s,买入,价格:%f" % (time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(ts)), buy_price))
        # total = money + coin * tt[-1]["p"]
        # print("当前余额约：%f, 盈利率:%f" % (total, total / 10000 -1))



def run(time_type, interval):
    log('start')

    while True:
        try:
            with open('Slope_alert_cfg.json') as d:
                cfg = json.load(d)

            from_time = time.time()
            folder_name = "data/" + time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime(from_time))

            Utils.mkdir(folder_name)

            for symbol in cfg["symbols"]:
                print("\n\n回测:%s"%symbol)
                c = Coin(symbol, cfg)
                c.check_kline(time_type, folder_name)




            # account.begin_logs(time_type)
            # for symbol in symbols:
            #
            #     if account.holding_symbol(symbol):
            #         coin = coins[symbol]
            #         if coin.has_kline() and coin.is_sell_point():
            #             (ask1, bid1) = coin.check_price()
            #             sell_price = ask1 - 0.0001
            #             account.sell(symbol, sell_price)
            #             pass
            #         pass
            #
            # if account.has_money():
            #     for symbol in symbols:
            #         coin = coins[symbol]
            #         if coin.has_kline() and coin.is_buy_point() and account.has_money():
            #             (ask1, bid1) = coin.check_price()
            #             buy_price = bid1 + 0.0001
            #             account.buy(symbol, buy_price)
            #             pass
            #     pass
            #
            # account.flush_logs()

        except Exception as e:
            raise e

        time.sleep(interval)

        pass


run("1min", 120)
