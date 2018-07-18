
from .Handler import Handler
import sqlite3
import time
import json
import shutil
import os

def mkdir(path):
    folder = os.path.exists(path)
    if not folder:  # 判断是否存在文件夹如果不存在则创建为文件夹
        os.makedirs(path)  # makedirs 创建文件时如果路径不存在会创建这个路径

class SymbolDB(object):

    def __init__(self, folder, symbol):
        self.append_count = 0
        self.conn = sqlite3.connect(folder + '/' + symbol + ".db")
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE message (ID INTEGER PRIMARY KEY autoincrement,
                                  type CHAR(50),
                                  message TEXT,
                                  ts DATETIME DEFAULT (datetime('now','localtime')));
            ''')
        self.conn.commit()
        self.last_commit_time = 0

    def append(self, type, message):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO message (type, message) VALUES (?,?)
            ''', (type, message,))
        self.try_commit()

    def try_commit(self):
        if time.time() - self.last_commit_time > 5*60:
            self.commit()

    def commit(self):
        self.conn.commit()
        self.last_commit_time = time.time()

    def append_deals(self, deals):
        self.append("deal", deals)

    def append_depth(self, depth):
        self.append("depth", depth)


class CaptureHandler(Handler):
    def __init__(self, notify):
        super().__init__(notify)
        self.dbs = {}
        from_time = time.time()
        folder_name = "capture/" + time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime(from_time)) + "-" + str(
            int((from_time - int(from_time)) * 1000))

        mkdir(folder_name)
        self.folder_name=folder_name

    def getDB(self, symbol):
        if symbol not in self.dbs:
            self.dbs[symbol] = SymbolDB(self.folder_name,symbol)
        db = self.dbs[symbol]
        return db

    def OnNewDeals(self, deals, symbol, ts):
        self.getDB(symbol).append_deals( json.dumps(deals))

    def OnNewDepth(self, depth, symbol, ts):
        self.getDB(symbol).append_depth(json.dumps(depth))

    def close(self):
        for k, v in self.dbs.items():
            v.commit()
        t = time.time()
        dest_folder = self.folder_name+"~"+time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime(t)) + "-" + str(
            int((t - int(t)) * 1000))
        shutil.move(self.folder_name, dest_folder)