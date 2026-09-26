from importlib import metadata


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
