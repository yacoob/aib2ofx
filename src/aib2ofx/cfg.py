"""Configuration file handling for aib2ofx."""

import json
import os
import re


class Config:
    """Simple dictionary-like config object."""

    def __init__(self, config_filename='~/.aib2ofx.json'):
        filepath = open(os.path.expanduser(config_filename))
        config_string = filepath.read(-1)
        filepath.close()

        # Kill trailing commas.
        trailing_commas = re.compile(r',\s*([\]}])')
        config_string = trailing_commas.sub(r'\g<1>', config_string)
        self.cfg = json.loads(config_string)

    def get_config(self):
        """Returns the entire config object."""
        return self.cfg

    def users(self):
        """Returns list of configured users."""
        return list(self.cfg.keys())

    def __getitem__(self, name):
        if name in self.cfg:
            return self.cfg[name]
        raise AttributeError
