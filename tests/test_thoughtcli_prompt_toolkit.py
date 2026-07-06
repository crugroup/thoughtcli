import json
from unittest.mock import MagicMock, patch
from requests.exceptions import HTTPError

import pytest

from thoughtcli import git_commit, git_deploy, git_deploy_validate, read_config, test_connection
from thoughtcli.connection import TSConnection, TSProfile


@pytest.fixture
def mock_connection():
    profile = TSProfile(server_url="https://example.thoughtspot.cloud", username="u", password="p")
    conn = TSConnection(profile)
    mock_v2 = MagicMock()
    mock_v2.__enter__ = MagicMock(return_value=mock_v2)
    mock_v2.__exit__ = MagicMock(return_value=False)
    conn.v2 = mock_v2
    return conn


def test_test_connection_success(mock_connection):
    result = test_connection(mock_connection)
    assert result == "Connection Successful"


def test_test_connection_failure(mock_connection):
    mock_connection.v2.__enter__.side_effect = Exception("timeout")
    result = test_connection(mock_connection)
    assert result == "Connection Failed: timeout"


def test_read_config_uses_env_var(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("profiles:\n  prod:\n    server_url: https://example.thoughtspot.cloud\n")
    monkeypatch.setenv("THOUGHTCLI_CONFIG_PATH", str(config_file))

    config = read_config()
    assert "profiles" in config
    assert "prod" in config["profiles"]


def test_read_config_uses_default_path(tmp_path, monkeypatch):
    monkeypatch.delenv("THOUGHTCLI_CONFIG_PATH", raising=False)
    monkeypatch.setattr("thoughtcli.Path.home", lambda: tmp_path)

    config_dir = tmp_path / ".thoughtcli"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("profiles:\n  prod:\n    server_url: https://example.thoughtspot.cloud\n")

    config = read_config()
    assert "profiles" in config
    assert "prod" in config["profiles"]


def test_read_config_exits_if_missing(monkeypatch):
    monkeypatch.setenv("THOUGHTCLI_CONFIG_PATH", "/nonexistent/config.yaml")
    with pytest.raises(SystemExit):
        read_config()


@patch("thoughtcli.input_dialog")
@patch("thoughtcli.checkboxlist_dialog")
def test_git_commit_cancelled_when_no_comment(mock_checkbox, mock_input, mock_connection):
    mock_connection.v2.__enter__.return_value.client.metadata_search.return_value = []
    mock_checkbox.return_value.run.return_value = []
    mock_input.return_value.run.return_value = None

    result = git_commit(mock_connection)
    assert result == "Cancelled"


@patch("thoughtcli.input_dialog")
@patch("thoughtcli.checkboxlist_dialog")
def test_git_commit_no_metadata_selected(mock_checkbox, mock_input, mock_connection):
    mock_connection.v2.__enter__.return_value.client.metadata_search.return_value = []
    mock_checkbox.return_value.run.return_value = []
    mock_input.return_value.run.return_value = "my commit"

    result = git_commit(mock_connection)
    assert result == "No metadata selected"


@patch("thoughtcli.input_dialog")
@patch("thoughtcli.checkboxlist_dialog")
def test_git_commit_success(mock_checkbox, mock_input, mock_connection):
    mock_connection.v2.__enter__.return_value.client.metadata_search.return_value = [
        {"metadata_id": "123", "metadata_name": "MyTable", "metadata_header": {"type": "ONE_TO_ONE_LOGICAL"}}
    ]
    mock_checkbox.return_value.run.return_value = ["123"]
    mock_input.return_value.run.return_value = "my commit"

    result = git_commit(mock_connection)
    assert result == "Commit Successful"


def test_git_commit_http_error(mock_connection):
    mock_connection.v2.__enter__.return_value.client.metadata_search.side_effect = HTTPError(response=MagicMock(text="bad request"))

    result = git_commit(mock_connection)
    assert result == "Commit Failed: \nbad request"


@patch("thoughtcli.input_dialog")
def test_git_deploy_validate_cancelled(mock_input):
    mock_input.return_value.run.return_value = None

    result = git_deploy_validate(MagicMock())
    assert result == "Cancelled"


@patch("thoughtcli.input_dialog")
def test_git_deploy_validate_cancelled_on_target(mock_input, mock_connection):
    mock_input.return_value.run.side_effect = ["source-branch", None]

    result = git_deploy_validate(mock_connection)
    assert result == "Cancelled"


@patch("thoughtcli.input_dialog")
def test_git_deploy_validate_success(mock_input, mock_connection):
    mock_input.return_value.run.side_effect = ["source-branch", "target-branch"]
    mock_connection.v2.__enter__.return_value.client.vcs_git_branches_validate.return_value = {"status": "success"}

    result = git_deploy_validate(mock_connection)
    assert result == "Deployment validation successful: " + json.dumps({"status": "success"}, indent=4)


@patch("thoughtcli.input_dialog")
def test_git_deploy_validate_http_error(mock_input, mock_connection):
    mock_input.return_value.run.side_effect = ["source-branch", "target-branch"]
    mock_connection.v2.__enter__.return_value.client.vcs_git_branches_validate.side_effect = HTTPError(response=MagicMock(text="conflict"))

    result = git_deploy_validate(mock_connection)
    assert result == "Deployment validation failed: \nconflict"


@patch("thoughtcli.input_dialog")
def test_git_deploy_cancelled_on_branch(mock_input):
    mock_input.return_value.run.return_value = None

    result = git_deploy(MagicMock())
    assert result == "Cancelled"


@patch("thoughtcli.radiolist_dialog")
@patch("thoughtcli.input_dialog")
def test_git_deploy_cancelled_on_type(mock_input, mock_radio, mock_connection):
    mock_input.return_value.run.return_value = "main"
    mock_radio.return_value.run.return_value = None

    result = git_deploy(mock_connection)
    assert result == "Cancelled"


@patch("thoughtcli.radiolist_dialog")
@patch("thoughtcli.input_dialog")
def test_git_deploy_cancelled_on_policy(mock_input, mock_radio, mock_connection):
    mock_input.return_value.run.return_value = "main"
    mock_radio.return_value.run.side_effect = ["DELTA", None]

    result = git_deploy(mock_connection)
    assert result == "Cancelled"


@patch("thoughtcli.radiolist_dialog")
@patch("thoughtcli.input_dialog")
def test_git_deploy_success(mock_input, mock_radio, mock_connection):
    mock_input.return_value.run.return_value = "main"
    mock_radio.return_value.run.side_effect = ["DELTA", "ALL_OR_NONE"]
    mock_connection.v2.__enter__.return_value.client.vcs_git_commits_deploy.return_value = {"status": "success"}

    result = git_deploy(mock_connection)
    assert result == "Deployment successful: " + json.dumps({"status": "success"}, indent=4)


@patch("thoughtcli.radiolist_dialog")
@patch("thoughtcli.input_dialog")
def test_git_deploy_http_error(mock_input, mock_radio, mock_connection):
    mock_input.return_value.run.return_value = "main"
    mock_radio.return_value.run.side_effect = ["DELTA", "ALL_OR_NONE"]
    mock_connection.v2.__enter__.return_value.client.vcs_git_commits_deploy.side_effect = HTTPError(response=MagicMock(text="error"))

    result = git_deploy(mock_connection)
    assert result == "Deployment failed: \nerror"
