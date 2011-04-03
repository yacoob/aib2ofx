#!/usr/bin/env python
# coding: utf-8

from BeautifulSoup import BeautifulStoneSoup
import re, os, subprocess, fnmatch, codecs
from datetime import datetime

class PdfParse:
    def __init__(self, directory):
        self.debit_rpos=307
        self.credit_rpos=363
        self.balance_rpos=430
        self.desc_lpos=79
        self.items_top=300
        self.items_bottom=750

        self.dateRegEx = '\d+\s\w+\s\d{4,4}'
        self.accountNoRegEx = '\d{5,5}-\d{3,3}'
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
        data =  {'type':'checking',
                'available': '',
                'balance' : '',
                'bankId': 'AIB',
                'currency': 'EUR',
                'operations': []}

        statement = self._parse_xml(file_name)
        data['accountId']=statement['accountId']

        operations = statement['operations']
        data['operations']=operations
        data['balance']=operations[-1]['balance']
        data['available']=data['balance']
        data['reportDate']=operations[-1]['timestamp']
        return data

    def _parse_xml(self, file_name):
        file = codecs.open(file_name, "r")
        xml = file.read()
        soup = BeautifulStoneSoup(xml);

        operations=[]
        current_ts = ''
        accountId = ''
        #Template for an operation
        operation_tmpl = dict(debit='',credit='',balance='',description='')
        operation=operation_tmpl.copy()

        for elm in soup.findAll('text'):
            right_pos=int(elm['left'])+int(elm['width'])
            left_pos=int(elm['left'])
            top_pos=int(elm['top'])

            accountIdMatch = re.search(self.accountNoRegEx, elm.string)
            if(accountIdMatch):
                accountId=accountIdMatch.group(0)

            if(top_pos<self.items_top or top_pos>self.items_bottom):
              continue

            if(left_pos<=70):
                dateMatch = re.search(self.dateRegEx,elm.string)
                if(dateMatch):
                    date = dateMatch.group(0)
                    operation['description'] = elm.string.replace(date,'').lstrip()
                    current_ts = datetime.strptime(date, '%d %b %Y')
            if(right_pos==self.debit_rpos):
                operation['debit'] = elm.string
                operations.append(operation)
                operation=operation_tmpl.copy()
            if(abs(right_pos-self.credit_rpos)<2):
                operation['credit'] = elm.string
                operations.append(operation)
                operation=operation_tmpl.copy()
            if(left_pos==self.desc_lpos):
                operation['description'] = elm.string

            if(right_pos==self.balance_rpos and len(operations)):
                operations[-1]['balance'] = elm.string

            operation['timestamp'] = current_ts

        return {'accountId':accountId, 'operations':operations}
