"""All functionality related to interactions with AIB online interface."""

import csv
import datetime
import logging
import re
import tempfile
import time

import dateutil.parser as dparser
import mechanicalsoup


def _to_date(text):
    # AIB CSV export format: DD/MM/YYYY
    return dparser.parse(text, dayfirst=True, yearfirst=False)


def _to_value(text):
    tmp = text.strip().replace(',', '')
    if tmp[-3:] == ' DR':
        return '-' + tmp[:-3]
    return tmp


def _csv2account(csv_data, acc):
    transactions = list(csv_data)
    if not transactions:
        return None
    if 'Masked Card Number' in transactions[0]:
        acc['type'] = 'credit'
    else:
        acc['type'] = 'checking'
        acc['balance'] = transactions[-1].get('Balance', 0)
    operations = []
    for transaction in transactions:
        operation = {}
        operation['timestamp'] = _to_date(transaction['Posted Transactions Date'])
        # The mysterious story of 'Description' field in CSV exports continues!
        # Now the columns differ between CC and current account, on top of the
        # implemented bugs :(
        if acc['type'] == 'credit':
            desc = transaction['Description']
            if len(desc) > 18 and desc[18] == ' ':
                desc = desc[:18] + desc[19:]
        else:
            descriptions = []
            for i in [1, 2, 3]:
                descriptions.append(transaction['Description%s' % i].strip())
            desc = ' '.join(filter(bool, descriptions))
        operation['description'] = desc
        operation['debit'] = _to_value(transaction['Debit Amount'])
        operation['credit'] = _to_value(transaction['Credit Amount'])
        operations.append(operation)
    acc['operations'] = operations
    return acc


class CleansingFormatter(logging.Formatter):
    """Logging formatter that scrubs monetary values out."""

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


class Aib:
    """Automated browser interacting with AIB online interface."""

    def __init__(self, logindata, chatter):
        self.logindata = logindata
        if chatter['debug']:
            # make a directory for debugging output
            debugdir = tempfile.mkdtemp(prefix='aib2ofx_')
            print('WARNING: putting *sensitive* debug data in %s' % debugdir)
            self.logger = logging.getLogger("mechanize")
            logfile = logging.FileHandler(debugdir + '/mechanize.log', 'w')
            formatter = CleansingFormatter('%(asctime)s\n%(message)s')
            logfile.setFormatter(formatter)
            self.logger.addHandler(logfile)
            self.logger.setLevel(logging.DEBUG)
        else:
            logging.disable(logging.DEBUG)
            self.logger = logging.getLogger(None)
        self.browser = mechanicalsoup.StatefulBrowser()
        self.login_done = False
        self.data = {}

    def login(self):
        """Go through the login process."""
        brw = self.browser

        # first stage of login - registration number
        self.logger.debug('Requesting first login page.')
        brw.open('https://onlinebanking.aib.ie/inet/roi/login.htm')
        brw.select_form(selector='#loginstep1Form')
        brw['regNumber'] = self.logindata['regNumber']
        self.logger.debug('Submitting first login form.')
        brw.submit_selected()

        # second stage of login - selected pin digits
        brw.select_form(selector='#loginstep2Form')
        labels = brw.get_current_page().select('label[for^=digit]')
        for idx, label in enumerate(labels):
            requested_digit = int(label.text[-2]) - 1
            pin_digit = self.logindata['pin'][requested_digit]
            field_name = 'pacDetails.pacDigit' + str(idx + 1)
            self.logger.debug('Using digit number %d of PIN.', (requested_digit + 1))
            brw[field_name] = pin_digit
        self.logger.debug('Submitting second login form.')
        brw.submit_selected()

        # Wait for 2FA on phone
        tfa_done = False
        while not tfa_done:
            brw.select_form('#finalizeForm')
            response = brw.submit_selected(update_state=False)
            if response.content == b'approved':
                tfa_done = True
            elif response.content != b'in_progress':
                raise RuntimeError(
                    'unexpected answer during 2FA auth: %s' % response.content
                )
            time.sleep(1)

        # Forward to normal interface.
        brw.select_form('#finalizeForm')
        brw.submit_selected()

        # mark login as done
        if brw.get_current_page().find(string='My Accounts'):
            self.login_done = True

    def get_data(self):
        """Download data for all accounts."""
        if not self.login_done:
            self.login()

        brw = self.browser
        self.data = {}
        # parse totals
        main_page = brw.get_current_page()
        for account_line in main_page.find_all(
            'button', attrs={'class': 'account-button'}
        ):
            if not account_line.dt:
                continue

            # Skip pension and saving accounts
            if account_line.find(text=re.compile('SAVINGS')):
                continue

            account = {}
            account['accountId'] = account_line.dt.get_text(strip=True)
            account['available'] = _to_value(
                account_line.find(
                    'span', {'class': re.compile('.*a-amount.*')}
                ).get_text(strip=True)
            )
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
        brw.select_form('#historicalstatement_form_id')
        brw.submit_selected()

        brw.select_form('#hForm')
        accounts_on_page = {
            o.text: o.get('value')
            for o in brw.get_current_form().form.find_all('option')
        }

        for account in list(self.data):
            if account not in accounts_on_page.keys():
                self.logger.debug(
                    'skipping account %s which is absent on historical'
                    'transactions page',
                    account,
                )
                del self.data[account]
                continue

            # get account's page
            self.logger.debug('Requesting transactions for %s.', account)
            brw.select_form('#hForm')
            brw['dsAccountIndex'] = accounts_on_page[account]
            brw.submit_selected()

            # click the export button
            form = brw.select_form('#historicalTransactionsCommand')
            # Some accounts (eg. freshly opened ones) have export facility
            # disabled. Skip them.
            if form.form.find(attrs={'name': 'export'}).get('value') == 'false':
                self.logger.debug(
                    'skipping account %s which has its "Export" button' 'disabled',
                    account,
                )
                del self.data[account]
                continue
            brw.submit_selected()

            # confirm the export request
            brw.select_form('#historicalTransactionsCommand')
            response = brw.submit_selected(update_state=False)
            csv_data = csv.DictReader(
                response.iter_lines(decode_unicode=True), skipinitialspace=True
            )
            self.data[account] = _csv2account(csv_data, self.data[account])

            # go back to the list of accounts
            brw.select_form('#historicaltransactions_form_id')
            brw.submit_selected()

    def getdata(self):
        """Returns data acquired from online interface."""
        return self.data

    def bye(self):
        """Logs user out of bank's online interface."""
        self.logger.debug('Logging out.')
        brw = self.browser
        brw.select_form('#formLogout')
        brw.submit_selected()
        if not brw.get_current_page().find(string='Logged Out'):
            raise Exception('Logout failed!')
