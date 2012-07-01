#!/usr/bin/env python
# coding: utf-8

import json, os, re


class config:
    def __init__(self, config_filename='~/.aib-sucker'):
        fp = open(os.path.expanduser(config_filename))
        config_string = fp.read(-1)
        fp.close()

        # Kill trailing commas.
        trailing_commas = re.compile(',\s*([\]}])')
        config_string = trailing_commas.sub('\g<1>', config_string)
        self.cfg = json.loads(config_string)


    def get_config(self):
        return self.cfg


    def users(self):
        return self.cfg.keys()


    def __getitem__(self, name):
        if self.cfg.has_key(name):
            return self.cfg[name]
        else:
            raise AttributeError
