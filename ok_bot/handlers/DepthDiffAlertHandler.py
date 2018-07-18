import json
import heapq
from .Handler import Handler

class DepthMonitor(object):

    def __init__(self, symbol):
        self.symbol=symbol
        self.asks = {}
        self.bids = {}

        self.top_ask1=[]
        self.top_ask2=[]

        self.top_bid1=[]
        self.top_bid2=[]
        self.update_times = 0


    def update_depth(self, direction_depth, change):

        for a in change:
            if a[1] == '0' and a[0] in direction_depth:
                del direction_depth[a[0]]
            else:
                direction_depth[a[0]] = float(a[1])

    def depth_change(self, change):
        self.update_times += 1
        if 'asks' in change:
            self.update_depth(self.asks, change['asks'])
        if 'bids' in change:
            self.update_depth(self.bids, change['bids'])
        self.update_ask1_and_bid1_ask2_and_bid2()

    def get_total_depth(self, depth):
        t = 0
        p = 0
        for k, v in depth.items():
            t += v
            p += float(k) * float(v)
        return p, t

    def get_total_asks(self):
        return self.get_total_depth(self.asks)

    def get_total_bids(self):
        return self.get_total_depth(self.bids)

    def update_ask1_and_bid1_ask2_and_bid2(self):

        top_bids = heapq.nlargest(2, self.bids.items(), key=lambda x:float(x[0]))
        bottom_asks = heapq.nsmallest(2, self.asks.items(), key=lambda x:float(x[0]))

        self.top_ask1 = bottom_asks[0]
        self.top_ask2 = bottom_asks[1]
        self.top_bid1 = top_bids[0]
        self.top_bid2 = top_bids[1]


class DepthDiffAlertHandler(Handler):
    def __init__(self, notify):
        super().__init__(notify)
        self.alerts = {}

    def cfgFile(self):
        return 'depth_diff_alert_cfg.json'

    def OnNewDepth(self, depth, symbol, ts):
        if symbol not in self.cfg:
            return
        if symbol not in self.alerts:
            self.alerts[symbol] = DepthMonitor(symbol)
        monitor = self.alerts[symbol]

        monitor.depth_change(depth)

        if monitor.update_times < 2:
            return

        cfg = self.cfg[symbol]
        if "alert_diff_p" in cfg:
            alert_diff = float(cfg['alert_diff_p'])
            bid_diff = float(monitor.top_bid2[0]) / float(monitor.top_bid1[0])
            alert_text =""
            if bid_diff < alert_diff:
                alert_text = "%s 买盘价差超过:%f，买一:%s 买二:%s" % (symbol, bid_diff, monitor.top_bid1[0], monitor.top_bid2[0])


            ask_diff = float(monitor.top_ask1[0]) / float(monitor.top_ask2[0])
            if ask_diff < alert_diff:
                alert_text = "%s 卖盘价差超过:%f, 卖一:%s 卖二:%s" % (symbol, ask_diff,monitor.top_ask1[0], monitor.top_ask2[0])
            if alert_text:
                self.notify(alert_text, ts)



    def OnNewDeals(self, deals, symbol, ts):
        pass


