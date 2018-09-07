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
        return self.close > self.open

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
        lastcandle = None
        for i in range(len(self.candles)):
            candle = self.candles[i]
            if candle.close >= self.start_price() * (1+price) and lastcandle.close < self.start_price() * (1+price): #涨幅超过了阈值
                if i >= cfg["k_count"]: # k线个数超过阈值
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
                        return candle, i
            lastcandle = self.candles[i]
        return None, -1

    def check_sell_point(self, cfg, buy_price, index):
        i = index
        while i < len(self.candles):
            candle = self.candles[i]
            if candle.close >= buy_price*(1+cfg["zhiying"]):
                return 1, candle
            if candle.close <= buy_price*(1-cfg["zhisun"]):
                return -1, candle
            i+=1
        return 0, None




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

    def check_kline(self, time_type, save_dir, initial_money):
        self.type = 0
        self.kline_checked = False
        try:
            ori_kline = okcoinSpot.kline(self.symbol, time_type, 2000)
            self.kline_checked = True
            kline_ts = ori_kline[-1][0]
            if kline_ts == self.last_checked_kline_ts:
                return initial_money
            self.last_checked_kline_ts = kline_ts
        except:
            print("get kline error:" + self.symbol)
            return initial_money

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

        if not self.tns:
            print("没有交汇点")
            return initial_money

        money = initial_money
        coin = 0

        sell_type_str = {1:"止盈卖出", -1:"止损卖出"}
        while self.tns:
            tn = self.tns.pop(0)
            buy_point, index = tn.check_buy_point(self.cfg)
            if buy_point:
                buy_price = buy_point.close
                print("%s, 买入点 %s, 价格：%f" %(self.symbol, Utils.time_str(buy_point.ts), buy_price))
                coin = money / buy_price * 0.998
                money = 0

                tn2 = tn
                index2 = index
                while True:
                    sell_type, sell_point = tn2.check_sell_point(self.cfg, buy_price, index2)
                    if sell_point:
                        money = coin * sell_point.close * 0.998
                        coin = 0
                        print("%s, 卖出点 %s, %s, 价格:%f, 收益:%f" %(self.symbol,Utils.time_str(sell_point.ts), sell_type_str[sell_type], sell_point.close, sell_point.close / buy_price -1))
                        break
                    if not self.tns:
                        break
                    tn2 = self.tns.pop(0)
                    index2 = 0

        remain_money = money + coin*price_array[-1]

        print("最终收益:%f" % ((remain_money - initial_money)/ initial_money))
        return remain_money


def run(time_type, interval):
    log('start')

    try:
        with open('Slope_alert_cfg.json') as d:
            cfg = json.load(d)

        from_time = time.time()
        folder_name = "data/" + time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime(from_time))

        Utils.mkdir(folder_name)

        money = 10000 # 每个币拿这么多钱去玩
        total_remain_money = 0 # 最终剩余的钱总和
        total_money = 0 # 总共投入的钱总和
        for symbol, symbol_cfg in cfg.items():
            print("\n\n回测:%s" % symbol)
            c = Coin(symbol, symbol_cfg)
            total_remain_money += c.check_kline(time_type, folder_name, money)
            total_money += money

        print("最终总收益:%f" % ((total_remain_money - total_money) / total_money))

    except Exception as e:
        raise e


run("1min", 120)
