from .Handler import Handler
import time, datetime
class Order(object):

    def __init__(self, price, amount, direction, ts):
        self.price = price
        self.amount = amount
        self.ts = ts
        self.direction = direction


class Kline(object):
    def __init__(self, open_time, duration):
        self.duration = duration
        self.reset(open_time)

    def reset(self, open_time):
        self.orders = []

        self.open = self.close = self.high = self.low = 0
        self.buy_vol = self.sel_vol = 0
        self.ma20 = self.ma5 = 0
        self.open_time = open_time


    def set_all_price(self, price):
        self.open = self.close = self.high = self.low = price

    def append_order(self, order):

        if order.ts < self.open_time or order.ts >= self.open_time + self.duration:
            return False

        self.orders.append(order)
        if len(self.orders) == 1:
            self.open = self.close = self.high = self.low = order.price
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

        return True

    def elapsed_time(self, ts):
        return ts-self.open_time;

class TN(object):

    def __init__(self, start_kline):
        self.start_kline = start_kline
        self.min = min(start_kline.close, start_kline.open)
        self.max = min(start_kline.close, start_kline.open)
    def update(self, kline):
        self.min = min(self.min, kline.close, kline.open)
        self.max = max(self.max, kline.close, kline.open)


class SymbolAlert(object):

    def __init__(self, symbol, notify, cfg, kline_duration):
        self.symbol = symbol
        self.notify = notify
        self.cfg = cfg
        self.h = cfg['h']
        self.r = cfg['r']
        self.hengpan = False
        self.hengpan_max = 0
        self.alerted = False
        self.kline_duration = kline_duration

        self.klines = []

        self.tn = []
        self.current_kline = None

        self.cc=0

    def push_tn(self, kline, new):
        if new:
            self.cc+=1
            self.alerted = False
            tn = TN(kline)
            self.tn.append(tn)

            if len(self.tn) >= 6:
                self.tn = self.tn[1:6]

            if len(self.tn) >= 5:
                min_v = min(self.tn[0:5], key=lambda x: x.min).min
                max_v = max(self.tn[0:5], key=lambda x: x.max).max
                if (max_v - min_v) / min_v <= self.h:
                    self.hengpan = True
                    self.hengpan_max = max_v
                else:
                    self.hengpan = False
        else:
            if len(self.tn) > 0:
                self.tn[-1].update(kline)


        pass

    def push_kline(self):

        current_kline = self.current_kline
        if len(current_kline.orders) == 0:
            current_kline.set_all_price(self.klines[-1].close)

        next_kline = Kline(current_kline.open_time + self.kline_duration, self.kline_duration)

        self.klines.append(current_kline)
        if len(self.klines) >= 20:

            # 只有超过20个kline，才能计算计算ma
            total = 0

            for i in range(-1, -6, -1):
                total += self.klines[i].close
            current_kline.ma5 = total / 5

            for i in range(-6, -21, -1):
                total += self.klines[i].close
            current_kline.ma20 = total / 20

            if len(self.klines) >= 21:
                # 只有超过21个kline，才能确定当前是不是交汇点
                last_kline = self.klines[-2]
                if (last_kline.ma5 > last_kline.ma20 and current_kline.ma5 < current_kline.ma20) or (last_kline.ma5 < last_kline.ma20 and current_kline.ma5 > current_kline.ma20):
                    self.push_tn(current_kline, True)
                else:
                    self.push_tn(current_kline, False)


        self.current_kline = next_kline
        if len(self.klines) > 100:
            self.klines = self.klines[-30:]

        pass

    def append_order(self, order):

        if not self.current_kline:
            self.current_kline = Kline(int(order.ts / self.kline_duration) * self.kline_duration, self.kline_duration)

        if order.ts < self.current_kline.open_time:
            return

        has_new_kline = False
        while not self.current_kline.append_order(order):
            self.push_kline()
            has_new_kline = True



        if not self.alerted and has_new_kline and len(self.klines) > 2:
            if self.hengpan:
                last_kline = self.klines[-2]
                last_kline_close_price = last_kline.close
                if (last_kline_close_price - self.hengpan_max) / self.hengpan_max >= self.r:
                    self.alerted = True
                    abc=[]
                    for i, val in enumerate(self.tn):
                        abc.append("t%d=%s" % (i+1,time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(val.start_kline.open_time))))
                    print("%s横盘突破，现价:%f。%s" % (self.symbol, last_kline_close_price, ", ".join(abc)), order.ts)
                    self.notify("%s横盘突破，现价:%f。" % (self.symbol, last_kline_close_price), order.ts)


    def OnNewDeals(self, deals, ts):
        date = time.strftime("%Y-%m-%d", time.localtime(ts))
        for order in deals:
            order_date = order[3]
            full_date_str = "%s %s" % (date, order_date)
            order_ts = int(datetime.datetime.strptime(full_date_str, "%Y-%m-%d %H:%M:%S").strftime('%s'))
            if order_ts > ts:
                order_ts -= 24 * 60 * 60
            new_order = Order(float(order[1]), float(order[2]), order[4], order_ts)
            self.append_order(new_order)
        pass

class HengpanAlertHandler(Handler):
        def __init__(self, notify):

            super().__init__(notify)
            self.symbol_alerts = {}

        def cfgFile(self):
            return "hengpan_alert_cfg.json"

        def OnNewDeals(self, deals, symbol, ts):

            if len(deals) == 0:
                return

            if symbol not in self.cfg:
                return

            if symbol not in self.symbol_alerts:
                self.symbol_alerts[symbol] = SymbolAlert(symbol, self.notify, self.cfg[symbol], 60)

            alert = self.symbol_alerts[symbol]
            alert.OnNewDeals(deals, ts)

        def OnNewDepth(self, depth, symbol, ts):
            pass