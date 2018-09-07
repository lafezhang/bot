from .Handler import Handler
import time, datetime

class HoldingCoin(object):
    def __init__(self, symbol, zhisun):
        self.zhisun = zhisun
        self.symbol = symbol
        self.amount = 0
        self.buy_price = 0

        self.sell_step = []
        self.buy_time = 0

    def buy(self, money, price, ts):
        self.amount += money/price * 0.998
        self.buy_price = price

        self.buy_time = ts

        # self.sell_step = [
            # {'p': price * (1+0.01), 'b': price * 1 * 0.97, 'v' : 0.3 * self.amount} ,
            # {'p': price * (1+0.02), 'b': price * 1 * 0.97,'v' : 0.3 * self.amount},
            # {'p': price * (1+0.03), 'b': price * 1 * 0.97,'v' : 0.3 * self.amount},
            # {'p': price * (1+0.5), 'b': price * 1 * 0.97,'v' : 0.01 * self.amount}]

        self.sell_step = [
            {'p': price * (1 + 0.01), 'b': price * 1 * (1-self.zhisun), 'v': self.amount}]


    def hold_duration(self, ts):
        return ts - self.buy_time

    def sell_all(self, price):
        amount = self.amount
        self.sell_step = []
        self.amount = 0
        return price * amount  * 0.998

    def sell_next(self, price):
        if len(self.sell_step) == 1:
            return self.sell_all(price)

        amount = self.sell_step[0]['v']
        self.sell_step = self.sell_step[1:]

        self.amount -= amount
        return amount * price  * 0.998



class Account(object):
    def __init__(self, money, zhisun):
        self.zhisun = zhisun
        self.initial_money = money
        self.money = money
        self.coins = {}
        self.last_prices = {}

        self.account_logs={}
        self.time_line_logs = []

    def get_a_log(self, symbol):
        if symbol not in self.account_logs:
            self.account_logs[symbol] = []
        return self.account_logs[symbol]


    def buy_all(self,symbol, price, ts):
        if self.money < 1:
            return

        if symbol not in self.coins:
            self.coins[symbol] = HoldingCoin(symbol, self.zhisun)
        coin =self.coins[symbol]
        coin.buy(self.money , price, ts)
        self.money = 0

        ll = {"type":'准备买入',"price":price, "ts":ts, "symbol":symbol}
        self.get_a_log(symbol).append(ll)
        self.time_line_logs.append(ll)

    def holding_coin(self,symbol):
        if symbol not in self.coins:
            return None
        return self.coins[symbol]

    def sell_next(self, symbol, price, ts):
        coin = self.holding_coin(symbol)
        if not coin:
            return

        ll = {"type": '盈利卖出', "price": price, "ts": ts, "symbol":symbol}
        self.get_a_log(symbol).append(ll)
        self.time_line_logs.append(ll)
        # print("%s 卖出:%s, 价格%f，盈利超过%f" % (time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(ts)),symbol, price, coin.sell_step[0]['p'] / coin.buy_price))
        self.money += coin.sell_next(price)
        self.print_asserts()

    def sell_all(self, symbol, price, ts):

        coin = self.holding_coin(symbol)
        if coin:
            self.money += coin.sell_all(price)
            ll = {"type": '止损卖出', "price": price, "ts": ts, "symbol":symbol}
            self.get_a_log(symbol).append(ll)
            self.time_line_logs.append(ll)
            print("%s 卖出止损:%s, 价格%f" % (time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(ts)), symbol, price))
            self.print_asserts()

    def sell_all_a(self, symbol, price, ts):
        coin = self.holding_coin(symbol)
        if coin:
            self.money += coin.sell_all(price)
            ll = {"type": '超时止损', "price": price, "ts": ts, "symbol":symbol}
            self.get_a_log(symbol).append(ll)
            self.time_line_logs.append(ll)
            print("%s 未突破阈值：卖出止损:%s, 价格%f" % (time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(ts)),symbol, price))
            self.print_asserts()

    def set_last_price(self, symbol, price):
        self.last_prices[symbol] = price

    def print_asserts(self):
        total = self.money
        coinss = []
        for s ,coin in self.coins.items():
            price = self.last_prices[s]
            total += price * coin.amount
            if coin.amount > 0:
                coinss.append("%s:%.4f * %.4f" %(s, price , coin.amount))
        ll = "当前盈利率:%.2f\n当前资产:%s\n\n\n" % ((total - self.initial_money) / self.initial_money, ", ".join(coinss))
        print(ll)

        return ll

    def print_summry(self):
        for symbol, logs in self.account_logs.items():
            print(symbol)
            for log in logs:
                print("%s, %s, %s" %(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(log['ts'])), log['type'], log['price']) )

            print('\n\n\n')
    def flush_logs(self):

        timeline_logs = []
        symbol_logs = []
        for symbol, logs in self.account_logs.items():
            symbol_logs.append(symbol)
            for log in logs:
                symbol_logs.append("%s, %s, %s" %(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(log['ts'])), log['type'], log['price']))
            symbol_logs.append('\n\n\n')

        for log in self.time_line_logs:
            timeline_logs.append("%s, %s, %s, %s" %(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(log['ts'])), log['symbol'],log['type'], log['price']))

        all_logs = "止损账户:%f\n时间线日志:\n%s\n\n\n币种操作日志:%s\n\n%s" %(self.zhisun,"\n".join(timeline_logs),"\n".join(symbol_logs), self.print_asserts())

        return all_logs

class Order(object):

    def __init__(self, price, amount, direction, ts):
        self.price = price
        self.amount = amount
        self.ts = ts
        self.direction = direction
        self.total_money = price * amount


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

class TN(object):

    def __init__(self, start_kline):
        self.start_kline = start_kline
        self.klines = [start_kline]
        self.min = min(start_kline.close, start_kline.open)
        self.max = min(start_kline.close, start_kline.open)

    def update(self, kline):
        self.min = min(self.min, kline.close, kline.open)
        self.max = max(self.max, kline.close, kline.open)
        self.klines.append(kline)


class SymbolAlert(object):

    def __init__(self, symbol, notify, cfg, kline_duration, hengpan_chanrao_count, back_testing, account, tupo_money):
        self.hengpan_chanrao_count = hengpan_chanrao_count
        self.account = account
        self.back_testing = back_testing
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

        self.tupo_money = tupo_money

    def has_effective_volume(self):
        c = 0
        tk = 0
        for k in self.tn[-1].klines:
            tk += 1
            if k.total_money < self.tupo_money:
                c += 1

        if c / tk > 0.3:
            return False

        c=0
        tk=0
        for tn in self.tn:
            for k in tn.klines:
                tk += 1
                if k.total_money < 1:
                    c += 1
        if c / tk > 0.3:
            return False

        return True


    def push_tn(self, kline, new):
        if new:
            self.cc+=1
            self.alerted = False
            tn = TN(kline)
            self.tn.append(tn)

            hengpan_tn_count = (self.hengpan_chanrao_count + 1) * 2

            if len(self.tn) >= hengpan_tn_count:
                self.tn = self.tn[1:hengpan_tn_count]

            if len(self.tn) >= hengpan_tn_count-1:
                min_v = min(self.tn[0:hengpan_tn_count-1], key=lambda x: x.min).min
                max_v = max(self.tn[0:hengpan_tn_count-1], key=lambda x: x.max).max
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


        if self.back_testing:
            for account in self.account:
                account.set_last_price(self.symbol, order.price)

        if not self.alerted and has_new_kline and len(self.klines) > 2:
            if self.hengpan and self.has_effective_volume():
                last_kline = self.klines[-2]
                last_kline_close_price = last_kline.close
                if (last_kline_close_price - self.hengpan_max) / self.hengpan_max >= self.r:
                    self.alerted = True
                    abc=[]
                    for i, val in enumerate(self.tn):
                        abc.append("t%d=%s" % (i+1,time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(val.start_kline.open_time))))
                    # print("%s横盘突破，现价:%f。%s, 横盘最高:%f" % (self.symbol, last_kline_close_price, ", ".join(abc), self.hengpan_max), order.ts)
                    self.notify("%s横盘突破，现价:%f。" % (self.symbol, last_kline_close_price), order.ts)
                    if self.back_testing:
                        for account in self.account:
                            account.buy_all(self.symbol, order.price, order.ts)

        if self.back_testing:
            for account in self.account:
                coin = account.holding_coin(self.symbol)
                if coin and coin.amount > 0:
                    first_s = coin.sell_step[0]
                    if first_s['b'] > order.price:
                        account.sell_all(self.symbol, order.price, order.ts)

                    elif order.price > first_s['p']:
                        account.sell_next(self.symbol, order.price, order.ts)



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
        def __init__(self, notify, tupo_money, back_testing = False):

            super().__init__(notify)
            self.tupo_money = tupo_money
            self.symbol_alerts = {}
            self.back_testing = back_testing
            self.account = [Account(10000, 0.03)]
            self.lastFlushTime = 0

        def cfgFile(self):
            return "hengpan_alert_cfg.json"

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
                self.symbol_alerts[symbol] = SymbolAlert(symbol, self.notify, self.cfg[symbol], 60, 2, self.back_testing, self.account, self.tupo_money / 6.5)

            alert = self.symbol_alerts[symbol]
            alert.OnNewDeals(deals, ts)

        def OnNewDepth(self, depth, symbol, ts):
            pass

        def send_logs(self):
            for account in self.account:
                logs = account.flush_logs()
                self.notify(logs, time.time(), "突破成交额%f" % self.tupo_money)

        def onEnd(self):
            if self.back_testing:
                self.send_logs()

                self.account = None
