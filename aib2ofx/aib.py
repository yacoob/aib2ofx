#!/usr/bin/env python
# coding: utf-8

import csv
import datetime
import logging
import re
import tempfile

from BeautifulSoup import BeautifulSoup
import dateutil.parser as dparser
import mechanicalsoup


def _to_date(text):
    # AIB CSV export format: DD/MM/YYYY
    return dparser.parse(text, dayfirst=True, yearfirst=False)


def _to_value(text):
    tmp = text.strip().replace(',', '')
    # FIXME: UNICODE characters, we has them in input
    # FIXME: alternatively, purge entities
    if tmp[-3:] == ' DR':
        return '-' + tmp[:-3]
    return tmp


def _attrEquals(name, text):
    return lambda f: f.attrs.get(name) == text


def _csv2account(csv_data, acc):
    txs = [tx for tx in csv_data]
    if not txs:
        return None
    if 'Masked Card Number' in txs[0]:
        acc['type'] = 'credit'
    else:
        acc['type'] = 'checking'
        acc['balance'] = txs[-1].get('Balance', 0)
    operations = []
    for tx in txs:
        op = {}
        op['timestamp'] = _to_date(tx['Posted Transactions Date'])
        # The mysterious story of 'Description' field in CSV exports continues!
        # Now the columns differ between CC and current account, on top of the
        # implemented bugs :(
        if acc['type'] == 'credit':
            desc = tx['Description']
            if len(desc) > 18 and desc[18] == ' ':
                desc = desc[:18] + desc[19:]
        else:
            d = []
            for i in [1, 2, 3]:
                d.append(tx['Description%s' % i].strip())
            desc = ' '.join(filter(bool, d))
        op['description'] = desc
        op['debit'] = _to_value(tx['Debit Amount'])
        op['credit'] = _to_value(tx['Credit Amount'])
        operations.append(op)
    acc['operations'] = operations
    return acc


class CleansingFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        self.amount_re = re.compile(r'(?:\d+,)*\d+\.\d+(?: DR)?')
        self.date_re = re.compile(r'\d\d/\d\d/\d\d')
        self.description_re = re.compile('<td>(?!dd/mm/yy).+</td>')
        logging.Formatter.__init__(self, fmt, datefmt)

    def format(self, record):
        tmp = record.msg
        tmp = self.amount_re.sub('X.XX', tmp)
        tmp = self.date_re.sub('dd/mm/yy', tmp)
        tmp = self.description_re.sub('<td>dummy description</td>', tmp)
        record.msg = tmp
        return logging.Formatter.format(self, record)


class aib:
    strip_chars = '\xa0\xc2'
    new_operations = ['Interest Rate']

    def __init__(self, logindata, chatter):
        self.logindata = logindata
        self.br = mechanicalsoup.StatefulBrowser()
        self.quiet = chatter['quiet']
        self.debug = chatter['debug']
        br = self.br

        if self.debug:
            # make a directory for debugging output
            self.debugdir = tempfile.mkdtemp(prefix='aib2ofx_')
            print 'WARNING: putting *sensitive* debug data in %s' % self.debugdir
            self.logger = logging.getLogger("mechanize")
            fh = logging.FileHandler(self.debugdir + '/mechanize.log', 'w')
            fm = CleansingFormatter('%(asctime)s\n%(message)s')
            fh.setFormatter(fm)
            self.logger.addHandler(fh)
            self.logger.setLevel(logging.DEBUG)

            # FIXME: better logging for page *content*
            # br.set_debug_redirects(True)
            # br.set_debug_responses(True)
        else:
            logging.disable(logging.DEBUG)
            self.logger = logging.getLogger(None)

        self.login_done = False
        self.data = {}

    def login(self, quiet=False):
        br = self.br
        logindata = self.logindata

        # first stage of login - registration number
        self.logger.debug('Requesting first login page.')
        br.open('https://onlinebanking.aib.ie/inet/roi/login.htm')
        br.select_form(selector='#loginstep1Form')
        br['regNumber'] = logindata['regNumber']
        self.logger.debug('Submitting first login form.')
        br.submit_selected()

        # second stage of login - selected pin digits
        br.select_form(selector='#loginstep2Form')
        labels = br.get_current_page().select('label[for^=digit]')
        for idx, label in enumerate(labels):
            requested_digit = int(label.text[-2]) - 1
            pin_digit = logindata['pin'][requested_digit]
            field_name = 'pacDetails.pacDigit' + str(idx + 1)
            self.logger.debug('Using digit number %d of PIN.' %
                              (requested_digit + 1))
            br[field_name] = pin_digit
        self.logger.debug('Submitting second login form.')
        br.submit_selected()

        # skip potential interstitial by clicking on 'my messages'
        br.select_form('#mail_l_form_id')
        self.logger.debug(
            'Going to messages, navigating around potential interstitial.')
        br.submit_selected()

        # go to the main page
        br.select_form('#accountoverviewPage_form_id')
        self.logger.debug('Navigating to main page.')
        br.submit_selected()

        # mark login as done
        if br.get_current_page().find(string='My Accounts'):
            self.login_done = True

    def scrape(self, quiet=False):
        if not self.login_done:
            self.login()

        br = self.br
        self.data = {}

        # parse totals
        main_page = BeautifulSoup(br.response().read(), convertEntities='html')
        for account_line in main_page.findAll(
                'button', attrs={'class': 'account-button'}):
            if not account_line.dt:
                continue

            # Skip pension and saving accounts
            if account_line.find(text=re.compile('SAVINGS')):
                continue

            account = {}
            account['accountId'] = account_line.dt.renderContents().translate(
                None, '\r\t\n').strip()
            account['available'] = _to_value(
                account_line.find('span', {
                    'class': re.compile('.*a-amount.*')
                }).renderContents().translate(
                    None,
                    '\r\t\n' + ''.join([chr(i) for i in range(128, 256)])))
            account['currency'] = 'EUR'
            account['bankId'] = 'AIB'
            account['reportDate'] = datetime.datetime.now()

            self.data[account['accountId']] = account

        # parse transactions
        #
        # Note: As of January 2017 there are *two* places that produce CSV data
        # for an account - 'Historical transactions' and 'Recent transactions'.
        # The latter covers shorter period of time, so we use the former. Both
        # exports differ in the type and amount of fields they export. :(
        self.logger.debug('Switching to transaction listing.')
        br.select_form(
            predicate=_attrEquals('id', 'historicalstatement_form_id'))
        br.submit()

        br.select_form(predicate=_attrEquals('id', 'hForm'))
        account_dropdown = br.find_control(name='dsAccountIndex')
        accounts_on_page = [
            m.get_labels()[-1].text for m in account_dropdown.get_items()
        ]
        accounts_in_data = self.data.keys()

        for account in accounts_in_data:
            if not account in accounts_on_page:
                self.logger.debug(
                    'skipping account %s which is absent on historical transactions page'
                    % account)
                del self.data[account]
                continue

            # get account's page
            self.logger.debug('Requesting transactions for %s.' % account)
            br.select_form(predicate=_attrEquals('id', 'hForm'))
            account_dropdown = br.find_control(name='dsAccountIndex')
            account_dropdown.set_value_by_label([account])
            br.submit()

            # click the export button
            br.select_form(
                predicate=_attrEquals('id', 'historicalTransactionsCommand'))
            # Some accounts (eg. freshly opened ones) have export facility
            # disabled. Skip them.
            if br.find_control(name='export').attrs.get('value') == 'false':
                self.logger.debug(
                    'skipping account %s which has its "Export" button disabled'
                    % account)
                del self.data[account]
                continue
            br.submit()

            # confirm the export request
            br.select_form(
                predicate=_attrEquals('id', 'historicalTransactionsCommand'))
            response = br.open_novisit(br.click())
            csv_data = csv.DictReader(response, skipinitialspace=True)
            self.data[account] = _csv2account(csv_data, self.data[account])

            # go back to the list of accounts
            br.select_form(
                predicate=_attrEquals('id', 'historicaltransactions_form_id'))
            br.submit()

    def getdata(self):
        return self.data

    def bye(self, quiet=False):
        self.logger.debug('Logging out.')
        br = self.br
        br.select_form(predicate=_attrEquals('id', 'formLogout'))
        br.submit()
        # FIXME: check whether we really logged out here
