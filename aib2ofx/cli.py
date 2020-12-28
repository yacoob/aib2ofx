"""Command line interface of aib2ofx."""

import datetime
import errno
import optparse
import os
import re
import sys

import dateutil.parser as dparser

from . import aib
from . import cfg
from . import ofx


def get_options():
    """Parse argv into options."""
    parser = optparse.OptionParser()
    option_list = [
        optparse.make_option(
            '-d',
            '--output-dir',
            dest='output_dir',
            help='directory to put OFX files in [/tmp]',
        ),
        optparse.make_option(
            '-D',
            '--debug',
            action='store_true',
            dest='debug_mode',
            help='display some debug output [False]',
        ),
        optparse.make_option(
            '-q',
            '--quiet',
            action='store_true',
            dest='quiet_mode',
            help='display no output at all [False]',
        ),
        optparse.make_option(
            '-l',
            '--later-than',
            dest='later_than',
            help='exports only transactions later than specified date [YYYY-MM-DD]',
        ),
    ]
    parser.add_options(option_list)
    output_dir = os.path.join('.', datetime.date.today().strftime('%Y-%m-%d'))
    parser.set_defaults(output_dir=output_dir, debug_mode=False, quiet_mode=False)
    return parser.parse_args()


def write_file(account_data, output_dir, user, account_id, formatter):
    """Save parsed data to a file."""
    outf = open('%s/%s_%s.ofx' % (output_dir, user, account_id), 'w')
    outf.write(formatter.prettyprint(account_data))
    outf.close()


def get_data(user, config, output_dir, formatter, chatter):
    """Fetch, process and save data for a single user."""

    def show_and_tell(pre, function, post='done.'):
        if chatter['quiet']:
            function(chatter)
        else:
            print(pre, end=' ')
            sys.stdout.flush()
            function(chatter)
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
        write_file(account, output_dir, user, name, formatter)


def main():
    """Main script entry point."""
    # Parse command line options.
    (options, _) = get_options()
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
    formatter = ofx.Ofx(later_than)

    try:
        os.makedirs(options.output_dir)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    # Iterate through accounts, scrape, format and save data.
    for user in config.users():
        get_data(user, config, options.output_dir, formatter, chatter)


if __name__ == '__main__':
    main()
