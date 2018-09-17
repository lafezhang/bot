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
        self.ma20 = self.ma5 = 0
        self.open_time = open_time
        self.total_money = 0
        self.ema12=0
        self.ema26=0
        self.diff=0
        self.dea=0
        self.macd=0


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
        # price = cfg["price"]
        # lastcandle = self.candles[-1]

        # if lastcandle.close < self.start_price() * (1 + price):
        #     # 涨幅没满足
        #     return False

        if len(self.candles) < cfg["k_count"]:
            # k线个数没满足
            return False

        above_ma5_count = 0
        green_count = 0
        for cc in self.candles:
            if cc.is_green():
                green_count += 1
            if cc.is_above_ma5():
                above_ma5_count += 1
        above_ma5_ratio = float(above_ma5_count) / len(self.candles)
        green_ratio = float(green_count) / len(self.candles)

        if above_ma5_ratio >= cfg["above_ma5"] and green_ratio >= cfg["green_count"]:  # 绿珠子满足阈值
            return True

        return False

    def buy_info(self):

        above_ma5_count = 0
        green_count = 0
        for cc in self.candles:
            if cc.is_green():
                green_count += 1
            if cc.is_above_ma5():
                above_ma5_count += 1
        above_ma5_ratio = float(above_ma5_count) / len(self.candles)
        green_ratio = float(green_count) / len(self.candles)

        return "kline_count:%d, above_ma5_ratio:%f, green_ratio:%f" %(len(self.candles), above_ma5_ratio, green_ratio)

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
        self.skipped_count = 0

        self.logs = []

        self.sss = 0


    def sell_all(self,price, type, ts):
        self.money = price * self.coin_count * 0.998
        self.coin_count = 0
        self.buy_price = 0
        log = "%s, %s:%f" % (Utils.time_str(ts), type, price)
        self.logs.append(log)



    def buy_all(self, price, ts):
        self.coin_count = self.money / price  * 0.998
        self.money = 0
        self.buy_price = price
        self.skipped_count = 0
        log = "%s, 买入:%f" % (Utils.time_str(ts), price)
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

        if len(current_candle.orders) != 4:
            pass

        if not self.candles:
            current_candle.ema12=current_candle.close
            current_candle.ema26=current_candle.close
            current_candle.diff = current_candle.ema12 - current_candle.ema26
            current_candle.dea=current_candle.diff
        else:
            last_candle = self.candles[-1]
            current_candle.ema12 = 2.0/13 * current_candle.close + 11.0/13*last_candle.ema12
            current_candle.ema26 = 2.0/27 * current_candle.close + 25.0/13*last_candle.ema26
            current_candle.diff = current_candle.ema12 - current_candle.ema26
            current_candle.dea = 2.0/10 * current_candle.diff + 8.0/10 * last_candle.dea

        current_candle.macd = 2*(current_candle.diff - current_candle.dea)

        self.candles.append(current_candle)
        if len(self.candles) >= 20:

            # 只有超过20个kline，才能计算计算ma
            total = 0

            for i in range(-1, -6, -1):
                total += self.candles[i].close

            current_candle.ma5 = total / 5

            for i in range(-6, -21, -1):
                total += self.candles[i].close

            current_candle.ma20 = total / 20

            if len(self.candles) >= 21:
                # 只有超过21个kline，才能确定当前是不是交汇点

                last_candle = self.candles[-2]

                if self.coin_count > 0:
                    should_sell = False
                    sell_type = None
                    if current_candle.close >= self.buy_price * (1 + self.cfg["zhiying"]):
                        should_sell = True
                        sell_type = "止盈卖出"
                    if current_candle.close <= self.buy_price * (1 - self.cfg["zhisun"]):
                        should_sell = True
                        sell_type = "止损卖出"
                    if (last_candle.ma_type() > 0 and current_candle.ma_type() < 0):
                        if self.skipped_count == 1:
                            should_sell = True
                            sell_type = "缠绕结束卖出"
                        else:
                            self.skipped_count+=1

                    if should_sell:
                        self.sell_all(current_candle.close, sell_type, current_candle.orders[-1].ts)
                        self.tn = None


                if (last_candle.ma_type() < 0 and current_candle.ma_type() > 0):
                    self.logs.append("%s, 缠绕开始" % (Utils.time_str(current_candle.open_time)))
                    self.tn = TN()

                if self.tn:
                    self.tn.push_candle(current_candle)
                    if self.money > 0.0001:
                        should_buy = self.tn.check_buy_point(self.cfg)
                        if should_buy:
                            self.logs.append(self.tn.buy_info())
                            self.buy_all(current_candle.close, current_candle.orders[-1].ts)




        self.current_candle = Candle(current_candle.open_time + self.kline_duration, self.kline_duration)
        if len(self.candles) > 100:
            self.candles = self.candles[-30:]

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
                self.symbol_alerts[symbol] = SymbolAlert(symbol, self.notify, self.cfg[symbol], 60, 10000, self.back_testing)

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

