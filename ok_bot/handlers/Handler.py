
import json
import os
class Handler(object):

    def __init__(self, notify):
        file = self.cfgFile()
        self.cfg = {}
        if file:
            d = os.path.dirname(__file__)
            with open(os.path.join(d, file)) as d:
                self.cfg = json.load(d)
        self.notify = notify

    def cfgFile(self):
        return None


    def get_cfg_symbols_set(self):
        return set(self.cfg.keys())
