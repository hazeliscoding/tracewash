from importlib import metadata

import pytest
from definition_samples import VALID, changed, write_definition

from tracewash import definitions


@pytest.fixture
def brokers_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(definitions, "BROKERS_DIR", tmp_path)
    return tmp_path


def test_version_prints_the_installed_version(cli):
    result = cli("--version")

    assert result.exit_code == 0
    assert result.stdout == f"tracewash {metadata.version('tracewash')}\n"


def test_status_says_its_output_is_a_sample(cli):
    result = cli("status")

    assert result.exit_code == 0
    assert result.stdout.splitlines()[0].startswith("sample output")


def test_status_lists_brokers_by_state(cli):
    lines = cli("status").stdout.splitlines()

    for label in ("brokers", "removed", "requested", "action required", "listed again"):
        assert any(line.startswith(f"{label} ") for line in lines), label


def test_brokers_list_shows_each_broker_with_its_opt_out_method(cli, brokers_dir):
    write_definition(brokers_dir, VALID)
    write_definition(brokers_dir, changed("id", "otherpeople"), stem="otherpeople")

    result = cli("brokers", "list")

    assert result.exit_code == 0
    rows = [line.split() for line in result.stdout.splitlines()[1:]]
    assert [(row[0], row[-1]) for row in rows] == [
        ("otherpeople", "form"),
        ("peoplesearch", "form"),
    ]


def test_brokers_list_points_to_check_when_a_definition_is_broken(cli, brokers_dir):
    write_definition(brokers_dir, changed("recheck_days", 0))

    result = cli("brokers", "list")

    assert result.exit_code == 1
    assert "tracewash brokers check" in result.stderr


def test_brokers_check_passes_valid_definitions(cli, brokers_dir):
    write_definition(brokers_dir, VALID)

    result = cli("brokers", "check")

    assert result.exit_code == 0
    assert result.stdout == "1 definition checked, all valid\n"


def test_brokers_check_fails_an_invalid_definition(cli, brokers_dir):
    write_definition(brokers_dir, VALID)
    write_definition(brokers_dir, changed("recheck_days", 0), stem="broken")

    result = cli("brokers", "check")

    assert result.exit_code == 1
    assert "broken.yaml" in result.stderr
    assert "peoplesearch.yaml" not in result.stderr
    assert result.stdout == "2 definitions checked, 1 invalid\n"


def test_brokers_check_accepts_a_directory(cli, tmp_path):
    write_definition(tmp_path, changed("recheck_days", 0))

    result = cli("brokers", "check", str(tmp_path))

    assert result.exit_code == 1


def test_brokers_check_passes_the_shipped_definitions(cli):
    assert cli("brokers", "check").exit_code == 0
