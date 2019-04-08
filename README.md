# aib2ofx
...or how to grab transaction data out of AIB's online interface, and format it
into `OFX` file.

## Installation

    pipenv --two install 'git+git://github.com/yacoob/aib2ofx.git@master#egg=aib2ofx'

This will create a virtualenv for `aib2ofx`, fetch its code then install it with
all dependencies. Once that completes, you'll find `aib2ofx` executable in the
`bin` directory of this new virtualenv.

## Usage

Create a `~/.aib2ofx.json` file, with AIB login details.
Set the permission bits to 0600 to prevent other system users from reading it.

    touch ~/.aib2ofx.json
    chmod 0600 ~/.aib2ofx.json

It has a JSON format, single object with one key per AIB login you want to use.

    {
        "bradmajors": {
            "regNumber": "12345678",
            "pin": "12345"
        }
    }

The fields are as follows:

* regNumber
    > Your AIB registered number.

* pin
    > Your five digit PIN.

You can put more than one set of credentials in the file; the script
will download data for all accounts for all logins.

    {
        "bradmajors": {
            "regNumber": "12345678",
            "pin": "12345"
        },
        "janetweiss": {
            "regNumber": "87654321",
            "pin": "54321"
        }
    }

Note that there's no comma after the last account details.

Once you've prepared that config file, run:

    aib2ofx -d /output/directory

The script should connect to AIB, log in using provided credentials,
iterate through all accounts, and save each of those to a separate
file located in `/output/directory`.

## Guarantee

There is none.

I've written that script with my best intentions, it's not malicious,
it's not sending the data anywhere, it's not doing anything nasty. I'm
using it day to day to get data about my AIB accounts into a financial
program that I use. It should work for you as good as it works for
me. See the `LICENSE` file for more details.
