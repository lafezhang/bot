import ok_api
import json
import time
import threading
import Notification

# 初始化apikey，secretkey,url
# 初始化apikey，secretkey,url
apikey = '52928f7e-a6ea-4cc5-b6fb-458cc150dd2b'
secretkey = 'BB1F6ACEC90BCD53A25FEFA2250D14CF'
okcoinRESTURL = 'www.okb.com'  # 请求注意：国内账号需要 修改为 www.okcoin.cn

# 现货API
okcoinSpot = ok_api.OKCoinSpot(okcoinRESTURL, apikey, secretkey)

class SellOrder(object):
    def __init__(self, symbol, order_id, price, amount):
        self.orderid = order_id
        self.symbol = symbol

        self.price = price
        self.amount = amount
        # status: -1:已撤销
        # 0: 未成交
        # 1: 部分成交
        # 2: 完全成交
        # 2: 完全成交
        # 3: 撤单处理中
        self.status = -2

    def update_status(self):
        result = json.loads(okcoinSpot.orderinfo(self.symbol, self.orderid))
        if "result" in result and result["result"] and "orders" in result:
            oo = result["orders"][0]
            self.status = oo["status"]

    def cancel_order(self):
        while 1:
            try:
                result = json.loads(okcoinSpot.cancelOrder(self.symbol, self.orderid))

                cc = 0
                while self.status not in [-1, 2, 1] and cc < 10:
                    self.update_status()
                    time.sleep(0.2)
                    cc += 1
                return

            except Exception as e:
                print(e)
                time.sleep(10)



class Bot(object):

    def __init__(self, symbol,cfg):
        self.cfg = cfg
        self.symbol = symbol
        self.orders = []

    def run_once(self):
        try:

            for order in self.orders:
                order.cancel_order()
                if order.status in [1, 2]:
                    title = "%s已成交，价格:%f, 数量:%f" %(self.symbol, order.price, order.amount)
                    Notification.log_and_email(title, title)

            self.orders = []
            userinfo = json.loads(okcoinSpot.userinfo())
            if "result" in userinfo and userinfo["result"]:
                coin = self.symbol.split("_")[0]
                free_coin = float(userinfo["info"]["funds"]["free"][coin])
                ticker = okcoinSpot.ticker(self.symbol)
                last_price = float(ticker['ticker']['last'])
                for cfg in self.cfg:
                    price = last_price * (1+cfg['p'])
                    amount = free_coin * cfg['v']
                    order = json.loads(okcoinSpot.trade(self.symbol, "sell", price, amount))
                    if "order_id" in order:
                        self.orders.append(SellOrder(self.symbol, order["order_id"], price, amount))



        except Exception as e:
            print(e)


        pass

def run_on_symbol(symbol, cfg):
    bot = Bot(symbol, cfg)

    while 1:
        bot.run_once()
        time.sleep(10)


def run():
    while 1:
        try:
            with open('ok_frequent_order_cfg.json') as d:
                cfg = json.load(d)
                symbols = cfg.keys()
            threads = []
            for k, config in cfg.items():
                t = threading.Thread(target=run_on_symbol, args=(k, config))
                t.start()
                threads.append(t)

            for t in threads:
                t.join()


        except Exception as e:
            print(e)

        time.sleep(10)

        pass


run()