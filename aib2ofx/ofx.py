#!/usr/bin/env python
# coding: utf-8

from hashlib import sha256
from xml.sax.saxutils import escape


def _toDate(d):
    return d.strftime('%Y%m%d%H%M%S')


class ofx:
    def __init__(self, later_than):
        self.later_than = later_than
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
            'checking':
            """
<BANKMSGSRSV1>
<STMTTRNRS><TRNUID>1</TRNUID>
<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
<STMTRS><CURDEF>%(currency)s</CURDEF>
<BANKACCTFROM><BANKID>%(bankId)s</BANKID>
<ACCTID>%(accountId)s</ACCTID>
<ACCTTYPE>CHECKING</ACCTTYPE>
</BANKACCTFROM>""",
            'credit':
            """
<CREDITCARDMSGSRSV1>
<CCSTMTTRNRS><TRNUID>1</TRNUID>
<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
<CCSTMTRS><CURDEF>%(currency)s</CURDEF>
<CCACCTFROM>
<ACCTID>%(accountId)s</ACCTID>
</CCACCTFROM>""",
        }

        self.transactions = """
<BANKTRANLIST>
<DTSTART>%(firstDate)s</DTSTART>
<DTEND>%(lastDate)s</DTEND>
%(transactions)s
</BANKTRANLIST>"""

        self.closing = {
            'checking':
            """
<LEDGERBAL><BALAMT>%(balance)s</BALAMT><DTASOF>%(reportDate)s</DTASOF></LEDGERBAL>
<AVAILBAL><BALAMT>%(available)s</BALAMT><DTASOF>%(reportDate)s</DTASOF></AVAILBAL>
</STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>""",
            'credit':
            """
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
        if data['operations']:
            data['firstDate'] = _toDate(data['operations'][0]['timestamp'])
            data['lastDate'] = _toDate(data['operations'][-1]['timestamp'])
        else:
            data['firstDate'] = data['reportDate']
            data['lastDate'] = data['reportDate']

        # Turn set of transactions into a lengthy string.
        hashes = {}
        transactions = []
        for transaction in data['operations']:
            t = transaction.copy()
            if self.later_than and t['timestamp'] <= self.later_than:
                continue
            t['description'] = escape(t['description'])
            if t['credit'] and float(t['credit']) != 0:
                t['type'] = 'CREDIT'
                t['amount'] = t['credit']
            else:
                t['type'] = 'DEBIT'
                t['amount'] = '-%s' % t['debit']
            t['timestamp'] = _toDate(t['timestamp'])
            h = sha256(t['timestamp'].encode("utf-8") +
                       t['amount'].encode("utf-8") +
                       t['description'].encode("utf-8"))
            hd = h.hexdigest()
            # If there's been a transaction with identical hash in the current
            # set, record this and modify the hash to be different in OFX.
            if hd in hashes:
                n = hashes[hd] + 1
                hashes[hd] = n
                h.update(str(n))
            else:
                hashes[hd] = 1
            t['tid'] = h.hexdigest()
            transactions.append(self.single_transaction % t)

        data['transactions'] = '\n'.join(transactions)

        # Wrap up and return resulting OFX.
        ofx = '\n'.join((self.opening, self.headers[data['type']],
                         self.transactions, self.closing[data['type']]))
        ofx = ofx % data

        return ofx
