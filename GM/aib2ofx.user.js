// ==UserScript==
// @name           aib2ofx
// @namespace      yacoob
// @description    Exports AIB transactions to to OFX/CSV format
// @include        file:///Users/yacoob/_download/*
// @include        https://aibinternetbanking.aib.ie/inet/roi/login.htm
// @include        https://aibinternetbanking.aib.ie/inet/roi/statement.htm
// @include        https://aibinternetbanking.aib.ie/inet/roi/overview.htm
// @require        http://ajax.googleapis.com/ajax/libs/jquery/1.3.2/jquery.min.js
// @require        http://crypto-js.googlecode.com/files/2.0.0-crypto-sha256.js
// ==/UserScript==


/**
*
*  Base64 encode / decode
*  http://www.webtoolkit.info/
*
**/

var Base64 = {

	// private property
	_keyStr : "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=",

	// public method for encoding
	encode : function (input) {
		var output = "";
		var chr1, chr2, chr3, enc1, enc2, enc3, enc4;
		var i = 0;

		input = Base64._utf8_encode(input);

		while (i < input.length) {

			chr1 = input.charCodeAt(i++);
			chr2 = input.charCodeAt(i++);
			chr3 = input.charCodeAt(i++);

			enc1 = chr1 >> 2;
			enc2 = ((chr1 & 3) << 4) | (chr2 >> 4);
			enc3 = ((chr2 & 15) << 2) | (chr3 >> 6);
			enc4 = chr3 & 63;

			if (isNaN(chr2)) {
				enc3 = enc4 = 64;
			} else if (isNaN(chr3)) {
				enc4 = 64;
			}

			output = output +
			this._keyStr.charAt(enc1) + this._keyStr.charAt(enc2) +
			this._keyStr.charAt(enc3) + this._keyStr.charAt(enc4);

		}

		return output;
	},

	// public method for decoding
	decode : function (input) {
		var output = "";
		var chr1, chr2, chr3;
		var enc1, enc2, enc3, enc4;
		var i = 0;

		input = input.replace(/[^A-Za-z0-9\+\/\=]/g, "");

		while (i < input.length) {

			enc1 = this._keyStr.indexOf(input.charAt(i++));
			enc2 = this._keyStr.indexOf(input.charAt(i++));
			enc3 = this._keyStr.indexOf(input.charAt(i++));
			enc4 = this._keyStr.indexOf(input.charAt(i++));

			chr1 = (enc1 << 2) | (enc2 >> 4);
			chr2 = ((enc2 & 15) << 4) | (enc3 >> 2);
			chr3 = ((enc3 & 3) << 6) | enc4;

			output = output + String.fromCharCode(chr1);

			if (enc3 != 64) {
				output = output + String.fromCharCode(chr2);
			}
			if (enc4 != 64) {
				output = output + String.fromCharCode(chr3);
			}

		}

		output = Base64._utf8_decode(output);

		return output;

	},

	// private method for UTF-8 encoding
	_utf8_encode : function (string) {
		string = string.replace(/\r\n/g,"\n");
		var utftext = "";

		for (var n = 0; n < string.length; n++) {

			var c = string.charCodeAt(n);

			if (c < 128) {
				utftext += String.fromCharCode(c);
			}
			else if((c > 127) && (c < 2048)) {
				utftext += String.fromCharCode((c >> 6) | 192);
				utftext += String.fromCharCode((c & 63) | 128);
			}
			else {
				utftext += String.fromCharCode((c >> 12) | 224);
				utftext += String.fromCharCode(((c >> 6) & 63) | 128);
				utftext += String.fromCharCode((c & 63) | 128);
			}

		}

		return utftext;
	},

	// private method for UTF-8 decoding
	_utf8_decode : function (utftext) {
		var string = "";
		var i = 0;
		var c = c1 = c2 = 0;

		while ( i < utftext.length ) {

			c = utftext.charCodeAt(i);

			if (c < 128) {
				string += String.fromCharCode(c);
				i++;
			}
			else if((c > 191) && (c < 224)) {
				c2 = utftext.charCodeAt(i+1);
				string += String.fromCharCode(((c & 31) << 6) | (c2 & 63));
				i += 2;
			}
			else {
				c2 = utftext.charCodeAt(i+1);
				c3 = utftext.charCodeAt(i+2);
				string += String.fromCharCode(((c & 15) << 12) | ((c2 & 63) << 6) | (c3 & 63));
				i += 3;
			}

		}

		return string;
	}

};


function toDate(text) {
    // AIB format: DD/MM/YY
    var re = /(\d+)\/(\d+)\/(\d+)/;
    var dateChunks = re.exec(text);
    // the +2000 part is really horrible. Don't try that at home, kids.
    var newdate = new Date(
        parseInt(dateChunks[3], 10) + 2000,     // year
        parseInt(dateChunks[2], 10) - 1,        // month
        parseInt(dateChunks[1], 10)             // day
    );
    return newdate;
};


function toValue(text) {
    var tmp = text.replace(',','');
    if (tmp.match(/DR/)) {
        return parseFloat('-' + tmp);
    } else {
        return parseFloat(tmp);
    };
};


function toOfxDate(dateobject) {
    return dateobject.toLocaleFormat('%Y%m%d%H%M%S');
};




function aibParser() {

    var statementType;
    if ($('th:contains("Summary of last statement")').length > 0) {
        // it's a credit card statement
        statementType = 'cc'
    } else {
        statementType = 'checking'
    };

    var transactions = $('tr.jext01,tr.ext01').map(function() {
            // single row consists of following <td>s:
            // Checking:
            // Date, Description, Debit, Credit, Balance
            // CCard:
            // Date, Description, Debit, Credit
            var new_operation = {};
            var values = $(this).find('td').map(function() {
                    return $(this).text();
                }
            );
            new_operation.timestamp = toDate(values[0]);
            new_operation.description = values[1];
            new_operation.debit = toValue(values[2]);
            new_operation.credit = toValue(values[3]);
            if (statementType != 'cc') {
                new_operation.balance = toValue(values[4]);
            };
            if ( (!isNaN(new_operation.credit)) ||
                 (!isNaN(new_operation.debit))) {
                return new_operation;
            };
        }
    );
    transactions.type = statementType;
    transactions.currency = 'EUR';
    transactions.accountId = $('select#index').val();

    if (statementType == 'checking') {
        transactions.balance = transactions[transactions.length-1].balance;
    };

    transactions.available = GM_getValue(transactions.accountId);

    return transactions;

};


function ofxFormatter(transactions) {
    var reportDate = toOfxDate(new Date());
    var output = "OFXHEADER:100\nDATA:OFXSGML\nVERSION:102\nSECURITY:NONE\nENCODING:USASCII\nCHARSET:1252\nCOMPRESSION:NONE\nOLDFILEUID:NONE\nNEWFILEUID:NONE\n\n";
    output += "<OFX>\n<SIGNONMSGSRSV1>\n<SONRS>\n<STATUS>\n<CODE>0</CODE>\n<SEVERITY>INFO</SEVERITY>\n</STATUS>"
        + "<DTSERVER>" + reportDate +"</DTSERVER>\n"
        + "<LANGUAGE>ENG</LANGUAGE>\n</SONRS>\n</SIGNONMSGSRSV1>\n"

    if (transactions.type == 'checking') {
        output += "<BANKMSGSRSV1>\n<STMTTRNRS><TRNUID>1</TRNUID>\n"
        + "<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>\n"
        + "<STMTRS><CURDEF>" + transactions.currency + "</CURDEF>"
        + "<BANKACCTFROM><BANKID>AIB</BANKID>"
        + "<ACCTID>" + transactions.accountId + "</ACCTID>"
        + "<ACCTTYPE>CHECKING</ACCTTYPE>\n</BANKACCTFROM>\n\n";
    } else {
        output += "<CREDITCARDMSGSRSV1>\n<CCSTMTTRNRS><TRNUID>1</TRNUID>\n"
        + "<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>\n"
        + "<CCSTMTRS><CURDEF>" + transactions.currency + "</CURDEF>"
        + "<CCACCTFROM>"
        + "<ACCTID>" + transactions.accountId + "</ACCTID>"
        + "</CCACCTFROM>\n\n";
    };

    output += '<BANKTRANLIST>'
	+ '<DTSTART>' + toOfxDate(transactions[0].timestamp) + '</DTSTART>'
	+ '<DTEND>' + toOfxDate(transactions[transactions.length-1].timestamp) + '</DTEND>\n'

    for (var i = 0; i < transactions.length; i++) {
        var t = transactions[i];
        var amount = 0;
        output += "<STMTTRN>\n<TRNTYPE>";
        if (t.credit) {
            output += 'CREDIT</TRNTYPE>\n';
            amount = t.credit;
        } else {
            output += 'DEBIT</TRNTYPE>\n';
            amount = -t.debit;
        };
        var ofxDate = toOfxDate(t.timestamp);
        var tid = Crypto.SHA256(ofxDate + amount + t.description);
        output += '<DTPOSTED>' + ofxDate + '</DTPOSTED>\n';
        output += '<TRNAMT>' + amount + '</TRNAMT>\n';
        output += '<FITID>' + tid + '</FITID>\n';
        output += '<NAME>' + t.description + '</NAME>\n';
        output += '</STMTTRN>\n\n';
    }

    output += '</BANKTRANLIST>\n';

    if (transactions.type == 'checking') {
        output += '<LEDGERBAL><BALAMT>' + transactions.balance + '</BALAMT><DTASOF>' + reportDate + '</DTASOF></LEDGERBAL>\n'
            + '<AVAILBAL><BALAMT>' + transactions.available + '</BALAMT><DTASOF>' + reportDate + '</DTASOF></AVAILBAL>\n'
            + '</STMTRS> </STMTTRNRS> </BANKMSGSRSV1> </OFX>';
    } else {
        output += '<LEDGERBAL><BALAMT>' + transactions.available + '</BALAMT><DTASOF>' + reportDate + '</DTASOF></LEDGERBAL>\n'
            + '</CCSTMTRS> </CCSTMTTRNRS> </CREDITCARDMSGSRSV1></OFX>';
    };

    return output;
};


function csvFormatter(transactions) {
    var output = '';
    output += '# Date, Description, Operation\n';

    for (var i = 0; i < transactions.length; i++) {
        var t = transactions[i];
        output += t.timestamp.toLocaleDateString() + ', ' + t.description + ', ';
        if (t.debit) {
            output += '-' + t.debit;
        } else {
            output += t.credit;
        }
        output += '\n';
    };
    return output;
};


function newTabOutputter(content) {
    var newwin = window.open();
    newwin.document.open();
    var p = '<pre>' + content.replace(/\n/g, '<br>') + '</pre>';
    newwin.document.write(p);
    newwin.document.close();
};


function dataOutputter(content) {
    var newwin = window.open();
    // can't specify filename... yet
    // https://bugzilla.mozilla.org/show_bug.cgi?id=532230
    var dataUri = 'data:application/octet-stream;base64,' + Base64.encode(content);
    newwin.document.location = dataUri;
};


function mungeTransactions(parser, formatter, outputter) {
    //var transactionTable = $('table.aibtableStyle01');
    var transactions = parser();
    var output = formatter(transactions);
    outputter(output);
};


function createButtons() {
    $('table.aibtableStyle01').before('[<a id="aib2ofx" href="#aib2ofx">QFX</a>|<a id="aib2csv" href="#aib2csv">CSV</a>]');
    $('a#aib2ofx').bind('click', function(e) {
            mungeTransactions(aibParser, ofxFormatter, dataOutputter);
        }
    );
    $('a#aib2csv').bind('click', function(e) {
            mungeTransactions(aibParser, csvFormatter, dataOutputter);
        }
    );
};


function grabBalances() {
    $('div.acountOverviewLink').map(function() {
            var id = $(this).find('button').find('span').text();
            var amount = toValue($(this).find('h3').text());
            GM_setValue(id, amount.toString());
        }
    );
};


function init() {
    if (window.location == 'https://aibinternetbanking.aib.ie/inet/roi/statement.htm') {
        // create buttons & hook events
        createButtons();
    } else {
        // overview page, try to grab balances for later
        grabBalances();
    };
};


// start
$(document).ready(init);