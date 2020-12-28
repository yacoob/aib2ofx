"""Command line interface of aib2ofx."""

import argparse
import datetime
import errno
import os
import re
import sys

import dateutil.parser as dparser

from . import aib
from . import cfg
from . import ofx


def get_options():
    """Parse argv into options."""
    parser = argparse.ArgumentParser(
        description='Download data from aib.ie in OFX format'
    )
    parser.add_argument(
        '-d',
        '--output-dir',
        default=os.path.join('.', datetime.date.today().strftime('%Y-%m-%d')),
        dest='output_dir',
        help='directory to put OFX files in [%(default)s]',
    )
    parser.add_argument(
        '-D',
        '--debug',
        action='store_true',
        default=False,
        dest='debug_mode',
        help='display some debug output [%(default)s]',
    )
    parser.add_argument(
        '-q',
        '--quiet',
        action='store_true',
        default=False,
        dest='quiet_mode',
        help='display no output at all [%(default)s]',
    )
    parser.add_argument(
        '-l',
        '--later-than',
        dest='later_than',
        help='exports only transactions later than specified date (YYYY-MM-DD)',
    )
    return parser.parse_args()


def write_file(output_dir, user, account_id, contents):
    """Save parsed data to a file."""
    outf = open('%s/%s_%s.ofx' % (output_dir, user, account_id), 'w')
    outf.write(contents)
    outf.close()


def get_data(user, config, output_dir, later_than, chatter):
    """Fetch, process and save data for a single user."""

    def show_and_tell(pre, function, post='done.'):
        if chatter['quiet']:
            function()
        else:
            print(pre, end=' ')
            sys.stdout.flush()
            function()
            print(post)

    cleanup_re = re.compile('[- 	]+')

    # Login to the bank, get data for all accounts.
    creds = config[user]
    bank = aib.Aib(creds, chatter)
    show_and_tell(
        'Logging in as \'%s\' (check your phone for 2FA)...' % user, bank.login
    )
    show_and_tell('Scraping account pages for data...', bank.get_data)
    show_and_tell('Logging \'%s\' out...' % user, bank.bye)

    # Save each account to separate OFX file.
    for account in bank.getdata().values():
        if not account:
            continue
        name = re.sub(cleanup_re, '_', account['accountId']).lower()
        contents = ofx.bankdata_to_ofx(account, later_than)
        write_file(output_dir, user, name, contents)


def main():
    """Main script entry point."""
    # Parse command line options.
    options = get_options()
    chatter = {
        'quiet': options.quiet_mode,
        'debug': options.debug_mode,
    }
    if options.later_than:
        later_than = dparser.parse(options.later_than, dayfirst=False, yearfirst=True)
    else:
        later_than = None

    # Read user-provided credentials.
    config = cfg.Config()

    try:
        os.makedirs(options.output_dir)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    # Iterate through accounts, scrape, format and save data.
    for user in config.users():
        get_data(user, config, options.output_dir, later_than, chatter)


if __name__ == '__main__':
    main()
