#!/usr/bin/python
# -*- coding: utf-8 -*-
# encoding: utf-8
#客户端调用，扫描指定币种集合

from OkcoinSpotAPI import OKCoinSpot
from OkcoinFutureAPI import OKCoinFuture
import time
#初始化apikey，secretkey,url
apikey = '52928f7e-a6ea-4cc5-b6fb-458cc150dd2b'
secretkey = 'BB1F6ACEC90BCD53A25FEFA2250D14CF'
okcoinRESTURL = 'www.okb.com'   #请求注意：国内账号需要 修改为 www.okcoin.cn  

#现货API
okcoinSpot = OKCoinSpot(okcoinRESTURL,apikey,secretkey)


r = -0.005
a = 0.08


def getAV(prices, length):
	size = len(prices)
	av=[sum(prices[0:length]) / length]
	head = length
	while head < size:
		v = av[-1]
		v -= (prices[head-length] / length)
		v += (prices[head] / length)
		av.append(v)
		head+=1
		pass
	return av

def is_buy_vector(av5, av20):
	return av5 > av20

def is_sell_vector(av5, av20):
	return av5 < av20

#0表示买点和卖点
#1表示只找买点
#-1表示只找卖点
def find_alert(kline_data, k, alert_type=0):
	new_kline = kline_data[::-1]

	for kk in new_kline:
		kk.append(0)

	price_array = [float(x[4]) for x in new_kline]

	av5=getAV(price_array, 5)
	av20=getAV(price_array, 20)

	alerts = []
	for i in range(len(av20) - 1):
		kline = new_kline[i]
		if is_buy_vector(av5[i], av20[i]) and not is_buy_vector(av5[i+1],  av20[i+1]) and av20[i] / av20[i+1] > (1+r):
			#买入点
			if alert_type == 0 or alert_type == 1:
				kline[-1] = 1
		elif is_sell_vector(av5[i], av20[i]) and not is_sell_vector(av5[i+1],  av20[i+1]):
			#卖出点
			if alert_type == 0 or alert_type == -1:
				kline[-1] = -1
				pass
		elif (av5[i] - av5[i+1]) / av5[i+1] < -k:
			if alert_type == 0 or alert_type == -1:
				kline[-1] = -2
				pass

			

	return new_kline[::-1]


def format_kline(kline):
	timestamp = kline[0]
	return "时间:%s 收盘价:%s" % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp/1000)), kline[4])

class MyCoin(object):
	kline=None
	symbol=None
	count=0
	cur_time=0
	holding = False

	buy_price = 0

	def __init__(self, symbol, kline, start_time):
		self.kline=kline
		self.symbol=symbol
		self.cur_time = start_time

	def forward_time_to(self, t):
		self.cur_time = t


	def kline_at_this_time(self):
		for x in self.kline:
			if x[0] > self.cur_time:
				return None
			if x[0] == self.cur_time:
				return x

		return None

	def buy(self, money, price):
		self.count += money / price * 0.998
		self.buy_price = price
		self.holding = True

	def sell(self, price):
		money = self.count * price * 0.998
		self.count =0
		self.holding = False
		return money

	def win_ratio(self, price):
		return price / self.buy_price - 1

	def test_sell(self,price):
		return self.count * price * 0.998



delta = 14400000


def test(symbols, type, k, m):
	#kline_data为时间倒序排列
	print("\n\n回测:%s ,%s" %(symbols, type))

	o_klines = [ okcoinSpot.kline(s, type, 4000) for s in symbols]

	min_time = o_klines[0][0][0]
	max_time = o_klines[0][-1][0]
	for x in o_klines:
		if x[0][0] < min_time:
			min_time = x[0][0]
		if x[-1][0] > max_time:
			max_time = x[-1][0]

	klines = {symbols[i] : o_klines[i] for i in range(len(symbols))}
	alerts = {s : find_alert(v, k) for s,v in klines.items()}

	coins = {}

	for s, v in alerts.items():
		coins[s] = MyCoin(s, v, min_time)


	currentMoney = 10000
	holdingSymbol = None

	t = min_time
	while t <= max_time:

		time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t/1000))
		current_status = {}

		for s,v in coins.items():
			v.forward_time_to(t)
			kline = v.kline_at_this_time()
			current_status[s] = kline


		#当前持币
		if holdingSymbol:

			#所持币到达卖点，卖出
			coin = coins[holdingSymbol]
			kline = coin.kline_at_this_time()
			if kline and kline[-1] < 0:
				print("到达卖出点，时间:%s, 卖出%s, 盈利:%f" % (time_str,holdingSymbol, float(kline[4])/coin.buy_price - 1))
				currentMoney = coin.sell(float(kline[4]))
				holdingSymbol = None
			# elif coin.win_ratio(float(kline[4])) > m:
			# 	#没有到达卖点，看看其他的币有没有到达买点，并且盈利超过m
			# 	for s in symbols:
			# 		other_coin = coins[s]
			# 		other_kline = other_coin.kline_at_this_time()
			# 		if other_kline and other_kline[-1] > 0:

			# 			print("换币，时间:%s, 卖出%s, 买入%s 盈利:%f" % (time_str,holdingSymbol, s, float(kline[4])/coin.buy_price - 1))
			# 			currentMoney = coin.sell(float(kline[4]))
			# 			holdingSymbol = None

			# 			holdingSymbol = s
			# 			other_coin.buy(currentMoney,float(other_kline[4]))
			# 			currentMoney = 0
			# 			break


			#卖出后，看看有没有到达买点的币
			if not holdingSymbol:
				
				for s in symbols:
					coin = coins[s]
					kline = coin.kline_at_this_time()
					if kline and kline[-1] > 0:
						holdingSymbol = s
						coin.buy(currentMoney,float(kline[4]))
						currentMoney = 0
						print("到达买入点，时间:%s, 买入:%s" %(time_str, s))
						break

		else:
			#找到一个处于买点的币，买入
			for s in symbols:
				coin = coins[s]
				kline = coin.kline_at_this_time()
				if kline and kline[-1] > 0:
					holdingSymbol = s
					coin.buy(currentMoney,float(kline[4]))
					currentMoney = 0
					print("到达买入点，时间:%s, 买入:%s" %(time_str, s))
					break

		t += delta

		pass

	totalmoney = 0
	if not holdingSymbol:
		totalmoney = currentMoney
	else:
		kline = klines[holdingSymbol]
		coin = coins[holdingSymbol]
		totalmoney = coin.sell(float(klines[holdingSymbol][-1][4]))

	print("总盈利:%f" % (totalmoney / 10000 -1))

	return totalmoney / 10000 - 1

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


test(['okb_usdt', 'etc_usdt', '1st_usdt', 'aac_usdt', 'act_usdt', 'aidoc_usdt', 'auto_usdt', 'btm_usdt', 'cai_usdt', 'can_usdt', 'chat_usdt', 'cic_usdt', 'cmt_usdt', 'cvc_usdt', 'dent_usdt', 'elf_usdt', 'enj_usdt', 'eos_usdt', 'fair_usdt', 'fun_usdt', 'gnt_usdt', 'gtc_usdt', 'hmc_usdt', 'hot_usdt', 'insur_usdt', 'int_usdt', 'iost_usdt', 'iota_usdt', 'kan_usdt', 'kcash_usdt', 'key_usdt', 'lba_usdt', 'light_usdt', 'lrc_usdt', 'mag_usdt', 'mana_usdt', 'mdt_usdt', 'mith_usdt', 'of_usdt', 'ont_usdt', 'pra_usdt', 'rct_usdt', 'rfr_usdt', 'rnt_usdt', 'sc_usdt', 'show_usdt', 'snt_usdt', 'soc_usdt', 'ssc_usdt', 'stc_usdt', 'swftc_usdt', 'tct_usdt', 'theta_usdt', 'tnb_usdt', 'topc_usdt', 'tra_usdt', 'trio_usdt', 'true_usdt', 'trx_usdt', 'ugc_usdt', 'viu_usdt', 'wfee_usdt', 'win_usdt', 'xlm_usdt', 'xrp_usdt', 'yee_usdt', 'you_usdt', 'zil_usdt', 'zip_usdt'], '4hour',0.03, 0.2)
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


#print (u' 现货历史交易信息 ')
#print (okcoinSpot.trades())

#print (u' 用户现货账户信息 ')
#print (okcoinSpot.userinfo())

#print (u' 现货下单 ')
#print (okcoinSpot.trade('ltc_usdt','buy','0.1','0.2'))

#print (u' 现货批量下单 ')
#print (okcoinSpot.batchTrade('ltc_usdt','buy','[{price:0.1,amount:0.2},{price:0.1,amount:0.2}]'))

#print (u' 现货取消订单 ')
#print (okcoinSpot.cancelOrder('ltc_usdt','18243073'))

#print (u' 现货订单信息查询 ')
#print (okcoinSpot.orderinfo('ltc_usdt','18243644'))

#print (u' 现货批量订单信息查询 ')
#print (okcoinSpot.ordersinfo('ltc_usdt','18243800,18243801,18243644','0'))

#print (u' 现货历史订单信息查询 ')
#print (okcoinSpot.orderHistory('ltc_usdt','0','1','2'))

#print (u' 期货行情信息')
#print (okcoinFuture.future_ticker('ltc_usdt','this_week'))

#print (u' 期货市场深度信息')
#print (okcoinFuture.future_depth('btc_usdt','this_week','6'))

#print (u'期货交易记录信息') 
#print (okcoinFuture.future_trades('ltc_usdt','this_week'))

#print (u'期货指数信息')
#print (okcoinFuture.future_index('ltc_usdt'))

#print (u'美元人民币汇率')
#print (okcoinFuture.exchange_rate())

#print (u'获取预估交割价') 
#print (okcoinFuture.future_estimated_price('ltc_usdt'))

#print (u'获取全仓账户信息')
#print (okcoinFuture.future_userinfo())

#print (u'获取全仓持仓信息')
#print (okcoinFuture.future_position('ltc_usdt','this_week'))

#print (u'期货下单')
#print (okcoinFuture.future_trade('ltc_usdt','this_week','0.1','1','1','0','20'))

#print (u'期货批量下单')
#print (okcoinFuture.future_batchTrade('ltc_usdt','this_week','[{price:0.1,amount:1,type:1,match_price:0},{price:0.1,amount:3,type:1,match_price:0}]','20'))

#print (u'期货取消订单')
#print (okcoinFuture.future_cancel('ltc_usdt','this_week','47231499'))

#print (u'期货获取订单信息')
#print (okcoinFuture.future_orderinfo('ltc_usdt','this_week','47231812','0','1','2'))

#print (u'期货逐仓账户信息')
#print (okcoinFuture.future_userinfo_4fix())

#print (u'期货逐仓持仓信息')
#print (okcoinFuture.future_position_4fix('ltc_usdt','this_week',1))



   
