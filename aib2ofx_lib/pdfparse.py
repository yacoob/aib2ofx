#!/usr/bin/env python
# coding: utf-8

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
        items_bottom = 750

        date_lpos = 50
        desc_lpos = 79
        debit_rpos = 307
        credit_rpos = 363
        cover_balance = None
        balance_rpos = 430

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
        current_ts = ''
        descriptions=[]
        accountId = ''
        balance = ''
        #Template for an operation
        operation_tmpl = dict(debit='',credit='',balance='',description='')
        operation=operation_tmpl.copy()

        def position(elm):
            return (elm.findParent('page')['number'], int(elm['top']), int(elm['left']))

        for elm in sorted(soup.findAll('text'), key=position):
            right_pos=int(elm['left'])+int(elm['width'])
            left_pos=int(elm['left'])
            top_pos=int(elm['top'])

            if(not statement_date and elm.string.startswith(self.credit_card_marker)):
                conf = self.CreditAccountConfiguration
                month_year = ' '.join(elm.string.split(' ')[-2:])
                statement_date = datetime.strptime(month_year, '%B, %Y')

            if(elm.findParent('page')['number'] == conf.cover_page):
                if(abs(right_pos-conf.balance_rpos)<2):
                    if(descriptions and descriptions[0]==conf.cover_balance):
                        balance = elm.string.replace(',','')
                descriptions = [elm.string]
                continue
            if(elm.string in conf.end_of_operations):
                break
            if(elm.string in conf.blacklisted):
                continue

            accountIdMatch = re.search(conf.accountNoRegEx, elm.string)
            if(accountIdMatch):
                accountId=accountIdMatch.group(0).replace('*','x').replace(' ','-')

            if(top_pos<conf.items_top or top_pos>conf.items_bottom):
                continue

            if(left_pos<=conf.date_lpos):
                dateMatch = re.match(conf.dateRegEx,elm.string)
                if(dateMatch):
                    date = dateMatch.group(0) + conf.dateParseSuffix
                    current_ts = datetime.strptime(date, conf.dateFormat)
                    if(statement_date):
                        current_ts = (current_ts.replace(statement_date.year -
                            (1 if statement_date.month < 2 and current_ts.month > 10 else 0)))
                    else:
                        elm.string = elm.string.replace(date,'').lstrip()
                        left_pos = conf.desc_lpos

            commit_operation=False
            if(abs(right_pos-conf.debit_rpos)<2):
                operation['debit'] = elm.string.replace(',','')
                commit_operation=True
            if(abs(right_pos-conf.credit_rpos)<2):
                operation['credit'] = elm.string.replace(',','')
                commit_operation=True
            if(left_pos==conf.desc_lpos):
                descriptions.append(elm.string)
                if(elm.string in conf.new_operations):
                    commit_operation=True

            if(commit_operation):
                if(len(operations) and descriptions[:-1]):
                    operations[-1]['description'] += ' ' + ' '.join(descriptions[:-1])
                operation['description'] = descriptions[-1]
                operation['timestamp'] = current_ts
                operations.append(operation)
                operation=operation_tmpl.copy()
                descriptions=[]

            if(right_pos==conf.balance_rpos and len(operations)):
                operations[-1]['balance'] = elm.string
                balance = elm.string

        if(len(operations) and descriptions):
            operations[-1]['description'] += ' ' + ' '.join(descriptions)

        return {'type':conf.type, 'accountId':accountId, 'operations':operations, 'balance':balance}
