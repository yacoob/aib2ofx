"""Tests for the command line interface."""

import sys

import pytest

from aib2ofx import cli


@pytest.fixture
def argv(monkeypatch):
    """Return a helper that runs get_options against a given command line."""

    def parse(*args):
        monkeypatch.setattr(sys, 'argv', ['aib2ofx', *args])
        return cli.get_options()

    return parse


def test_config_defaults_to_the_home_dotfile(argv):
    """Without -c, credentials are read from ~/.aib2ofx.json."""
    assert argv().config_file == '~/.aib2ofx.json'


def test_config_accepts_a_short_flag(argv):
    """-c points the reader at another file."""
    assert (
        argv('-c', '/run/secrets/aib.json').config_file
        == '/run/secrets/aib.json'
    )


def test_config_accepts_a_long_flag(argv):
    """--config points the reader at another file."""
    assert argv('--config', 'creds.json').config_file == 'creds.json'
