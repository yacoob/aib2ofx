#!/usr/bin/env python
# coding: utf-8

import json, os

class config:
    def __init__(self, config_filename='~/.aib-sucker'):
        fp = open(os.path.expanduser(config_filename))
        self.cfg = json.load(fp)
        fp.close()

    def get_config(self):
        return self.cfg

    def users(self):
        return self.cfg.keys()

    def __getitem__(self, name):
        if self.cfg.has_key(name):
            return self.cfg[name]
        else:
            raise AttributeError
