#!/usr/bin/env python
# coding: utf-8

import cookielib, datetime, exceptions, logging, os, re, tempfile

from BeautifulSoup import BeautifulSoup
import mechanize

def _toDate(text):
    # AIB format: DD/MM/YY
    date_chunks = text.strip().split('/')
    # FIXME: proper year heuristics
    # the +2000 part is really horrible. Don't try that at home, kids.
    newdate = datetime.date(
        int(date_chunks[2], 10) + 2000, # year
        int(date_chunks[1], 10),        # month
        int(date_chunks[0], 10)         # day
    )
    return newdate


def _toValue(text):
    tmp = text.strip().replace(',','')
    #FIXME: UNICODE characters, we has them in input
    #FIXME: alternatively, purge entities
    if tmp[-3:] == ' DR':
        return '-' + tmp[:-3]
    else:
        return tmp

def _actionEndsWith(text):
    return lambda f: f.action.endswith(text)

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
        br.open('https://aibinternetbanking.aib.ie/inet/roi/login.htm')
        br.select_form(name='form1')
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
        br.select_form(predicate=_actionEndsWith('/accountoverview.htm'))
        br.submit()

        # parse totals
        main_page = BeautifulSoup(br.response().read(), convertEntities='html')
        for div in main_page.findAll('div', 'aibBoxStyle04'):
            if not div.span:
                continue
            account = {}
            account['accountId'] = div.span.renderContents()
            account['available'] = _toValue(
                    div.h3.renderContents().translate(None, '\r\t\n' +
                        ''.join([chr(i) for i in range(128,256)])))
            account['currency'] = 'EUR'
            account['bankId'] = 'AIB'
            account['reportDate'] = datetime.datetime.now()

            self.data[account['accountId']] = account


        # parse transactions
        self.logger.debug('Switching to transaction listing.')
        br.select_form(predicate=_actionEndsWith('statement.htm'))
        br.submit()

        br.select_form(predicate=_attrEquals('id', 'accountForm'))
        account_dropdown = br.find_control(name='index')
        accounts_on_page = [m.get_labels()[-1].text for m in account_dropdown.get_items()]
        accounts_in_data = self.data.keys()

        for account in accounts_on_page:
            if not account in accounts_in_data:
                self.logger.debug('skipping dubious account %s' % account)
                continue

            # get account's page
            self.logger.debug('Requesting transactions for %s.' % account)
            br.select_form(predicate=_attrEquals('id', 'accountForm'))
            account_dropdown = br.find_control(name='index')
            account_dropdown.set_value_by_label([account])
            br.submit()

            # mangle the data
            statement_page = BeautifulSoup(br.response().read(), convertEntities='html')
            acc = self.data[account]
            header = statement_page.find('div', 'aibStyle07')
            body = header.findNextSibling('div')
            table = body.find('table', 'aibtableStyle01')
            operations = []
            last_operation = None

            if table:
                # single row consists of following <th>s:
                # Checking:
                # Date, Description, Debit, Credit, Balance
                # CCard:
                # Date, Description, Debit, Credit
                num_columns = len(table.tr.findAll('th'))
                if num_columns == 4:
                    acc['type'] = 'credit'
                elif num_columns == 5:
                    acc['type'] = 'checking'
                else:
                    self.logger.debug('unknown number of columns %d, removing account %s from list' %
                            (num_columns, account))
                    del self.data[account]
                    continue
                for row in table.findAll('tr'):
                    if not row.td:
                        continue
                    cells = row.findAll('td')
                    operation = {}
                    operation['timestamp'] = _toDate(cells[0].renderContents())
                    operation['description'] = cells[1].renderContents()
                    operation['debit'] = _toValue(cells[2].renderContents())
                    operation['credit'] = _toValue(cells[3].renderContents())
                    if acc['type'] != 'credit':
                        operation['balance'] = _toValue(cells[4].renderContents().strip(self.strip_chars))

                    if operation['debit'] or operation['credit']:
                        operations.append(operation)
                        last_operation = operation
                    elif (last_operation and
                          operation['description'] not in self.new_operations and
                          operation['timestamp'] == last_operation['timestamp']):
                        last_operation['description'] += ' ' + operation['description']
                        if operation.get('balance') and not last_operation.get('balance'):
                          last_operation['balance'] = operation['balance']
                    else:
                        last_operation = operation

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
        br.select_form(predicate=_actionEndsWith('/logout.htm'))
        br.submit()
        # FIXME: check whether we really logged out here
