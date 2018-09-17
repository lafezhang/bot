import Utils
import sqlite3
import time
import ok_api
import json
import threading
import shutil
# 初始化apikey，secretkey,url
# 初始化apikey，secretkey,url
apikey = '52928f7e-a6ea-4cc5-b6fb-458cc150dd2b'
secretkey = 'BB1F6ACEC90BCD53A25FEFA2250D14CF'
okcoinRESTURL = 'www.okb.com'  # 请求注意：国内账号需要 修改为 www.okcoin.cn

# 现货API


class SymbolDB(object):

    def __init__(self, folder, symbol):
        self.append_count = 0
        self.conn = sqlite3.connect(folder + '/' + symbol + ".db")
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE orders (tid INTEGER PRIMARY KEY,
                                  date_ms CHAR(15),
                                  amount NUMBER,
                                  type CHAR(1),
                                  price NUMBER);
            ''')
        self.conn.commit()
        self.last_commit_time = 0
        self.empty_count = 0

    def append(self, order_json):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO orders (tid, date_ms,amount,type,price) VALUES (?,?,?,?,?)
            ''', (order_json['tid'], order_json['date_ms'], order_json['amount'], order_json['type'][0], order_json['price']))
        self.try_commit()

    def append_empty(self):
        self.append({
            'tid':self.empty_count,
            'date_ms':time.time()*1000,
            'amount':0,
            'type':'none',
            'price':0
        })
        self.empty_count+=1

    def try_commit(self):
        if time.time() - self.last_commit_time > 5*60:
            self.commit()

    def commit(self):
        self.conn.commit()
        self.last_commit_time = time.time()



class SymbolCapture(object):
    def __init__(self, folder, symbol):
        self.symbol = symbol
        self.folder = folder
        self.api = ok_api.OKCoinSpot(okcoinRESTURL, apikey, secretkey)

    def start(self):

        self.db = SymbolDB(self.folder, self.symbol)
        last_order_id = 0
        while True:
            try:
                while True:
                    orders = self.api.trades(self.symbol, last_order_id)
                    if len(orders) > 0:
                        last_order_id = orders[-1]['tid']

                    for o in orders:
                        self.db.append(o)

                    if len(orders) < 10:
                        break

            except Exception as e:
                self.db.append_empty()
                self.db.commit()

            time.sleep(5)

def run_capture(s):
    s.start()

def run():

    from_time = time.time()
    folder_name = "capture_orders/" + time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime(from_time)) + "-" + str(
        int((from_time - int(from_time)) * 1000))

    Utils.mkdir(folder_name)

    with open("capture_cfg.json") as d:
        aa = json.load(d)
        symbols = aa["symbols"]

    cc = []
    threads = []
    for s in symbols:
        capt = SymbolCapture(folder_name, s)
        cc.append(capt)
        t = threading.Thread(target=run_capture, args=(capt, ))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    t = time.time()
    dest_folder =folder_name + "~" + time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime(t)) + "-" + str(
        int((t - int(t)) * 1000))
    shutil.move(folder_name, dest_folder)


while True:
    run()

    time.sleep(10)


