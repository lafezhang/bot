#!/usr/bin/python
# -*- coding: utf-8 -*-
# encoding: utf-8
# 客户端调用，扫描指定币种集合

from OkcoinSpotAPI import OKCoinSpot
from OkcoinFutureAPI import OKCoinFuture
import time

import logging
import logging.handlers

LOG_FILE = 'history.log'

handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=100 * 1024 * 1024, backupCount=5)  # 实例化handler
fmt = '%(asctime)s - %(message)s'

formatter = logging.Formatter(fmt)  # 实例化formatter
handler.setFormatter(formatter)  # 为handler添加formatter

logger = logging.getLogger('tst')  # 获取名为tst的logger
logger.addHandler(handler)  # 为logger添加handler
logger.setLevel(logging.DEBUG)

# 初始化apikey，secretkey,url
apikey = '52928f7e-a6ea-4cc5-b6fb-458cc150dd2b'
secretkey = 'BB1F6ACEC90BCD53A25FEFA2250D14CF'
okcoinRESTURL = 'www.okb.com'  # 请求注意：国内账号需要 修改为 www.okcoin.cn

# 现货API
okcoinSpot = OKCoinSpot(okcoinRESTURL, apikey, secretkey)

r = -0.005


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


def is_buy_vector(av5, av20):
    return av5 > av20


def is_sell_vector(av5, av20):
    return av5 < av20


class Account(object):

    def __init__(self, money, symbols):
        self.money = money
        self.coins = {x: {'count': 0, 'buy_price': 0} for x in symbols}

    def buy(self, symbol, price):
        logger.info("买入:%s 价格:%f" % (symbol, price))
        count = self.money / price * 0.998
        self.coins[symbol] = {'count': self.coins[symbol] + count, 'buy_price': price}
        self.money = 0

    def sell(self, symbol, price):
        buy_price = self.coins[symbol]['buy_price']
        logger.info("卖出:%s 价格:%f, 盈利:%f" % (symbol, price, (price / buy_price) - 1))
        money = self.coins[symbol] * price * 0.998
        self.money = money
        self.coins[symbol] = {'count': 0, 'buy_price': 0}

    def holding_symbol(self, symbol):
        return self.coins[symbol]['count'] > 0.0001

    def has_money(self):
        return self.money > 0.0001


class Coin(object):

    def __init__(self, symbol):
        self.symbol = symbol
        self.count = 0
        self.buy_price = 0
        self.type = 0

    def check_kline(self, time_type):
        print("checking kline:"+self.symbol)
        kline = okcoinSpot.kline(self.symbol, time_type, 30)

        reversed_kline = kline[::-1]
        price_array = [float(x[4]) for x in reversed_kline]
        av5 = sum(price_array[:5]) / 5
        av20 = sum(price_array[:20]) / 20

        last_av5 = sum(price_array[1:6]) / 5
        last_av20 = sum(price_array[1:21]) / 20
        if is_buy_vector(av5, av20) and not is_buy_vector(last_av5, last_av20) and av20 / last_av20 > (1 + r):
            self.type = 1
        elif is_sell_vector(av5, av20) and not is_sell_vector(last_av5, last_av20):
            self.type = -1
        else:
            self.type = 0

    def is_buy_point(self):
        return self.type > 0

    def is_sell_point(self):
        return self.type < 0

    def check_price(self):
        depth = okcoinSpot.depth(self.symbol)
        ask1 = depth['asks'][-1][0]
        bid1 = depth['bids'][0][0]
        return ask1, bid1


timers = {
    '3min': {'mod': 3 * 60, 'first': 10, 'interval': 3 * 60},

    '5min': {'mod': 5 * 60, 'first': 10, 'interval': 5 * 60},
    '4hour': {'mod': 4 * 60 * 60, 'first': 30, 'interval': 4 * 60 * 60}
}


def run(symbols, time_type):
    logger.info('start')

    account = Account(10000, symbols)
    coins = {x: Coin(x) for x in symbols}

    timer_info = timers[time_type]

    while True:
        t = int(time.time())
        if t % timer_info['mod'] < timer_info['first']:
            break
        else:
            time.sleep(timer_info['first'])
        pass

    while True:
        logger.info('check klines')

        for symbol in symbols:
            logger.info("checking:"+symbol)
            coins[symbol].check_kline(time_type)

        for symbol in symbols:

            if account.holding_symbol(symbol):
                coin = coins[symbol]
                if coin.is_sell_point():
                    (ask1, bid1) = coin.check_price()
                    sell_price = ask1 - 0.0001
                    account.sell(symbol, sell_price)
                    pass
                pass

        if account.has_money():
            for symbol in symbols:
                coin = coins[symbol]
                if coin.is_buy_point():
                    (ask1, bid1) = coin.check_price()
                    buy_price = bid1 + 0.0001
                    account.buy(symbol, buy_price)
                    pass
            pass

        time.sleep(timer_info['interval'])

        pass


run(["cic_usdt", "mith_usdt", "theta_usdt", "swftc_usdt", "nas_usdt", "trx_usdt", "pra_usdt", "mana_usdt","eos_usdt", "bch_usdt", "okb_usdt", "btm_usdt", "cmt_usdt", "ont_usdt", "wfee_usdt", "zip_usdt", "soc_usdt"], '4hour')

# test2('eos_usdt', 1, 0.08)
# result = []
# for s in ['eos_usdt', 'bch_usdt','okb_usdt','btm_usdt','cmt_usdt','ont_usdt']:
# 	for t in ['1hour', '4hour']:
# 		for k in [0, 0.0005, 0.0008, 0.0015, 0.03]:
# 			ratio = test(s, t, k)
# 			result.append(','.join([s, t, str(k)]) + ",   盈利率:"+str(ratio))
# all_symbols = ['btc_usdt','ltc_usdt','eth_usdt','okb_usdt','etc_usdt','bch_usdt','1st_usdt','aac_usdt','abt_usdt','ace_usdt','act_usdt','ae_usdt','aidoc_usdt','amm_usdt','ark_usdt','ast_usdt','atl_usdt','auto_usdt','avt_usdt','bcd_usdt','bec_usdt','bkx_usdt','bnt_usdt','brd_usdt','btg_usdt','btm_usdt','cag_usdt','cai_usdt','can_usdt','cbt_usdt','chat_usdt','cic_usdt','cmt_usdt','ctxc_usdt','cvc_usdt','dadi_usdt','dash_usdt','dat_usdt','dent_usdt','dgb_usdt','dgd_usdt','dna_usdt','dnt_usdt','dpy_usdt','edo_usdt','elf_usdt','eng_usdt','enj_usdt','eos_usdt','evx_usdt','fair_usdt','fun_usdt','gas_usdt','gnt_usdt','gnx_usdt','gsc_usdt','gtc_usdt','gto_usdt','hmc_usdt','hot_usdt','hsr_usdt','icn_usdt','icx_usdt','ins_usdt','insur_usdt','int_usdt','iost_usdt','iota_usdt','ipc_usdt','itc_usdt','kan_usdt','kcash_usdt','key_usdt','knc_usdt','la_usdt','lba_usdt','lend_usdt','lev_usdt','light_usdt','link_usdt','lrc_usdt','lsk_usdt','mag_usdt','mana_usdt','mco_usdt','mda_usdt','mdt_usdt','mith_usdt','mkr_usdt','mof_usdt','mot_usdt','mth_usdt','mtl_usdt','nano_usdt','nas_usdt','neo_usdt','ngc_usdt','nuls_usdt','oax_usdt','of_usdt','ok06ett_usdt','omg_usdt','ont_usdt','ost_usdt','pay_usdt','poe_usdt','ppt_usdt','pra_usdt','pst_usdt','qtum_usdt','qun_usdt','qvt_usdt','r_usdt','rcn_usdt','rct_usdt','rdn_usdt','read_usdt','ref_usdt','ren_usdt','req_usdt','rfr_usdt','rnt_usdt','salt_usdt','san_usdt','sc_usdt','show_usdt','snc_usdt','sngls_usdt','snm_usdt','snt_usdt','soc_usdt','spf_usdt','ssc_usdt','stc_usdt','storj_usdt','sub_usdt','swftc_usdt','tct_usdt','theta_usdt','tio_usdt','tnb_usdt','topc_usdt','tra_usdt','trio_usdt','true_usdt','trx_usdt','ubtc_usdt','uct_usdt','ugc_usdt','ukg_usdt','utk_usdt','vee_usdt','vib_usdt','viu_usdt','wfee_usdt','win_usdt','wrc_usdt','wtc_usdt','xem_usdt','xlm_usdt','xmr_usdt','xrp_usdt','xuc_usdt','yee_usdt','you_usdt','yoyo_usdt','zec_usdt','zen_usdt','zil_usdt','zip_usdt','zrx_usdt']
# suc = []
# fail = []
# for s in all_symbols:
# 	print("test:"+s)
# 	kline = okcoinSpot.kline(s, '1day', 30)

# 	vol = [float(x[-1]) for x in kline]
# 	avg_vol = sum(vol) / len(vol)
# 	if avg_vol > 2000000:
# 		suc.append(s)
# 	else:
# 		fail.append(s)

# print("suc:")
# print(suc)

# print("fail:")
# print(fail)

# test(['okb_usdt', 'etc_usdt', '1st_usdt', 'aac_usdt', 'act_usdt', 'aidoc_usdt', 'auto_usdt', 'btm_usdt', 'cai_usdt', 'can_usdt', 'chat_usdt', 'cic_usdt', 'cmt_usdt', 'cvc_usdt', 'dent_usdt', 'elf_usdt', 'enj_usdt', 'eos_usdt', 'fair_usdt', 'fun_usdt', 'gnt_usdt', 'gtc_usdt', 'hmc_usdt', 'hot_usdt', 'insur_usdt', 'int_usdt', 'iost_usdt', 'iota_usdt', 'kan_usdt', 'kcash_usdt', 'key_usdt', 'lba_usdt', 'light_usdt', 'lrc_usdt', 'mag_usdt', 'mana_usdt', 'mdt_usdt', 'mith_usdt', 'of_usdt', 'ont_usdt', 'pra_usdt', 'rct_usdt', 'rfr_usdt', 'rnt_usdt', 'sc_usdt', 'show_usdt', 'snt_usdt', 'soc_usdt', 'ssc_usdt', 'stc_usdt', 'swftc_usdt', 'tct_usdt', 'theta_usdt', 'tnb_usdt', 'topc_usdt', 'tra_usdt', 'trio_usdt', 'true_usdt', 'trx_usdt', 'ugc_usdt', 'viu_usdt', 'wfee_usdt', 'win_usdt', 'xlm_usdt', 'xrp_usdt', 'yee_usdt', 'you_usdt', 'zil_usdt', 'zip_usdt'], '4hour',0.03, 0.2)
# test(['eos_usdt'], '4hour',0.03)


# test("amm_usdtt",'1min',400)

# all_symbols = ['btc_usdt','ltc_usdt','eth_usdt','okb_usdt','etc_usdt','bch_usdt','1st_usdt','aac_usdt','abt_usdt','ace_usdt','act_usdt','ae_usdt','aidoc_usdt','amm_usdt','ark_usdt','ast_usdt','atl_usdt','auto_usdt','avt_usdt','bcd_usdt','bec_usdt','bkx_usdt','bnt_usdt','brd_usdt','btg_usdt','btm_usdt','cag_usdt','cai_usdt','can_usdt','cbt_usdt','chat_usdt','cic_usdt','cmt_usdt','ctxc_usdt','cvc_usdt','dadi_usdt','dash_usdt','dat_usdt','dent_usdt','dgb_usdt','dgd_usdt','dna_usdt','dnt_usdt','dpy_usdt','edo_usdt','elf_usdt','eng_usdt','enj_usdt','eos_usdt','evx_usdt','fair_usdt','fun_usdt','gas_usdt','gnt_usdt','gnx_usdt','gsc_usdt','gtc_usdt','gto_usdt','hmc_usdt','hot_usdt','hsr_usdt','icn_usdt','icx_usdt','ins_usdt','insur_usdt','int_usdt','iost_usdt','iota_usdt','ipc_usdt','itc_usdt','kan_usdt','kcash_usdt','key_usdt','knc_usdt','la_usdt','lba_usdt','lend_usdt','lev_usdt','light_usdt','link_usdt','lrc_usdt','lsk_usdt','mag_usdt','mana_usdt','mco_usdt','mda_usdt','mdt_usdt','mith_usdt','mkr_usdt','mof_usdt','mot_usdt','mth_usdt','mtl_usdt','nano_usdt','nas_usdt','neo_usdt','ngc_usdt','nuls_usdt','oax_usdt','of_usdt','ok06ett_usdt','omg_usdt','ont_usdt','ost_usdt','pay_usdt','poe_usdt','ppt_usdt','pra_usdt','pst_usdt','qtum_usdt','qun_usdt','qvt_usdt','r_usdt','rcn_usdt','rct_usdt','rdn_usdt','read_usdt','ref_usdt','ren_usdt','req_usdt','rfr_usdt','rnt_usdt','salt_usdt','san_usdt','sc_usdt','show_usdt','snc_usdt','sngls_usdt','snm_usdt','snt_usdt','soc_usdt','spf_usdt','ssc_usdt','stc_usdt','storj_usdt','sub_usdt','swftc_usdt','tct_usdt','theta_usdt','tio_usdt','tnb_usdt','topc_usdt','tra_usdt','trio_usdt','true_usdt','trx_usdt','ubtc_usdt','uct_usdt','ugc_usdt','ukg_usdt','utk_usdt','vee_usdt','vib_usdt','viu_usdt','wfee_usdt','win_usdt','wrc_usdt','wtc_usdt','xem_usdt','xlm_usdt','xmr_usdt','xrp_usdt','xuc_usdt','yee_usdt','you_usdt','yoyo_usdt','zec_usdt','zen_usdt','zil_usdt','zip_usdt','zrx_usdt']
# all_type = ['1min','3min','5min','15min','30min','1day','3day','1week','1hour','2hour','4hour','6hour','12hour']
# all_symbols = ['eos_usdt']
# all_type = ['4hour','6hour','12hour']
# size = 4000
# for symbol in all_symbols:
# 	for type in all_type:
# 		test2(symbol, type, size)


# print (u' 现货历史交易信息 ')
# print (okcoinSpot.trades())

# print (u' 用户现货账户信息 ')
# print (okcoinSpot.userinfo())

# print (u' 现货下单 ')
# print (okcoinSpot.trade('ltc_usdt','buy','0.1','0.2'))

# print (u' 现货批量下单 ')
# print (okcoinSpot.batchTrade('ltc_usdt','buy','[{price:0.1,amount:0.2},{price:0.1,amount:0.2}]'))

# print (u' 现货取消订单 ')
# print (okcoinSpot.cancelOrder('ltc_usdt','18243073'))

# print (u' 现货订单信息查询 ')
# print (okcoinSpot.orderinfo('ltc_usdt','18243644'))

# print (u' 现货批量订单信息查询 ')
# print (okcoinSpot.ordersinfo('ltc_usdt','18243800,18243801,18243644','0'))

# print (u' 现货历史订单信息查询 ')
# print (okcoinSpot.orderHistory('ltc_usdt','0','1','2'))

# print (u' 期货行情信息')
# print (okcoinFuture.future_ticker('ltc_usdt','this_week'))

# print (u' 期货市场深度信息')
# print (okcoinFuture.future_depth('btc_usdt','this_week','6'))

# print (u'期货交易记录信息')
# print (okcoinFuture.future_trades('ltc_usdt','this_week'))

# print (u'期货指数信息')
# print (okcoinFuture.future_index('ltc_usdt'))

# print (u'美元人民币汇率')
# print (okcoinFuture.exchange_rate())

# print (u'获取预估交割价')
# print (okcoinFuture.future_estimated_price('ltc_usdt'))

# print (u'获取全仓账户信息')
# print (okcoinFuture.future_userinfo())

# print (u'获取全仓持仓信息')
# print (okcoinFuture.future_position('ltc_usdt','this_week'))

# print (u'期货下单')
# print (okcoinFuture.future_trade('ltc_usdt','this_week','0.1','1','1','0','20'))

# print (u'期货批量下单')
# print (okcoinFuture.future_batchTrade('ltc_usdt','this_week','[{price:0.1,amount:1,type:1,match_price:0},{price:0.1,amount:3,type:1,match_price:0}]','20'))

# print (u'期货取消订单')
# print (okcoinFuture.future_cancel('ltc_usdt','this_week','47231499'))

# print (u'期货获取订单信息')
# print (okcoinFuture.future_orderinfo('ltc_usdt','this_week','47231812','0','1','2'))

# print (u'期货逐仓账户信息')
# print (okcoinFuture.future_userinfo_4fix())

# print (u'期货逐仓持仓信息')
# print (okcoinFuture.future_position_4fix('ltc_usdt','this_week',1))
