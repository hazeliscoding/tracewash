import re

import pytest
from test_profile_cli import PASSPHRASE, init_input

from tracewash import evidence, paths
from tracewash.tracker import Tracker
from tracewash.vault import Vault

WHEN = r"\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}"


@pytest.fixture
def screenshot(tmp_path, canary_profile):
    path = tmp_path / "shot.png"
    path.write_bytes(f"no results for {canary_profile['last_name']}".encode())
    return path


@pytest.fixture
def vault_ready(cli, canary_profile):
    assert cli("init", input=init_input(canary_profile)).exit_code == 0


def test_track_records_what_you_saw(cli):
    result = cli("track", "spokeo", "found")

    assert result.exit_code == 0
    assert result.stdout == "spokeo: listed\n"


def test_track_refuses_an_unknown_broker(cli):
    result = cli("track", "nosuchbroker", "found")

    assert result.exit_code == 1
    assert "no broker called nosuchbroker" in result.stderr


def test_track_refuses_a_step_the_table_does_not_allow(cli):
    result = cli("track", "spokeo", "requested")

    assert result.exit_code == 1
    assert "requested can't follow not checked" in result.stderr


def test_removal_without_evidence_is_refused_before_asking_for_the_passphrase(cli):
    cli("track", "spokeo", "found")

    result = cli("track", "spokeo", "not-found")

    assert result.exit_code == 1
    assert "needs evidence" in result.stderr
    assert "Passphrase" not in result.stdout


def test_a_full_manual_cycle_ends_removed_with_proof(cli, vault_ready, screenshot):
    cli("track", "spokeo", "found")
    cli("track", "spokeo", "requested")

    result = cli(
        "track",
        "spokeo",
        "not-found",
        "--evidence",
        str(screenshot),
        input=PASSPHRASE + "\n",
    )

    assert result.exit_code == 0
    assert re.search(r"spokeo: removed, evidence [0-9a-f]{8}\n$", result.stdout)
    with Tracker(paths.tracker_path()) as tracker:
        proof = tracker.timeline("spokeo")[-1].evidence
    _, stored = evidence.load(Vault.unlock(paths.vault_dir(), PASSPHRASE), proof)
    assert stored == screenshot.read_bytes()


def test_a_wrong_passphrase_records_nothing(cli, vault_ready, screenshot):
    cli("track", "spokeo", "found")

    result = cli(
        "track",
        "spokeo",
        "not-found",
        "--evidence",
        str(screenshot),
        input="wrong one\n",
    )

    assert result.exit_code == 1
    with Tracker(paths.tracker_path()) as tracker:
        assert len(tracker.timeline("spokeo")) == 1


def test_a_missing_evidence_file_is_refused_without_naming_it(cli, tmp_path):
    cli("track", "spokeo", "found")
    missing = tmp_path / "Quillfeather search.png"

    result = cli("track", "spokeo", "not-found", "--evidence", str(missing))

    assert result.exit_code == 1
    assert "evidence file doesn't exist" in result.stderr


def test_timeline_shows_each_step_with_its_time_and_proof(cli, vault_ready, screenshot):
    cli("track", "spokeo", "found")
    cli("track", "spokeo", "requested")
    cli(
        "track",
        "spokeo",
        "not-found",
        "--evidence",
        str(screenshot),
        input=PASSPHRASE + "\n",
    )

    lines = cli("timeline", "spokeo").stdout.splitlines()

    assert [line.split()[2:4] for line in lines] == [
        ["found", "listed"],
        ["requested", "requested"],
        ["not-found", "removed"],
    ]
    assert all(re.match(WHEN, line) for line in lines)
    assert re.search(r"evidence [0-9a-f]{8}$", lines[-1])


def test_timeline_of_an_untouched_broker_says_so(cli):
    assert cli("timeline", "spokeo").stdout == "spokeo: not checked yet\n"


def test_status_starts_with_every_broker_not_checked(cli):
    lines = cli("status").stdout.splitlines()

    assert re.match(r"brokers +10 tracked, 10 covered by DROP$", lines[0])
    assert re.match(r"not checked +10$", lines[1])


def test_status_groups_brokers_by_state(cli):
    cli("track", "spokeo", "found")
    cli("track", "whitepages", "found")
    cli("track", "whitepages", "requested")
    cli("track", "mylife", "blocked")

    lines = cli("status").stdout.splitlines()

    assert re.match(r"action required +1 mylife$", lines[1])
    assert re.match(r"listed +1 spokeo$", lines[2])
    assert re.match(r"requested +1 whitepages$", lines[3])
    assert re.match(r"not checked +7$", lines[4])
