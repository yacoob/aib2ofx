#!/usr/bin/env python
# coding: utf-8

import re

import aib, cfg, ofx

def main():
    cleanup_re = re.compile('[- 	]+')
    config = cfg.config()
    formatter = ofx.ofx()

    for user in config.users():
        creds = config[user]
        bank = aib.aib(creds)
        bank.login()
        bank.scrape()
        bank.bye()

        for account in bank.getdata().values():
            name = re.sub(cleanup_re,
                          '_',
                          account['accountId']).lower()
            f = open('/tmp/%s_%s.ofx' % (user, name),
                     'w')
            f.write(formatter.prettyprint(account))
            f.close

if __name__ == '__main__':
    main()
