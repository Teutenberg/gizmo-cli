import pytest
from click.testing import CliRunner
from unittest.mock import patch

from gizmo.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


# --- init ---

def test_init_writes_config(runner, tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path):
        with patch("gizmo.cli.config_init") as mock_init:
            result = runner.invoke(cli, ["init", "--database", "mydb", "--schema", "myschema"])
    mock_init.assert_called_once()
    assert result.exit_code == 0


# --- config list ---

def test_config_list_all(runner):
    with patch("gizmo.cli.config_list", return_value={"foo": "bar", "baz": "qux"}):
        result = runner.invoke(cli, ["config", "list"])
    assert result.exit_code == 0
    assert "foo: bar" in result.output
    assert "baz: qux" in result.output


def test_config_list_single_key(runner):
    with patch("gizmo.cli.config_get", return_value="bar"):
        result = runner.invoke(cli, ["config", "list", "foo"])
    assert result.exit_code == 0
    assert "bar" in result.output


def test_config_list_missing_key(runner):
    with patch("gizmo.cli.config_list", return_value={}):
        result = runner.invoke(cli, ["config", "list", "missing"])
    assert result.exit_code != 0
    assert "missing" in result.output


# --- config set ---

def test_config_set(runner):
    with patch("gizmo.cli.config_set") as mock_set:
        result = runner.invoke(cli, ["config", "set", "foo", "bar"])
    assert mock_set.call_args[0][1:] == ("foo", "bar")
    assert result.exit_code == 0


# --- config unset ---

def test_config_unset(runner):
    with patch("gizmo.cli.config_unset") as mock_unset:
        result = runner.invoke(cli, ["config", "unset", "foo"])
    mock_unset.assert_called_once_with("foo")
    assert result.exit_code == 0


# --- secret list ---

def test_secret_list(runner):
    with patch("gizmo.cli.keyring_list", return_value=["personal_access_token", "api_key"]):
        result = runner.invoke(cli, ["secret", "list"])
    assert result.exit_code == 0
    assert "personal_access_token" in result.output
    assert "api_key" in result.output


# --- secret set ---

def test_secret_set(runner):
    with patch("gizmo.cli.keyring_set") as mock_set:
        result = runner.invoke(cli, ["secret", "set", "--name", "mykey", "--value", "myvalue"])
    mock_set.assert_called_once_with("mykey", "myvalue")
    assert result.exit_code == 0


# --- secret delete ---

def test_secret_delete(runner):
    with patch("gizmo.cli.keyring_delete") as mock_delete:
        result = runner.invoke(cli, ["secret", "delete", "mykey"])
    mock_delete.assert_called_once_with("mykey")
    assert result.exit_code == 0


# --- secret rotate_key ---

def test_secret_rotate_key(runner):
    with patch("gizmo.cli.keyring_rotate_key") as mock_rotate:
        result = runner.invoke(cli, ["secret", "rotate_key"])
    mock_rotate.assert_called_once()
    assert result.exit_code == 0
