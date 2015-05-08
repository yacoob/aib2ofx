# aib2ofx
...or how to suck data out of AIB's online interface, and format it into `OFX` file.
Also supports conversion of pre-downloaded AIB e-statements.


## Installation

If your `pip` install is new enough, it's sufficient to run this:

    pip install 'git+git://github.com/yacoob/aib2ofx.git@HEAD'

If your `pip` doesn't support installing from VCS sources, or you just want to
do things the traditional way, execute following commands:

    umask 022
    python setup.py build
    sudo python setup.py install

All missing dependencies should be installed as well. If that has completed
successfully, you should find `aib2ofx` command in your Python's `bin` dir.


## How to use

Create a `~/.aib-sucker` file, with AIB login details.
Set the permission bits to 0600 to prevent other system users from reading it.

    touch ~/.aib-sucker
    chmod 0600 ~/.aib-sucker

It has a JSON format, single object with one key per AIB login you want to use.

    {
        "bradmajors": {
            "regNumber": "12345678",
            "pin": "12345"
        }
    }

The fields are, as follows:

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

To convert AIB PDF e-statements, download the statements from online banking and
put them in a directory of your choice.
Then run:

    aib2ofx -d /output/directory -p /pdf/statement/directory

## Guarantee

There is none.

I've written that script with my best intentions, it's not malicious,
it's not sending the data anywhere, it's not doing anything nasty. I'm
using it day to day to get data about my AIB accounts into a financial
program that I use. It should work for you as good as it works for
me. See the `LICENSE` file for more details.
