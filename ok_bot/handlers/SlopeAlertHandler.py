from .Handler import Handler
import time, datetime
import Utils

class Order(object):

    def __init__(self, price, amount, direction, ts):
        self.price = price
        self.amount = amount
        self.ts = ts
        self.direction = direction
        self.total_money = price * amount


class Candle(object):
    def __init__(self, open_time, duration):
        self.duration = duration
        self.reset(open_time)

    def reset(self, open_time):
        self.orders = []

        self.open = self.close = self.high = self.low = 0
        self.buy_vol = self.sel_vol = 0
        self.ma80 = self.ma40 = self.ma5 = 0

        self.open_time = open_time
        self.total_money = 0


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

        self.total_money += order.total_money

        return True

    def elapsed_time(self, ts):
        return ts-self.open_time;


#表示一个交汇段
class TN(object):
    def __init__(self):
        #这个交汇段内的柱子
        self.candles = []

    def push_candle(self, candle):
        self.candles.append(candle)

    def start_price(self):
        return self.candles[0].close


class SymbolAlert(object):

    def __init__(self, symbol, notify, cfg, kline_duration, money, back_testing):
        self.back_testing = back_testing
        self.symbol = symbol
        self.notify = notify
        self.cfg = cfg
        self.alerted = False
        self.kline_duration = kline_duration
        self.money = money
        self.initial_money = money

        self.current_candle = None
        self.candles = []
        self.tn = None
        self.total_candle_count = 0
        self.coin_count = 0
        self.buy_price = 0

        self.ma40up = False
        self.ma40_time = 0
        self.ma40up_count = 0

        self.ma80up = False
        self.ma80_time = 0
        self.ma80up_count = 0

        self.logs = []


    def sell_all(self,price, type, ts):
        log = "%s, %s:%f, 收益:%.4f" % (Utils.time_str(ts), type, price, price / self.buy_price - 1)
        self.money = price * self.coin_count * 0.998
        self.coin_count = 0
        self.buy_price = 0
        self.logs.append(log)



    def buy_all(self, price, ts, append_log=""):
        self.coin_count = self.money / price  * 0.998
        self.money = 0
        self.buy_price = price
        self.skipped_count = 0
        log = "%s, 买入:%f, %s" % (Utils.time_str(ts), price, append_log)
        self.logs.append(log)

        self.notify(log, time.time(), "斜率策略买入点%s" % self.symbol)

    def total_money(self):
        if self.coin_count > 0:
            return self.money + self.coin_count * self.candles[-1].close
        return self.money

    def push_candle(self):
        self.total_candle_count += 1
        current_candle = self.current_candle
        if len(current_candle.orders) == 0:
            current_candle.set_all_price(self.candles[-1].close)


        self.candles.append(current_candle)
        if len(self.candles) >= 80:

            # 只有超过20个kline，才能计算计算ma
            total = 0

            for i in range(-1, -6, -1):
                total += self.candles[i].close

            current_candle.ma5 = total / 5

            for i in range(-6, -41, -1):
                total += self.candles[i].close

            current_candle.ma40 = total / 40

            for i in range(-41, -81, -1):
                total += self.candles[i].close

            current_candle.ma80 = total / 80

            last_candle = self.candles[-2]


            if current_candle.ma5 >= current_candle.ma80 and last_candle.ma5 < last_candle.ma80:
                self.ma80up = current_candle.ma80 > last_candle.ma80
                self.ma80_time = current_candle.orders[-1].ts
                self.ma40up_count = 0
            elif current_candle.ma5 <= current_candle.ma80 and last_candle.ma5 > last_candle.ma80:
                self.ma80up = False

            if current_candle.ma5 >= current_candle.ma40 and last_candle.ma5 < last_candle.ma40:
                #小缠绕开始点,记录斜率
                self.ma40up = current_candle.ma40 > last_candle.ma40
                self.ma40_time = current_candle.orders[-1].ts
                if self.ma80up:
                    self.ma40up_count+=1
            elif current_candle.ma5 <= current_candle.ma40 and last_candle.ma5 > last_candle.ma40:
                self.ma40up = False

            if current_candle.ma5 >= current_candle.ma80 and last_candle.ma5 < last_candle.ma80:
                if self.ma40up:
                    self.ma40up_count = 0

            if self.coin_count > 0:
                should_sell = False
                sell_type = None

                if current_candle.close >= self.buy_price * (1 + self.cfg["zhiying"]) \
                        and current_candle.ma5 < self.candles[-2].ma5 < self.candles[-3].ma5:
                    should_sell = True
                    sell_type = "止盈卖出"
                if current_candle.close <= self.buy_price * (1 - self.cfg["zhisun"]):
                    should_sell = True
                    sell_type = "止损卖出"

                if self.ma40up and current_candle.ma5 < current_candle.ma80:
                    should_sell = True
                    sell_type = "缠绕结束卖出"

                if should_sell:
                    self.sell_all(current_candle.close, sell_type, current_candle.orders[-1].ts)
            elif self.money > 0.0001:
                if current_candle.ma5 >= current_candle.ma80 and last_candle.ma5 < last_candle.ma80:
                    # 大缠绕上涨开始
                    if current_candle.ma5 >= current_candle.ma40:
                        # 小缠绕也是上涨中
                        ma80up = current_candle.ma80 > last_candle.ma80

                        if ma80up or self.ma40up:
                            # 有一个是斜率向上，则买入
                            self.buy_all(current_candle.close, current_candle.orders[-1].ts, "小在大前，ma80向上" if ma80up else ("小在大前，ma40向上，ma40上涨缠绕开始时间:%s" % (Utils.time_str(self.ma40_time))))
                if self.money > 0.0001:
                    if current_candle.ma5 >= current_candle.ma40 and last_candle.ma5 < last_candle.ma40:
                        # 小缠绕开始上涨
                        if self.ma40up_count == 1 and current_candle.ma5 >= current_candle.ma80:
                            # 大缠绕上涨中，并且此小缠绕是第一个
                            if self.ma80up:
                                self.buy_all(current_candle.close, current_candle.orders[-1].ts,"大在小前" )

        self.current_candle = Candle(current_candle.open_time + self.kline_duration, self.kline_duration)
        if len(self.candles) > 200:
            self.candles = self.candles[-120:]

        pass


    def append_order(self, order):
        if not self.current_candle:
            self.current_candle  = Candle(int(order.ts / self.kline_duration) * self.kline_duration, self.kline_duration)


        if order.ts < self.current_candle.open_time:
            return

        while not self.current_candle.append_order(order):
            self.push_candle()


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

    def flush_logs(self):
        text = "\n".join(self.logs)
        shouyi = "当前收益:%f" % (self.total_money() / self.initial_money - 1)
        text += "\n%s" % shouyi
        return text


class SlopeAlertHandler(Handler):
        def __init__(self, notify, back_testing = False):

            super().__init__(notify)
            self.symbol_alerts = {}
            self.back_testing = back_testing
            self.lastFlushTime = 0


        def cfgFile(self):
            return "Slope_alert_cfg.json"

        def OnNewDeals(self, deals, symbol, ts):

            if len(deals) == 0:
                return

            if symbol not in self.cfg:
                return

            if self.lastFlushTime == 0 :
                self.lastFlushTime = time.time()
            else:
                if time.time() - self.lastFlushTime >= 4 * 60 * 60:
                    self.send_logs()
                    self.lastFlushTime = time.time()


            if symbol not in self.symbol_alerts:
                self.symbol_alerts[symbol] = SymbolAlert(symbol, self.notify, self.cfg[symbol], 15* 60, 10000, self.back_testing)

            alert = self.symbol_alerts[symbol]
            alert.OnNewDeals(deals, ts)

        def OnNewDepth(self, depth, symbol, ts):
            pass

        def send_logs(self):
            logs = []
            all_initial_money = 0
            all_remain_money = 0
            for sysmbol ,alert in self.symbol_alerts.items():
                all_initial_money += alert.initial_money
                all_remain_money += alert.total_money()
                logs.append("%s\n%s" % (sysmbol,alert.flush_logs()))

            all_shouyi = "当前总收益:%f" % (all_remain_money / all_initial_money - 1)
            self.notify("\n\n\n".join(logs), time.time(), all_shouyi)


        def onEnd(self):
            if self.back_testing:
                self.send_logs()

