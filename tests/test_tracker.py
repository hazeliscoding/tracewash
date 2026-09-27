import sqlite3
from datetime import UTC

import pytest

from tracewash import paths
from tracewash.states import Event, InvalidTransition, State
from tracewash.tracker import ProofRequired, Tracker

EVIDENCE = "0123456789abcdef0123456789abcdef"


@pytest.fixture
def tracker():
    with Tracker(paths.tracker_path()) as opened:
        yield opened


def test_a_broker_with_no_events_is_not_checked(tracker):
    assert tracker.state("spokeo") is State.NOT_CHECKED
    assert tracker.timeline("spokeo") == []


def test_a_full_cycle_ends_removed_with_its_proof(tracker):
    tracker.record("spokeo", Event.FOUND)
    tracker.record("spokeo", Event.REQUESTED)
    tracker.record("spokeo", Event.NOT_FOUND, evidence=EVIDENCE)

    timeline = tracker.timeline("spokeo")
    assert [(entry.event, entry.state) for entry in timeline] == [
        (Event.FOUND, State.LISTED),
        (Event.REQUESTED, State.REQUESTED),
        (Event.NOT_FOUND, State.REMOVED),
    ]
    assert timeline[-1].evidence == EVIDENCE
    assert all(entry.at.tzinfo is UTC for entry in timeline)


def test_removed_without_proof_is_refused_and_not_recorded(tracker):
    tracker.record("spokeo", Event.FOUND)

    with pytest.raises(ProofRequired, match="evidence"):
        tracker.record("spokeo", Event.NOT_FOUND)

    assert tracker.state("spokeo") is State.LISTED


def test_an_invalid_event_is_refused_and_not_recorded(tracker):
    with pytest.raises(InvalidTransition):
        tracker.record("spokeo", Event.REQUESTED)

    assert tracker.timeline("spokeo") == []


def test_not_found_before_any_listing_needs_no_proof(tracker):
    assert tracker.record("spokeo", Event.NOT_FOUND).state is State.NO_RECORD


def test_the_timeline_survives_reopening(tracker):
    tracker.record("spokeo", Event.FOUND)
    tracker.close()

    with Tracker(paths.tracker_path()) as reopened:
        assert reopened.state("spokeo") is State.LISTED


def test_states_lists_every_broker_with_events(tracker):
    tracker.record("spokeo", Event.FOUND)
    tracker.record("whitepages", Event.NOT_FOUND)

    assert tracker.states() == {"spokeo": State.LISTED, "whitepages": State.NO_RECORD}


def test_the_database_has_no_column_for_free_text(tracker):
    columns = {
        row[1]
        for row in sqlite3.connect(paths.tracker_path()).execute(
            "PRAGMA table_info(events)"
        )
    }

    assert columns == {"id", "broker", "event", "at", "evidence"}
