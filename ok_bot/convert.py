
import argparse
import sqlite3
import json
from operator import attrgetter
import time
import os


parser = argparse.ArgumentParser(description='use -i=input_folder -o=output_folder')
parser.add_argument('-i', type=str)
parser.add_argument('-o', type=str)
args = parser.parse_args()

def mkdir(path):
    folder = os.path.exists(path)
    if not folder:                   #判断是否存在文件夹如果不存在则创建为文件夹
        os.makedirs(path)            #makedirs 创建文件时如果路径不存在会创建这个路径

class Order(object):

    def __init__(self, dic):
        self.id = dic["id"]
        self.ts = dic["ts"]
        self.amount = dic["amount"]
        self.price = dic["price"]
        self.direction = dic["direction"]

    def simple_json(self):
        return [self.amount, self.price, "b" if self.direction=="buy" else "s"]

class Trade(object):

    def __init__(self, dic):
        self.id = dic["id"]
        self.ts = dic["ts"]
        self.orders = [Order(x) for x in dic["data"]]

    def get_amount(self, direction):
        amount = 0
        for o in self.orders:
            if o.direction == direction:
                amount += o.amount
        return amount

    def get_buy_amount(self):
        return self.get_amount("buy")
    def get_sell_amount(self):
        return self.get_amount("sell")

    def simple_json(self):
        return [x.simple_json() for x in self.orders]

class Kline(object):

    def __init__(self, ts):
        self.ts = ts
        self.timestr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts/1000))
        self.trades = []

        self.reset()

    def reset(self):

        self.open = 0
        self.close = 0
        self.high = 0
        self.low = 0
        self.buy_amount = 0
        self.sell_amount = 0
        self.buy_depth = []
        self.sell_depth = []

    def addTrade(self, trade):
        self.trades.append(trade)

    def process(self):
        self.reset()

        orders = []
        for t in self.trades:
            orders.extend(t.orders)
            buy_amount = t.get_buy_amount()
            sell_amount = t.get_sell_amount()
            if buy_amount > 0:
                self.buy_depth.append(buy_amount)
            if sell_amount > 0:
                self.sell_depth.append(sell_amount)

        self.buy_depth.sort(reverse=True)
        self.sell_depth.sort(reverse=True)

        orders.sort(key=attrgetter('ts'))
        self.open=orders[0].price
        self.close=orders[-1].price
        low=self.open
        high=self.open
        for o in orders:
            if o.price > high:
                high = o.price
            if o.price < low:
                low = o.price
            if o.direction == "buy":
                self.buy_amount += o.amount
            else:
                self.sell_amount += o.amount

        self.low = low
        self.high = high

    def reprJSON(self):
        return {"ts":self.ts, "open":self.open, "close":self.close, "high":self.high, "low":self.low,
                "buy":self.buy_amount, "sell":self.sell_amount, "buy_depth":self.buy_depth, "sell_depth":self.sell_depth}

    def simple_json(self):
        return [self.ts, [x.simple_json() for x in self.trades]]

    def json_only_buy(self):
        return {"ts":self.timestr, "buy-sell":self.buy_amount-self.sell_amount}



def GenKline(trades, duration):
    result = {}
    for t in trades:
        ts = int(t['ts'] / duration) * duration

        if ts not in result:
            result[ts] = Kline(ts)

        kline = result[ts]
        kline.addTrade(Trade(t))

    l = list(result.values())
    l.sort(key=attrgetter('ts'))
    for o in l:
        o.process()

    return l

class KlineEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj,'json_only_buy'):
            return obj.json_only_buy()
        else:
            return json.JSONEncoder.default(self, obj)

input_dir = args.i
output_dir = args.o
print(output_dir)
mkdir(output_dir)
for file in os.listdir(input_dir):
    input_file = os.path.join(input_dir, file)
    conn = sqlite3.connect(input_file)

    cursor = conn.execute("SELECT * from message where type='detail'")
    last_time = 0
    trades = [json.loads(row[2])['tick'] for row in cursor]

    duration = 1

    kline = GenKline(trades, duration * 60 * 1000)

    kline_json = [x.simple_json() for x in kline]
    kline_text = json.dumps(kline_json)

    output_file = os.path.join(output_dir,file)
    file = open(output_file, 'w')
    file.write(kline_text)
    file.close()