"""Functionality related to producing OFX format out of parsed data."""

from hashlib import sha256
from xml.sax.saxutils import escape


def _to_date(date):
    return date.strftime('%Y%m%d%H%M%S')


class Ofx:
    """OFX formatter."""
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

        self.transactions = """
<BANKTRANLIST>
<DTSTART>%(firstDate)s</DTSTART>
<DTEND>%(lastDate)s</DTEND>
%(transactions)s
</BANKTRANLIST>"""

        self.closing = {
            'checking': """
<LEDGERBAL><BALAMT>%(balance)s</BALAMT><DTASOF>%(reportDate)s</DTASOF></LEDGERBAL>
<AVAILBAL><BALAMT>%(available)s</BALAMT><DTASOF>%(reportDate)s</DTASOF></AVAILBAL>
</STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>""",
            'credit': """
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

    def prettyprint(self, input_data):
        """Turns dictionary into OFX document."""
        ofx = ''
        data = {}

        # Move obvious things to data.
        data = input_data.copy()

        # Calculate rest of necessary fields.
        data['reportDate'] = _to_date(data['reportDate'])
        if data['operations']:
            data['firstDate'] = _to_date(data['operations'][0]['timestamp'])
            data['lastDate'] = _to_date(data['operations'][-1]['timestamp'])
        else:
            data['firstDate'] = data['reportDate']
            data['lastDate'] = data['reportDate']

        # Turn set of transactions into a lengthy string.
        hashes = {}
        transactions = []
        for transaction in data['operations']:
            trx = transaction.copy()
            if self.later_than and trx['timestamp'] <= self.later_than:
                continue
            trx['description'] = escape(trx['description'])
            if trx['credit'] and float(trx['credit']) != 0:
                trx['type'] = 'CREDIT'
                trx['amount'] = trx['credit']
            else:
                trx['type'] = 'DEBIT'
                trx['amount'] = '-%s' % trx['debit']
            trx['timestamp'] = _to_date(trx['timestamp'])
            hsh = sha256(
                trx['timestamp'].encode("utf-8")
                + trx['amount'].encode("utf-8")
                + trx['description'].encode("utf-8")
            )
            digest = hsh.hexdigest()
            # If there's been a transaction with identical hash in the current
            # set, record this and modify the hash to be different in OFX.
            if digest in hashes:
                count = hashes[digest] + 1
                hashes[digest] = count
                hsh.update(b'%d' % count)
            else:
                hashes[digest] = 1
            trx['tid'] = hsh.hexdigest()
            transactions.append(self.single_transaction % trx)

        data['transactions'] = '\n'.join(transactions)

        # Wrap up and return resulting OFX.
        ofx = '\n'.join(
            (
                self.opening,
                self.headers[data['type']],
                self.transactions,
                self.closing[data['type']],
            )
        )
        ofx = ofx % data

        return ofx
