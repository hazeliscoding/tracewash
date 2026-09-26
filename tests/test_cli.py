from importlib import metadata


def test_version_prints_the_installed_version(cli):
    result = cli("--version")

    assert result.exit_code == 0
    assert result.stdout == f"tracewash {metadata.version('tracewash')}\n"
