from unittest.mock import MagicMock

import pytest

from thoughtcli.connection import TSConnection, TSProfile, V2Connection


def test_tsprofile_defaults():
    p = TSProfile(server_url="https://example.thoughtspot.cloud")
    assert p.username is None
    assert p.password is None
    assert p.org_identifier is None
    assert p.secret_key is None


def test_tsconnection_default_metadata_max_size():
    p = TSProfile(server_url="https://example.thoughtspot.cloud")
    conn = TSConnection(p)
    assert conn.metadata_max_size == 1000


def test_tsconnection_custom_metadata_max_size():
    p = TSProfile(server_url="https://example.thoughtspot.cloud")
    conn = TSConnection(p, metadata_max_size=500)
    assert conn.metadata_max_size == 500


def test_auth_uses_userpass_when_both_set():
    p = TSProfile(server_url="https://example.thoughtspot.cloud", username="u", password="p")
    conn = V2Connection(p)
    assert conn.user_pass_auth


def test_auth_no_userpass_when_missing():
    p = TSProfile(server_url="https://example.thoughtspot.cloud", secret_key="sk")
    conn = V2Connection(p)
    assert conn.user_pass_auth is None


@pytest.fixture
def userpass_conn():
    p = TSProfile(server_url="https://example.thoughtspot.cloud", username="u", password="p", org_identifier=42)
    conn = V2Connection(p)
    conn.client = MagicMock()
    return conn


@pytest.fixture
def token_conn():
    p = TSProfile(server_url="https://example.thoughtspot.cloud", username="u", secret_key="sk")
    conn = V2Connection(p)
    conn.client = MagicMock()
    conn.client.auth_token_full.return_value = {"token": "test"}
    return conn


def test_v2connection_enter_uses_session_login(userpass_conn):
    userpass_conn.__enter__()
    userpass_conn.client.auth_session_login.assert_called_once_with(
        username="u", password="p", org_identifier=42
    )


def test_v2connection_enter_uses_token_when_no_password(token_conn):
    token_conn.__enter__()
    token_conn.client.auth_token_full.assert_called_once_with(
    username="u", secret_key="sk", org_id=None
)
    assert token_conn.client.bearer_token == "test"


def test_v2connection_exit_calls_logout(userpass_conn):
    userpass_conn.__exit__(None, None, None)
    userpass_conn.client.auth_session_logout.assert_called_once()
