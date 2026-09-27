import os
from pathlib import Path

import pytest


@pytest.fixture
def run_inner_test(pytester, monkeypatch):
    # The inner session gets its own process so its log records can't reach
    # this test's log capture.
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).parent))

    def run(line):
        pytester.makepyfile(
            f"""
            import logging
            import os
            import sys

            def test_inner(canary_profile):
                {line}
            """
        )
        # --show-capture=no keeps the inner test's output, canary included,
        # out of this test's own stdout.
        return pytester.runpytest_subprocess("-p", "canary_guard", "--show-capture=no")

    return run


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("print(canary_profile['email'])", "email reached stdout call"),
        ("sys.stderr.write(canary_profile['phone'])", "phone reached stderr call"),
        (
            "logging.getLogger('tracewash').debug(canary_profile['street'])",
            "street reached log call",
        ),
        ("print(canary_profile['last_name'].upper())", "last_name reached stdout call"),
        (
            "os.makedirs(os.path.join(os.environ['TRACEWASH_HOME'], 'vault'));"
            "open(os.path.join(os.environ['TRACEWASH_HOME'], 'vault', 'profile.bin'), 'w')"
            ".write(canary_profile['city'])",
            "city reached file vault/profile.bin",
        ),
    ],
    ids=["stdout", "stderr", "debug-log", "changed-case", "file"],
)
def test_guard_fails_a_test_that_leaks_a_profile_value(run_inner_test, line, expected):
    result = run_inner_test(line)

    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines([f"*canary guard:*{expected}*"])


def test_guard_passes_a_test_that_leaks_nothing(run_inner_test):
    result = run_inner_test("print('status ok')")

    result.assert_outcomes(passed=1)


def test_cli_fixture_sends_output_through_capture(cli, capsys):
    cli("--version")

    assert capsys.readouterr().out.startswith("tracewash ")


def test_each_test_gets_its_own_empty_tracewash_home(tmp_path):
    home = Path(os.environ["TRACEWASH_HOME"])

    assert home.parent == tmp_path
    assert list(home.iterdir()) == []
