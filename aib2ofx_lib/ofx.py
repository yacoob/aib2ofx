#!/usr/bin/env python
# coding: utf-8

from hashlib import sha256


def _toDate(d):
    return d.strftime('%Y%m%d%H%M%S')


class ofx:
    def __init__(self):
        self.opening = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS>
<CODE>0</CODE>
<SEVERITY>INFO</SEVERITY>
</STATUS><DTSERVER>%(reportDate)s</DTSERVER>
<LANGUAGE>ENG</LANGUAGE>
</SONRS>
</SIGNONMSGSRSV1>"""

        self.headers = {
            'checking': """
<BANKMSGSRSV1>
<STMTTRNRS><TRNUID>1</TRNUID>
<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
<STMTRS><CURDEF>%(currency)s</CURDEF>
<BANKACCTFROM><BANKID>%(bankId)s</BANKID>
<ACCTID>%(accountId)s</ACCTID>
<ACCTTYPE>CHECKING</ACCTTYPE>
</BANKACCTFROM>""",
            'credit': """
<CREDITCARDMSGSRSV1>
<CCSTMTTRNRS><TRNUID>1</TRNUID>
<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
<CCSTMTRS><CURDEF>%(currency)s</CURDEF>
<CCACCTFROM>
<ACCTID>%(accountId)s</ACCTID>
</CCACCTFROM>""",
            }

        self.transactions_header = """
<BANKTRANLIST>
<DTSTART>%(firstDate)s</DTSTART>
<DTEND>%(lastDate)s</DTEND>"""

        self.closing = {
            'checking': """</BANKTRANLIST>
<LEDGERBAL><BALAMT>%(balance)s</BALAMT><DTASOF>%(reportDate)s</DTASOF></LEDGERBAL>
<AVAILBAL><BALAMT>%(available)s</BALAMT><DTASOF>%(reportDate)s</DTASOF></AVAILBAL>
</STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>""",
            'credit': """</BANKTRANLIST>
<LEDGERBAL><BALAMT>%(available)s</BALAMT><DTASOF>%(reportDate)s</DTASOF></LEDGERBAL>
</CCSTMTRS></CCSTMTTRNRS></CREDITCARDMSGSRSV1></OFX>""",
            }

        self.single_transaction = """<STMTTRN>
<TRNTYPE>%(type)s</TRNTYPE>
<DTPOSTED>%(timestamp)s</DTPOSTED>
<TRNAMT>%(amount)s</TRNAMT>
<FITID>%(tid)s</FITID>
<NAME>%(description)s</NAME>
</STMTTRN>
"""


    def prettyprint(self, input):
        ofx = ''
        data = {}

        # Move obvious things to data.
        data = input.copy()

        # Calculate rest of necessary fields.
        data['reportDate'] = _toDate(data['reportDate'])
        data['firstDate'] = _toDate(data['operations'][0]['timestamp'])
        data['lastDate'] = _toDate(data['operations'][-1]['timestamp'])

        # Turn set of transactions into a lengthy string.
        transactions = []
        for transaction in data['operations']:
            t = transaction.copy()
            if t['credit']:
                t['type'] = 'CREDIT'
                t['amount'] = t['credit']
            else:
                t['type'] = 'DEBIT'
                t['amount'] = '-%s' % t['debit']
            t['timestamp'] = _toDate(t['timestamp'])
            t['tid'] = sha256(t['timestamp'].encode("utf-8") + t['amount'].encode("utf-8") + t['description'].encode("utf-8")).hexdigest()
            transactions.append(self.single_transaction % t)

        list_of_transactions = '\n'.join(transactions)

        # Wrap up and return resulting OFX.
        ofx = '\n'.join ((self.opening,
                         self.headers[data['type']],
                         self.transactions_header,
                         list_of_transactions,
                         self.closing[data['type']]))
        ofx = ofx % data

        return ofx
