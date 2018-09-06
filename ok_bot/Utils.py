import os
import time

def mkdir(path):
    folder = os.path.exists(path)
    if not folder:  # 判断是否存在文件夹如果不存在则创建为文件夹
        os.makedirs(path)  # makedirs 创建文件时如果路径不存在会创建这个路径

def time_str(ts = None):
    tt = ts
    if not ts:
        tt = time.time()
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tt))

def singleton(cls, *args, **kw):
    instances = {}
    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]
    return _singleton
