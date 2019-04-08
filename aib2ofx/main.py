#!/usr/bin/env python
# coding: utf-8

import codecs, datetime, errno, optparse, os, re, sys

from aib2ofx import aib, cfg, ofx


def getOptions():
    parser = optparse.OptionParser()
    option_list = [
        optparse.make_option(
            '-d', '--output-dir',
            dest='output_dir', help='directory to put OFX files in [/tmp]'
        ),
        optparse.make_option(
            '-D', '--debug', action='store_true',
            dest='debug_mode', help='display some debug output [False]'
        ),
        optparse.make_option(
            '-q', '--quiet', action='store_true',
            dest='quiet_mode', help='display no output at all [False]'
        ),
    ]
    parser.add_options(option_list)
    output_dir = os.path.join('.', datetime.date.today().strftime('%Y-%m-%d'))
    parser.set_defaults(output_dir=output_dir, debug_mode=False,
            quiet_mode=False)
    return parser.parse_args()


def writeFile(account_data, output_dir, user, accountId, formatter):
    f = codecs.open(
        '%s/%s_%s.ofx' % (output_dir, user, accountId),
        'w',
        'utf-8'
    )
    f.write(formatter.prettyprint(account_data).encode('utf-8'))
    f.close


def getData(user, config, output_dir, formatter, chatter):

    def show_and_tell(pre, function, post='done.'):
        if (chatter['quiet']):
            function(chatter)
        else:
            print pre,
            sys.stdout.flush()
            function(chatter)
            print post


    cleanup_re = re.compile('[- 	]+')

    # Login to the bank, scrape data for all accounts.
    creds = config[user]
    bank = aib.aib(creds, chatter)
    show_and_tell('Logging in as \'%s\'...' % user, bank.login)
    show_and_tell('Scraping account pages for data...', bank.scrape)
    show_and_tell('Logging \'%s\' out...' % user, bank.bye)

    # Save each account to separate OFX file.
    for account in bank.getdata().values():
        if not account:
            continue
        name = re.sub(cleanup_re,
                      '_',
                      account['accountId']).lower()
        writeFile(account, output_dir, user, name, formatter)


def main():
    # Parse command line options.
    (options, args) = getOptions()
    chatter = {
        'quiet': options.quiet_mode,
        'debug': options.debug_mode,
    }

    # Read user-provided credentials.
    config = cfg.config()
    formatter = ofx.ofx()

    try:
        os.makedirs(options.output_dir)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    # Iterate through accounts, scrape, format and save data.
    for user in config.users():
        getData(user, config, options.output_dir, formatter,
                chatter)


if __name__ == '__main__':
    main()
