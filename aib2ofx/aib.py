#!/usr/bin/env python
# coding: utf-8

import cookielib, datetime, exceptions, os, re;

from BeautifulSoup import BeautifulSoup;
import mechanize;

def _toDate(text):
    # AIB format: DD/MM/YY
    date_chunks = text.strip().split('/');
    # FIXME: proper year heuristics
    # the +2000 part is really horrible. Don't try that at home, kids.
    newdate = datetime.date(
        int(date_chunks[2], 10) + 2000, # year
        int(date_chunks[1], 10),        # month
        int(date_chunks[0], 10)         # day
    );
    return newdate;


def _toValue(text):
    tmp = text.strip().replace(',','');
    #FIXME: UNICODE characters, we has them in input
    #FIXME: alternatively, purge entities
    if tmp[-3:] == ' DR':
        return '-' + tmp[:-3];
    else:
        return tmp;


class aib:
    strip_chars = '\xa0\xc2';

    def __init__(self, logindata, debug=False):
        self.logindata = logindata;
        self.br = mechanize.Browser();
        br = self.br;
        cj = cookielib.LWPCookieJar();
        br.set_cookiejar(cj);

        br.set_handle_equiv(True);
        #br.set_handle_gzip(True);
        br.set_handle_redirect(True);
        br.set_handle_referer(True);
        br.set_handle_robots(False);
        br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1);

        br.set_debug_http(debug);
        br.set_debug_redirects(debug);
        br.set_debug_responses(debug);

        br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')];
        self.login_done = False;
        self.data = {};


    def login(self):
        br = self.br;
        logindata = self.logindata;

        # first stage of login
        br.open('https://aibinternetbanking.aib.ie/inet/roi/login.htm');
        br.select_form(name='form1');
        br.set_value(name='regNumber', value=logindata['regNumber']);
        br.submit();

        # second stage of login
        br.select_form(name='loginstep2');

        for i in [1, 2, 3]:
            name = 'pacDetails.pacDigit' + str(i);
            c = br.find_control(name=name);
            l = c.get_labels()[-1].text;
            requested_digit = int(l[-1]) - 1;
            pin_digit = logindata['pin'][requested_digit];
            br.form[name] = pin_digit;

        name = 'challengeDetails.challengeEntered';
        c = br.find_control('challengeDetails.challengeEntered');
        l = c.get_labels()[-1].text;
        if (re.search('work phone', l)):
            br.form[name] = logindata['workNumber'];
        else:
            br.form[name] = logindata['homeNumber'];
        br.submit();

        # mark login as done
        self.login_done = True;


    def scrape(self):
        if not self.login_done:
            self.login();

        br = self.br;
        self.data = {};

        # make sure we're on the top page
        br.select_form(nr=2);
        br.submit();

        # parse totals
        main_page = BeautifulSoup(br.response().read(), convertEntities='html');
        for div in main_page.findAll('div', 'aibBoxStyle04'):
            if not div.span:
                continue;
            account = {};
            account['accountId'] = div.span.renderContents();
            amount = _toValue(div.h3.renderContents().partition('\r')[0]);
            # FIXME: need better method of detecting credit cards
            if amount[0] == '-':
                account['type'] = 'credit';
            else:
                account['type'] = 'checking';

            account['available'] = amount;
            account['currency'] = 'EUR';
            account['bankId'] = 'AIB';
            account['reportDate'] = datetime.datetime.now();

            self.data[account['accountId']] = account;


        # parse transactions
        br.select_form(nr=3);
        br.submit();

        br.select_form(nr=11);
        account_dropdown = br.find_control(name='index');
        accounts_on_page = [m.get_labels()[-1].text for m in account_dropdown.get_items()];
        accounts_in_data = self.data.keys();

        for account in accounts_on_page:
            if not account in accounts_in_data:
                print "skipping dubious account %s" % account;
                continue;

            # get account's page
            br.select_form(nr=11);
            account_dropdown = br.find_control(name='index');
            account_dropdown.set_value_by_label([account]);
            br.submit();

            # mangle the data
            statement_page = BeautifulSoup(br.response().read(), convertEntities='html');
            table = statement_page.find('table', 'aibtableStyle01');
            operations = [];
            # single row consists of following <td>s:
            # Checking:
            # Date, Description, Debit, Credit, Balance
            # CCard:
            # Date, Description, Debit, Credit
            for row in table.findAll('tr'):
                if not row.td:
                    continue;
                cells = row.findAll('td');
                operation = {};
                operation['timestamp'] = _toDate(cells[0].renderContents());
                operation['description'] = cells[1].renderContents();
                operation['debit'] = _toValue(cells[2].renderContents());
                operation['credit'] = _toValue(cells[3].renderContents());
                if self.data[account]['type'] != 'credit':
                    operation['balance'] = _toValue(cells[4].renderContents().strip(self.strip_chars));

                if operation['debit'] or operation['credit']:
                    operations.append(operation);

            acc = self.data[account]
            if acc['type'] != 'credit':
                acc['balance'] = operations[-1]['balance'];
            acc['operations'] = operations;

    def getdata(self):
        return self.data;

    def bye(self):
        br = self.br;
        br.select_form(nr=1);
        br.submit();
