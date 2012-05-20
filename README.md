# aib2ofx
...or how to suck data out of AIB's online interface, and format it into `OFX` file.
Also supports conversion of AIB e-statements.


## Installation

* Get [setuptools](http://pypi.python.org/pypi/setuptools) if you don't have it already.
* `umask 022`
* `python setup.py build`
* `sudo python setup.py install`

If that has completed successfully, you should find `aib2ofx` command
in your Python's `bin` dir.


## How to use

Create a `~/.aib-sucker` file, with AIB login details. It has a JSON
format, single object with one key per AIB login you want to use.

    {
        "bradmajors": {
            "homeNumber": "1234",
            "workNumber": "1234",
            "regNumber": "12345678",
            "pin": "12345"
        }
    }

The fields are, as follows:

* homeNumber
    > Last four digits of your home number.

* workNumber
    > Last four digits of your work number.

* regNumber
    > Your AIB registered number.

* pin
    > Your five digit PIN.

You can put more than one set of credentials in the file; the script
will download data for all accounts for all logins.

    {
        "bradmajors": {
            "homeNumber": "1234",
            "workNumber": "1234",
            "regNumber": "12345678",
            "pin": "12345"
        },
        "janetweiss": {
            "homeNumber": "4321",
            "workNumber": "8765",
            "regNumber": "87654321",
            "pin": "54321"
        }
    }

Note that there's no comma after the last account details. Remember to
run `chmod 600 ~/.aib-sucker`, to make sure that only you can read
this file.

Once you've prepared that config file, run:

    aib2ofx -d /output/directory

The script should connect to AIB, log in using provided credentials,
iterate through all accounts, and save each of those to a separate
file located in `/output/directory`.

To convert AIB PDF e-statements, download the statements from online banking and
put them in a folder of your choice.
Then run:

    aib2ofx -d /output/directory -p /pdf/statement/directory

## Guarantee

There is none.

I've written that script with my best intentions, it's not malicious,
it's not sending the data anywhere, it's not doing anything nasty. I'm
using it day to day to get data about my AIB accounts into a financial
program that I use. It should work for you as good as it works for
me. See the `LICENSE` file for more details.

## Varia

`GM` directory contains a crude GreaseMonkey version. It allows you to
download transactions in either OFX or CSV format, from *Statement*
page, but you have to do it account by account. See the `GM/README.md`
for details.
