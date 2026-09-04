"""Tests for the configuration file reader."""

import json

import pytest

from aib2ofx import cfg

CREDENTIALS = {
    'bradmajors': {'regNumber': '12345678', 'pin': '12345'},
    'janetweiss': {'regNumber': '87654321', 'pin': '54321'},
}


@pytest.fixture
def config_file(tmp_path):
    """Write CREDENTIALS out as JSON and return the file's path."""
    path = tmp_path / 'aib2ofx.json'
    path.write_text(json.dumps(CREDENTIALS))
    return str(path)


def test_reads_every_configured_user(config_file):
    """Every top level key is reported as a user."""
    assert sorted(cfg.Config(config_file).users()) == [
        'bradmajors',
        'janetweiss',
    ]


def test_exposes_credentials_by_user(config_file):
    """Indexing by user name yields that user's credentials."""
    assert cfg.Config(config_file)['bradmajors'] == CREDENTIALS['bradmajors']


def test_rejects_unknown_user(config_file):
    """Indexing by an unknown user name raises."""
    with pytest.raises(AttributeError):
        cfg.Config(config_file)['frankfurter']


def test_tolerates_trailing_commas(tmp_path):
    """A comma before a closing brace does not break parsing."""
    path = tmp_path / 'aib2ofx.json'
    path.write_text('{"bradmajors": {"regNumber": "1", "pin": "2",},}')
    assert cfg.Config(str(path)).users() == ['bradmajors']


def test_defaults_to_a_dotfile_in_the_home_directory(tmp_path, monkeypatch):
    """With no path given, the config is read from ~/.aib2ofx.json."""
    monkeypatch.setenv('HOME', str(tmp_path))
    (tmp_path / '.aib2ofx.json').write_text(json.dumps(CREDENTIALS))
    assert sorted(cfg.Config().users()) == ['bradmajors', 'janetweiss']
