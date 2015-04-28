#!/usr/bin/env python
# coding: utf-8

import cookielib, datetime, exceptions, logging, os, re, tempfile

from BeautifulSoup import BeautifulSoup
import dateutil.parser as dparser
import mechanize

def _toDate(text):
    # AIB format: Weekday, Nth Month YY
    return dparser.parse(text)


def _toValue(text):
    tmp = text.strip().replace(',','')
    #FIXME: UNICODE characters, we has them in input
    #FIXME: alternatively, purge entities
    if tmp[-3:] == ' DR':
        return '-' + tmp[:-3]
    else:
        return tmp

def _attrEquals(name, text):
    return lambda f: f.attrs.get(name) == text


class CleansingFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        self.amount_re = re.compile('(?:\d+,)*\d+\.\d+(?: DR)?')
        self.date_re = re.compile('\d\d/\d\d/\d\d')
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
        factory = mechanize.DefaultFactory()
        factory._forms_factory = mechanize.FormsFactory(form_parser_class=mechanize.XHTMLCompatibleFormParser)
        self.br = mechanize.Browser(factory=factory)
        self.quiet = chatter['quiet']
        self.debug = chatter['debug']
        br = self.br
        cj = cookielib.LWPCookieJar()
        br.set_cookiejar(cj)

        br.set_handle_equiv(True)
        #br.set_handle_gzip(True)
        br.set_handle_redirect(True)
        br.set_handle_referer(True)
        br.set_handle_robots(False)
        br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

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

            br.set_debug_redirects(True)
            br.set_debug_responses(True)
        else:
            logging.disable(logging.DEBUG)
            self.logger = logging.getLogger(None)

        br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
        self.login_done = False
        self.data = {}


    def login(self, quiet=False):
        br = self.br
        logindata = self.logindata

        # first stage of login
        self.logger.debug('Requesting first login page.')
        br.open('https://onlinebanking.aib.ie/inet/roi/login.htm')
        br.select_form(name='loginstep1')
        br.set_value(name='regNumber', value=logindata['regNumber'])
        self.logger.debug('Submitting first login form.')
        br.submit()

        # second stage of login
        br.select_form(name='loginstep2')

        for i in [1, 2, 3]:
            name = 'pacDetails.pacDigit' + str(i)
            c = br.find_control(name=name)
            l = c.get_labels()[-1].text
            requested_digit = int(l[-1]) - 1
            pin_digit = logindata['pin'][requested_digit]
            self.logger.debug('Using digit number %d of PIN.' % (requested_digit + 1))
            br.form[name] = pin_digit

        self.logger.debug('Submitting second login form.')
        br.submit()

        # mark login as done
        # FIXME: should really check whether we succesfully logged in here
        self.login_done = True


    def scrape(self, quiet=False):
        if not self.login_done:
            self.login()

        br = self.br
        self.data = {}

        # make sure we're on the top page
        self.logger.debug('Requesting main page with account listing to grab totals.')
        br.select_form(predicate=_attrEquals('id', 'accountoverviewPage_form_id'))
        br.submit()

        # parse totals
        main_page = BeautifulSoup(br.response().read(), convertEntities='html')
        for account_line in main_page.findAll('ul', onclick=re.compile('.+')):
            if not account_line.span:
                continue

            # Skip pension accounts
            if account_line.find('li', {'class': re.compile('i-umbrella')}):
                continue

            account = {}
            account['accountId'] = account_line.span.renderContents()
            account['available'] = _toValue(
                account_line.find('li', {'class': 'balance'}).em.renderContents().translate(
                    None, '\r\t\n' + ''.join([chr(i) for i in range(128,256)])))
            account['currency'] = 'EUR'
            account['bankId'] = 'AIB'
            account['reportDate'] = datetime.datetime.now()

            self.data[account['accountId']] = account


        # parse transactions
        self.logger.debug('Switching to transaction listing.')
        br.select_form(predicate=_attrEquals('id', 'statement_form_id'))
        br.submit()

        br.select_form(predicate=_attrEquals('id', 'sForm'))
        account_dropdown = br.find_control(name='index')
        accounts_on_page = [m.get_labels()[-1].text for m in account_dropdown.get_items()]
        accounts_in_data = self.data.keys()


        for account in accounts_on_page:
            if not account in accounts_in_data:
                self.logger.debug('skipping dubious account %s' % account)
                continue

            # get account's page
            self.logger.debug('Requesting transactions for %s.' % account)
            br.select_form(predicate=_attrEquals('id', 'sForm'))
            account_dropdown = br.find_control(name='index')
            account_dropdown.set_value_by_label([account])
            br.submit()

            # mangle the data
            statement_page = BeautifulSoup(br.response().read(), convertEntities='html')
            acc = self.data[account]

            # check the account type
            # Note: the HTML layout of credit card page and normal account have
            # different structure. Yay for consinstency! :|
            balance_header = statement_page.find(
                'ul', {'class': re.compile('summary-panel')}).find(
                    'strong').renderContents()
            if 'Last Statement' in balance_header:
                acc['type'] = 'credit'
                row_element = 'ul'
                cell_element = 'li'
            else:
                acc['type'] = 'checking'
                row_element = 'tr'
                cell_element = 'td'

            # extract the transaction list
            transactions_box = statement_page.find(
                'div', {'class': re.compile('trans-column-left')})
            operations = []
            last_operation = None
            last_encountered_date = None
            rows = transactions_box.findAll(row_element)
            if rows:
                for row in rows:
                    if row.find('form'):
                        # row with buttons (on cc pages)
                        continue
                    if row.has_key('class') and 'top-row' in row['class']:
                        # header
                        continue
                    if row.has_key('class') and 'date-row' in row['class']:
                        # each day has its own "header" row
                        last_encountered_date = _toDate(
                            row.strong.renderContents())
                        continue
                    cells = row.findAll(cell_element)
                    if not len(cells):
                        # empty row
                        continue
                    operation = {}
                    operation['timestamp'] = last_encountered_date
                    operation['description'] = cells[0].text
                    operation['debit'] = operation['credit'] = 0
                    amount = cells[1].text
                    if amount:
                        if amount[0] == '-':
                            op = 'debit'
                        else:
                            op = 'credit'
                        operation[op] = _toValue(amount[1:])
                    if acc['type'] != 'credit':
                        operation['balance'] = _toValue(cells[3].text)

                    # add parsed operation if current row was describing one
                    if operation['debit'] or operation['credit']:
                        operations.append(operation)
                        last_operation = operation
                    elif (last_operation and
                          operation['description'] not in self.new_operations and
                          operation['timestamp'] == last_operation['timestamp']):
                        # continuation rows - no amounts, just description and
                        # balance
                        last_operation['description'] += ' ' + operation['description']
                        if operation.get('balance') and not last_operation.get('balance'):
                          last_operation['balance'] = operation['balance']
                    else:
                        last_operation = operation

                # add final account balance, if available
                if acc['type'] != 'credit':
                    if operations:
                        acc['balance'] = operations[-1]['balance']
                    else:
                        acc['balance'] = acc['available']
                acc['operations'] = operations
            else:
                self.logger.debug('removing empty account %s from list' % account)
                del self.data[account]


    def getdata(self):
        return self.data

    def bye(self, quiet=False):
        self.logger.debug('Logging out.')
        br = self.br
        br.select_form(predicate=_attrEquals('id', 'formLogout'))
        br.submit()
        # FIXME: check whether we really logged out here
