import sys
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from tracewash.cli import app

FAKE_PROFILE = yaml.safe_load(
    (Path(__file__).parent / "fixtures" / "fake-profile.yaml").read_text(
        encoding="utf-8"
    )
)
# The state, age and birth year are too common to search test output for.
CANARY_FIELDS = ("first_name", "last_name", "city", "email", "phone", "street")
CANARY_PROFILE = {field: FAKE_PROFILE[field] for field in CANARY_FIELDS}


@pytest.fixture
def canary_profile():
    return dict(FAKE_PROFILE)


@pytest.fixture
def cli():
    runner = CliRunner()

    def invoke(*args):
        result = runner.invoke(app, list(args), catch_exceptions=False)
        # CliRunner keeps output to itself. Writing it out puts it in pytest's
        # capture, where the guard checks it.
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result

    return invoke


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    # Loggers below the capture level never reach the report, so a DEBUG line
    # holding a profile value would slip past the guard.
    config.option.log_level = "DEBUG"


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    if report.failed:
        return report
    leaks = [
        f"{field} reached {title.removeprefix('Captured ')}"
        # Sections accumulate across phases; checking only this phase's avoids
        # reporting one leak again at teardown.
        for title, content in report.sections
        if title.endswith(f" {report.when}")
        for field, value in CANARY_PROFILE.items()
        if value.casefold() in content.casefold()
    ]
    if leaks:
        report.outcome = "failed"
        report.longrepr = "canary guard: " + "; ".join(leaks)
    return report
