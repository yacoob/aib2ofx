#!/usr/bin/env python
# coding: utf-8

from itertools import groupby
from BeautifulSoup import BeautifulStoneSoup
import re, os, subprocess, fnmatch, codecs
from datetime import datetime

class PdfParse:
    credit_card_marker = 'Account Statement - '

    class CurrentAccountConfiguration(object):
        type = 'checking'
        new_operations = ['BALANCE FORWARD', 'Interest Rate', 'New Interest Rate']
        blacklisted = []
        end_of_operations = []
        cover_page = None

        items_top = 300
        items_bottom = 1100

        date_lpos = 55
        desc_lpos = 118
        debit_rpos = 461
        credit_rpos = 545
        cover_balance = None
        balance_rpos = 645

        dateRegEx = '\d+\s\w+\s\d{4,4}'
        dateFormat = '%d %b %Y'
        dateParseSuffix = ''
        accountNoRegEx = '\d{5,5}-\d{3,3}'

    class CreditAccountConfiguration(object):
        type = 'credit'
        new_operations = []
        blacklisted = ['Amount', 'Details and', 'Reference Number']
        end_of_operations = ['Start Date']
        cover_page = '1'

        items_top = 300
        items_bottom = 1200

        date_lpos = 160
        desc_lpos = 178
        debit_rpos = 606
        credit_rpos = 621
        cover_balance = 'New Balance'
        balance_rpos = 607

        dateRegEx = '\d+\s\w+'
        dateFormat = '%d %b %Y'
        # We can't use the default year of 1900 because it's not a leap year,
        # so we force it to 2000 so that 29 Feb will parse successfully.
        dateParseSuffix = ' 2000'
        accountNoRegEx = '\d{4} \d{2}\*{2} \*{4} \d{4}'

    def __init__(self, directory):
        self.directory = os.path.abspath(directory)

    def getData(self):
        files = os.listdir(self.directory)
        data=[]
        for f in files:
            if fnmatch.fnmatch(f, '*.pdf'):
                fullpdfname = self.directory+"/"+f
                fullxmlname = fullpdfname.rstrip('.pdf')+".xml"
                if not os.path.exists(fullxmlname):
                    subprocess.call(['pdftohtml', '-xml', fullpdfname])
                data.append(self._get_data_for_file(fullxmlname))
        return data

    def _get_data_for_file(self, file_name):
        data =  {'type':'',
                'accountId':'',
                'available': '',
                'balance' : '',
                'bankId': 'AIB',
                'currency': 'EUR',
                'operations': []}

        statement = self._parse_xml(file_name)
        data['accountId']=statement['accountId']
        data['type']=statement['type']

        operations = statement['operations']
        data['operations']=operations
        data['balance']=statement['balance']
        data['available']=data['balance']
        data['reportDate']=operations[-1]['timestamp']
        return data

    def _parse_xml(self, file_name):
        file = codecs.open(file_name, "r")
        xml = file.read()
        soup = BeautifulStoneSoup(xml);

        conf = self.CurrentAccountConfiguration
        statement_date = None
        operations=[]
        accountId = ''
        balance = ''
        #Template for an operation
        operation_tmpl = dict(debit='',credit='',balance='',description='')
        operation=operation_tmpl.copy()

        def classify_cells(row):
            """Takes a row of statement data and fills in some fields in a dict.

            The resulting dict always has a description field. Optional fields
            may include: timestamp, debit, credit, balance.

            Note: a single row may not contain a single transaction. The
            returned row corresponds to a line in the statement (literally).
            """
            res = {}
            for cell in row:
                s = ' '.join(cell.findAll(text=True)).strip()
                top_pos = int(cell['top'])
                left_pos = int(cell['left'])
                right_pos = left_pos + int(cell['width'])

                if(top_pos<conf.items_top or top_pos>conf.items_bottom):
                    continue

                if left_pos <= conf.date_lpos:
                    dateMatch = re.match(conf.dateRegEx,s)
                    if(dateMatch):
                        date = dateMatch.group(0) + conf.dateParseSuffix
                        current_ts = datetime.strptime(date, conf.dateFormat)
                        if statement_date:
                            current_ts = (current_ts.replace(statement_date.year -
                                (1 if statement_date.month < 2 and current_ts.month > 10 else 0)))
                        else:
                            s = s.replace(date, '').lstrip()
                            left_pos = conf.desc_lpos
                        res['timestamp'] = current_ts

                if abs(left_pos-conf.desc_lpos) < 2:
                    res['description'] = s.replace(',','')

                if abs(right_pos-conf.debit_rpos) < 2:
                    res['debit'] = s.replace(',','')

                if abs(right_pos-conf.credit_rpos) < 2:
                    res['credit'] = s.replace(',','')

                if abs(right_pos-conf.balance_rpos) < 2:
                    res['balance'] = s
                    balance = s
            return res

        def rows_reconciliator(rows_iter):
            """Combines asequence of statement lines into operations."""
            pending = {}
            for row in rows_iter:
                if not row:
                    continue
                description = row['description']
                timestamp = row.get('timestamp')
                credit = row.get('credit')
                debit = row.get('debit')
                balance = row.get('balance')
                if pending and (timestamp or debit or credit):
                    if pending.get('timestamp'):
                        yield pending
                    prev = pending
                    pending = {
                            'timestamp': timestamp or prev['timestamp'],
                            'description': '',
                            'credit': '',
                            'debit': '',
                            'balance': '',
                    }
                if credit:
                    pending['credit'] = credit
                if debit:
                    pending['debit'] = debit
                if balance:
                    pending['balance'] = balance

                if pending.get('description'):
                    pending['description'] += ' '
                else:
                    pending['description'] = ''
                pending['description'] += description
            yield pending

        def position(elm):
            return (elm.findParent('page')['number'], int(elm['top'])/5*5, int(elm['left']))

        def rows_iter(soup):
            """Iterates over rows of statement as dicts with some fields set."""
            def row_id(elm):
                """Returns elem['top'] floored to the nearest multiple of 5."""
                return int(elm['top'])/5 * 5

            for top_pos, row in groupby(sorted(soup.findAll('text'), key=position), row_id):
                yield classify_cells(row)

        for elm in sorted(soup.findAll('text'), key=position):
            right_pos=int(elm['left'])+int(elm['width'])
            left_pos=int(elm['left'])
            top_pos=int(elm['top'])

            s = ' '.join(elm.findAll(text=True)).strip()
            if(not statement_date and s.startswith(self.credit_card_marker)):
                conf = self.CreditAccountConfiguration
                month_year = ' '.join(s.split(' ')[-2:])
                statement_date = datetime.strptime(month_year, '%B, %Y')

            if(elm.findParent('page')['number'] == conf.cover_page):
                if(abs(right_pos-conf.balance_rpos)<2):
                    if(descriptions and descriptions[0]==conf.cover_balance):
                        balance = s.replace(',','')
                descriptions = [s]
                continue
            if(s in conf.end_of_operations):
                break
            if(s in conf.blacklisted):
                continue

            accountIdMatch = re.search(conf.accountNoRegEx, s)
            if(accountIdMatch):
                accountId=accountIdMatch.group(0).replace('*','x').replace(' ','-')

        operations = list(rows_reconciliator(rows_iter(soup)))

        return {'type':conf.type, 'accountId':accountId, 'operations':operations, 'balance':balance}
