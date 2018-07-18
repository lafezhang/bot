
import json

from .Handler import Handler
class Order(object):

    def __init__(self, arr):
        self.id = arr[0]
        self.price = float(arr[1])
        self.amount = float(arr[2])
        self.time = arr[3]
        self.direction = arr[4]


class Kline(object):
    def __init__(self, ts):
        self.reset(ts)

    def reset(self, ts):
        self.orders = []

        self.open = 0
        self.close = 0
        self.high = 0
        self.low = 0
        self.open_time = ts

        self.buy_vol = 0
        self.sel_vol = 0

        self.ma5 = 0
        self.ma20 = 0

    def append_order(self, order):
        self.orders.append(order)
        if len(self.orders) == 1:
            self.open = order.price
            self.close = order.price
            self.high = order.price
            self.low = order.price
        else:
            self.close = order.price

            if self.high < order.price:
                self.high = order.price

            if self.low > order.price:
                self.low = order.price

        if order.direction == "ask":
            self.sel_vol += order.amount
        else:
            self.buy_vol += order.amount

    def elapsed_time(self, ts):
        return ts-self.open_time;


class VolumeAlertHandler(Handler):
        def __init__(self, notify):

            super().__init__(notify)
            self.klines = {}

        def cfgFile(self):
            return "volume_alert_cfg.json"

        def get_cfg_symbols_set(self):
            return set(self.cfg.keys())

        def OnNewDeals(self, deals, symbol, ts):

            if len(deals) == 0:
                return

            if symbol not in self.cfg:
                return

            if symbol not in self.klines:
                self.klines[symbol] = Kline(ts)
                #忽略第一条聚合消息
                return

            kline = self.klines[symbol]

            for x in deals:
                kline.append_order(Order(x))

            if kline.elapsed_time(ts) > 60:
                symbol_cfg = self.cfg[symbol]
                buy_amount = kline.buy_vol - kline.sel_vol
                price_up = (kline.close / kline.open) - 1

                if buy_amount > symbol_cfg['alert_amount_in_1min']  and price_up >= 0.02:
                    alert_title = "%s, 买量:%d, 拉升:%.2f%%" % (symbol, buy_amount, price_up*100)
                    self.notify(alert_title, ts)


                kline.reset(ts)

            pass

        def OnNewDepth(self, depth, symbol, ts):
            pass