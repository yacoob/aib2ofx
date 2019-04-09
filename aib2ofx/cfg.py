#!/usr/bin/env python
# coding: utf-8

import json
import os
import re


class config:
    def __init__(self, config_filename='~/.aib2ofx.json'):
        fp = open(os.path.expanduser(config_filename))
        config_string = fp.read(-1)
        fp.close()

        # Kill trailing commas.
        trailing_commas = re.compile(r',\s*([\]}])')
        config_string = trailing_commas.sub(r'\g<1>', config_string)
        self.cfg = json.loads(config_string)

    def get_config(self):
        return self.cfg

    def users(self):
        return self.cfg.keys()

    def __getitem__(self, name):
        if name in self.cfg:
            return self.cfg[name]
        else:
            raise AttributeError
