import json
from unittest.mock import AsyncMock, MagicMock
from requests.exceptions import HTTPError

import pytest

from thoughtcli import ThoughtCLIApp, read_config


@pytest.fixture
def app():
    return ThoughtCLIApp(
        config={
            "profiles": {
                "dev": {
                    "server_url": "https://example.thoughtspot.cloud",
                    "username": "u",
                    "password": "p",
                }
            }
        }
    )


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    conn.v2.__enter__ = MagicMock(return_value=conn.v2)
    conn.v2.__exit__ = MagicMock(return_value=False)
    return conn


def test_test_connection_success(app, mock_conn):
    result = app._test_connection(mock_conn)
    assert result == "Connection Successful"


def test_test_connection_failure(app, mock_conn):
    mock_conn.v2.__enter__.side_effect = Exception("timeout")
    result = app._test_connection(mock_conn)
    assert result == "Connection Failed: timeout"


def test_read_config_uses_env_var(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "profiles:\n  dev:\n    server_url: https://example.thoughtspot.cloud\n"
    )
    monkeypatch.setenv("THOUGHTCLI_CONFIG_PATH", str(config_file))

    config = read_config()
    assert "profiles" in config
    assert "dev" in config["profiles"]


def test_read_config_uses_default_path(tmp_path, monkeypatch):
    monkeypatch.delenv("THOUGHTCLI_CONFIG_PATH", raising=False)
    monkeypatch.setattr("thoughtcli.Path.home", lambda: tmp_path)

    config_dir = tmp_path / ".thoughtcli"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(
        "profiles:\n  dev:\n    server_url: https://example.thoughtspot.cloud\n"
    )

    config = read_config()
    assert "profiles" in config
    assert "dev" in config["profiles"]


def test_read_config_exits_if_missing(monkeypatch):
    monkeypatch.setenv("THOUGHTCLI_CONFIG_PATH", "/nonexistent/config.yaml")
    with pytest.raises(SystemExit):
        read_config()


async def test_git_commit_cancelled_when_no_comment(app, mock_conn):
    app.push_screen_wait = AsyncMock(side_effect=[[], [], [], None])
    result = await app._git_commit(mock_conn)
    assert result == "Cancelled"


async def test_git_commit_no_metadata_selected(app, mock_conn):
    app.push_screen_wait = AsyncMock(side_effect=[[], [], [], "my commit"])
    result = await app._git_commit(mock_conn)
    assert result == "No metadata selected"


async def test_git_commit_success(app, mock_conn):
    app.push_screen_wait = AsyncMock(side_effect=[["table-id"], [], [], "my commit"])
    result = await app._git_commit(mock_conn)
    assert result == "Commit Successful"


async def test_git_commit_http_error(app, mock_conn):
    mock_conn.v2.__enter__.side_effect = HTTPError(
        response=MagicMock(text="bad request")
    )
    result = await app._git_commit(mock_conn)
    assert result == "Commit Failed: \nbad request"


async def test_git_deploy_validate_cancelled_on_source(app, mock_conn):
    app.push_screen_wait = AsyncMock(return_value=None)
    result = await app._git_deploy_validate(mock_conn)
    assert result == "Cancelled"


async def test_git_deploy_validate_cancelled_on_target(app, mock_conn):
    app.push_screen_wait = AsyncMock(side_effect=["source-branch", None])
    result = await app._git_deploy_validate(mock_conn)
    assert result == "Cancelled"


async def test_git_deploy_validate_success(app, mock_conn):
    mock_conn.v2.client.vcs_git_branches_validate.return_value = {"status": "success"}
    app.push_screen_wait = AsyncMock(side_effect=["source-branch", "target-branch"])
    result = await app._git_deploy_validate(mock_conn)
    assert result == "Deployment validation successful: " + json.dumps(
        {"status": "success"}, indent=4
    )


async def test_git_deploy_validate_http_error(app, mock_conn):
    mock_conn.v2.client.vcs_git_branches_validate.side_effect = HTTPError(
        response=MagicMock(text="conflict")
    )
    app.push_screen_wait = AsyncMock(side_effect=["source-branch", "target-branch"])
    result = await app._git_deploy_validate(mock_conn)
    assert result == "Deployment validation failed: \nconflict"


async def test_git_deploy_cancelled_on_branch(app, mock_conn):
    app.push_screen_wait = AsyncMock(return_value=None)
    result = await app._git_deploy(mock_conn)
    assert result == "Cancelled"


async def test_git_deploy_cancelled_on_type(app, mock_conn):
    app.push_screen_wait = AsyncMock(side_effect=["main", None])
    result = await app._git_deploy(mock_conn)
    assert result == "Cancelled"


async def test_git_deploy_cancelled_on_policy(app, mock_conn):
    app.push_screen_wait = AsyncMock(side_effect=["main", "DELTA", None])
    result = await app._git_deploy(mock_conn)
    assert result == "Cancelled"


async def test_git_deploy_success(app, mock_conn):
    mock_conn.v2.client.vcs_git_commits_deploy.return_value = {"status": "success"}
    app.push_screen_wait = AsyncMock(side_effect=["main", "DELTA", "ALL_OR_NONE"])
    result = await app._git_deploy(mock_conn)
    assert result == "Deployment successful: " + json.dumps(
        {"status": "success"}, indent=4
    )


async def test_git_deploy_http_error(app, mock_conn):
    mock_conn.v2.client.vcs_git_commits_deploy.side_effect = HTTPError(
        response=MagicMock(text="error")
    )
    app.push_screen_wait = AsyncMock(side_effect=["main", "DELTA", "ALL_OR_NONE"])
    result = await app._git_deploy(mock_conn)
    assert result == "Deployment failed: \nerror"
