from importlib import metadata

from typer.testing import CliRunner

from tracewash.cli import app


def test_version_prints_the_installed_version():
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout == f"tracewash {metadata.version('tracewash')}\n"
