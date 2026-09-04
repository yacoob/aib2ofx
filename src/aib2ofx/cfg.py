"""Configuration file handling for aib2ofx."""

import json
import os
import re

DEFAULT_CONFIG_FILE = '~/.aib2ofx.json'


class Config:
    """Simple dictionary-like config object."""

    def __init__(self, config_filename=DEFAULT_CONFIG_FILE):
        """Read and parse the config file at config_filename."""
        with open(os.path.expanduser(config_filename)) as filepath:
            config_string = filepath.read(-1)

        # Kill trailing commas.
        trailing_commas = re.compile(r',\s*([\]}])')
        config_string = trailing_commas.sub(r'\g<1>', config_string)
        self.cfg = json.loads(config_string)

    def get_config(self):
        """Return the entire config object."""
        return self.cfg

    def users(self):
        """Return the list of configured users."""
        return list(self.cfg.keys())

    def __getitem__(self, name):
        """Return the credentials of a single user."""
        if name in self.cfg:
            return self.cfg[name]
        raise AttributeError
