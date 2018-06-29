#!/usr/bin/python
# -*- coding: utf-8 -*-
# encoding: utf-8
#客户端调用，用于查看API返回结果

from OkcoinSpotAPI import OKCoinSpot
from OkcoinFutureAPI import OKCoinFuture
import time
#初始化apikey，secretkey,url
apikey = '52928f7e-a6ea-4cc5-b6fb-458cc150dd2b'
secretkey = 'BB1F6ACEC90BCD53A25FEFA2250D14CF'
okcoinRESTURL = 'www.okb.com'   #请求注意：国内账号需要 修改为 www.okcoin.cn  

#现货API
okcoinSpot = OKCoinSpot(okcoinRESTURL,apikey,secretkey)

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
def find_alert(kline_data, alert_type=0):
	price_array = [float(x[4]) for x in kline_data]

	av5=getAV(price_array, 5)
	av20=getAV(price_array, 20)

	alerts = []
	for i in range(len(av20) - 1):
		if is_buy_vector(av5[i], av20[i]) and not is_buy_vector(av5[i+1],  av20[i+1]):
			#买入点
			if alert_type == 0 or alert_type == 1:
				alerts.append({"kline":kline_data[i], "alert":1})
		elif is_sell_vector(av5[i], av20[i]) and not is_sell_vector(av5[i+1],  av20[i+1]):
			#卖出点
			if alert_type == 0 or alert_type == -1:
				alerts.append({"kline":kline_data[i], "alert":-1})
				pass
			

	alerts.reverse()
	return alerts

def format_kline(kline):
	timestamp = kline[0]
	return "时间:%s 收盘价:%s" % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp/1000)), kline[4])

def test(symbol, type, size):
	#kline_data为时间倒序排列
	print("\n\n回测:%s ,%s" %(symbol, type))
	kline_data = okcoinSpot.kline(symbol, type, size)
	if not isinstance(kline_data, list):
		print("获取K线失败：")
		print(kline_data)
		return
	kline_data.reverse()

	alerts = find_alert(kline_data)
	currentMoney = 10000
	currentCoin = 0
	last_buy_price = 0
	for alert in alerts:
		kline = alert['kline']
		price = float(kline[4])
		if alert['alert'] > 0:
			#买入点
			if currentMoney > 0.001:
				#还有钱可以买入
				coin = currentMoney / price
				currentCoin=coin
				currentMoney = 0
				last_buy_price = price
				print(u"买入点  %s" % (format_kline(kline)))
			pass
		elif currentCoin > 0.001:
			money = currentCoin * price

			currentCoin = 0
			currentMoney = money
			print(u"卖出点  %s, 盈利：%f" % (format_kline(kline), (price-last_buy_price) / last_buy_price))
			pass

	print("当前资产 --- money:%f  coin:%f  totalmoney:%f" % (currentMoney, currentCoin, currentCoin*float(kline_data[0][4])+currentMoney))


r = -0.005
a = 0.08


def test3(kline1):
	currentMoney = 10000
	currentCoin = 0


	kline1_index = 30
	while kline1_index < len(kline1):
		last_buy_price = 0
		#找买点
		this_data = kline1[kline1_index]
		last_data = kline1[kline1_index-1]

		if this_data[-2] > this_data[-1] and last_data[-2] < last_data[-1] and this_data[-1] / last_data[-1] > (1+r) :

			price = float(this_data[4])
			coin = currentMoney / price * 0.998
			currentCoin=coin
			currentMoney = 0
			last_buy_price = price
			# print(u"买入点  %s, -----r=%f" % (format_kline(this_data), this_data[-1] / last_data[-1] -1))
			kline1_index+=1
		else:
			kline1_index+=1
			continue

		
		while kline1_index < len(kline1):
			#找卖点
			this_data = kline1[kline1_index]
			last_data = kline1[kline1_index-1]
			price = float(this_data[4])
			if this_data[-2] < this_data[-1] and last_data[-2] > last_data[-1] :
				money = currentCoin * price * 0.998
				currentCoin = 0
				currentMoney = money
				# print(u"卖出点1  %s, 盈利：%f" % (format_kline(this_data), (price-last_buy_price) / last_buy_price))
				
				break
			else:
				pass
				# if (price - last_buy_price) / last_buy_price >= AAA:
				# 	t = this_data[0]
				# 	if t in kline2_by_time:
				# 		this_data2 = kline2_by_time[t]['data']
				# 		index = kline2_by_time[t]['index']
				# 		if this_data2[-1] > this_data2[-2]:

				# 			money = currentCoin * price
				# 			currentCoin = 0
				# 			currentMoney = money
				# 			print(u"卖出点2  %s, 盈利：%f, 4小时MA5:%f, MA20:%f" % (format_kline(this_data2), (price-last_buy_price) / last_buy_price, this_data2[-2], this_data2[-1]))
				# 			break

			kline1_index+=1

	yyy = (currentCoin*float(kline1[-1][4])+currentMoney) / 10000 -1
	# print("盈利率:%f" % (yyy))
	return yyy

def test4(kline1, k):
	currentMoney = 10000
	currentCoin = 0


	kline1_index = 30
	while kline1_index < len(kline1):
		last_buy_price = 0
		#找买点
		this_data = kline1[kline1_index]
		last_data = kline1[kline1_index-1]

		if this_data[-2] > this_data[-1] and last_data[-2] < last_data[-1] and this_data[-1] / last_data[-1] > (1+r) :

			price = float(this_data[4])
			coin = currentMoney / price * 0.998
			currentCoin=coin
			currentMoney = 0
			last_buy_price = price
			# print(u"买入点  %s, -----r=%f" % (format_kline(this_data), this_data[-1] / last_data[-1] -1))
			kline1_index+=1
		else:
			kline1_index+=1
			continue

		
		while kline1_index < len(kline1):
			#找卖点
			this_data = kline1[kline1_index]
			last_data = kline1[kline1_index-1]
			price = float(this_data[4])
			if this_data[-2] < this_data[-1] and last_data[-2] > last_data[-1] :
				money = currentCoin * price * 0.998
				currentCoin = 0
				currentMoney = money
				# print(u"卖出点1  %s, 盈利：%f" % (format_kline(this_data), (price-last_buy_price) / last_buy_price))
				
				break
			elif (this_data[-2] - last_data[-2]) / last_data[-2] < -k:
				money = currentCoin * price * 0.998
				currentCoin = 0
				currentMoney = money
				# print(u"卖出点2  %s, 盈利：%f" % (format_kline(this_data), (price-last_buy_price) / last_buy_price))
				
				break
				pass
				# if (price - last_buy_price) / last_buy_price >= AAA:
				# 	t = this_data[0]
				# 	if t in kline2_by_time:
				# 		this_data2 = kline2_by_time[t]['data']
				# 		index = kline2_by_time[t]['index']
				# 		if this_data2[-1] > this_data2[-2]:

				# 			money = currentCoin * price
				# 			currentCoin = 0
				# 			currentMoney = money
				# 			print(u"卖出点2  %s, 盈利：%f, 4小时MA5:%f, MA20:%f" % (format_kline(this_data2), (price-last_buy_price) / last_buy_price, this_data2[-2], this_data2[-1]))
				# 			break

			kline1_index+=1
	yyy = (currentCoin*float(kline1[-1][4])+currentMoney) / 10000 -1
	# print("盈利率:%f" % (yyy))
	return yyy


def test2(symbol, level, AAA):

	level_type = {1:"1hour", 2:"4hour", 3:"12hour"}
	#kline_data为时间倒序排列
	print("\n\n回测:%s ,level:%s" %(symbol, level_type[level]))

	kline1 = okcoinSpot.kline(symbol, level_type[level], 2000)
	kline2 = okcoinSpot.kline(symbol, level_type[level + 1], 2000)

	for x in [kline1, kline2]:
		for i in range(len(x)):
			data = x[i]
			if i < 4:
				data.append(-1)
			else:
				price_array = [float(a[4]) for a in kline1[i-4:i+1]] 
				av5 = sum( price_array) / 5
				data.append(av5)

			if i < 19:
				data.append(-1)
			else:
				av20 = sum([float(a[4]) for a in kline1[i-19:i+1]] ) / 20
				data.append(av20)


	print("比较: yyy0:%f,  yyy0.0008:%f, yyy0.0005:%f, yyy0.0015:%f, yyy0.03:%f, yyy0.05:%f" %(test3(kline1), test4(kline1,0.0008), test4(kline1, 0.0005), test4(kline1, 0.015), test4(kline1,0.03), test4(kline1,0.05)))


# test2('eos_usdt', 1, 0.08)
for s in ['eos_usdt', 'bch_usdt','okb_usdt','btm_usdt','cmt_usdt','ont_usdt']:
	for t in [1, 2]:
		for aa in [0.08]:
			test2(s, t,aa)
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



   
