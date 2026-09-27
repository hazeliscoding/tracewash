import pytest

from tracewash.states import (
    TRANSITIONS,
    Event,
    InvalidTransition,
    State,
    replay,
    state_after,
)

E, S = Event, State
SETTLED = (S.NOT_CHECKED, S.NO_RECORD, S.LISTED, S.REQUESTED, S.REMOVED, S.LISTED_AGAIN)


@pytest.mark.parametrize(
    ("events", "expected"),
    [
        ([], S.NOT_CHECKED),
        ([E.FOUND], S.LISTED),
        ([E.NOT_FOUND], S.NO_RECORD),
        ([E.NOT_FOUND, E.FOUND], S.LISTED),
        ([E.FOUND, E.FOUND], S.LISTED),
        ([E.FOUND, E.REQUESTED], S.REQUESTED),
        ([E.FOUND, E.REQUESTED, E.FOUND], S.REQUESTED),
        ([E.FOUND, E.REQUESTED, E.REQUESTED], S.REQUESTED),
        ([E.FOUND, E.REQUESTED, E.NOT_FOUND], S.REMOVED),
        ([E.FOUND, E.NOT_FOUND], S.REMOVED),
        ([E.FOUND, E.REQUESTED, E.NOT_FOUND, E.NOT_FOUND], S.REMOVED),
        ([E.FOUND, E.REQUESTED, E.NOT_FOUND, E.FOUND], S.LISTED_AGAIN),
        ([E.FOUND, E.REQUESTED, E.NOT_FOUND, E.FOUND, E.FOUND], S.LISTED_AGAIN),
        ([E.FOUND, E.REQUESTED, E.NOT_FOUND, E.FOUND, E.REQUESTED], S.REQUESTED),
        ([E.FOUND, E.REQUESTED, E.NOT_FOUND, E.FOUND, E.NOT_FOUND], S.REMOVED),
    ],
)
def test_events_lead_to_the_expected_state(events, expected):
    assert state_after(events) is expected


@pytest.mark.parametrize(
    ("before", "expected_after_not_found"),
    [
        ([], S.NO_RECORD),
        ([E.FOUND], S.REMOVED),
        ([E.FOUND, E.REQUESTED], S.REMOVED),
    ],
    ids=["before-any-search", "while-listed", "while-requested"],
)
@pytest.mark.parametrize("pause", [E.BLOCKED, E.FAILED])
def test_a_pause_resumes_from_the_state_before_it(
    before, expected_after_not_found, pause
):
    steps = replay([*before, pause, E.NOT_FOUND])

    assert steps[-2].state is (S.ACTION_REQUIRED if pause is E.BLOCKED else S.FAILED)
    assert steps[-1].state is expected_after_not_found


def test_a_second_pause_keeps_the_first_resume_point():
    steps = replay([E.FOUND, E.BLOCKED, E.FAILED, E.BLOCKED, E.REQUESTED])

    assert [step.state for step in steps] == [
        S.LISTED,
        S.ACTION_REQUIRED,
        S.FAILED,
        S.ACTION_REQUIRED,
        S.REQUESTED,
    ]


@pytest.mark.parametrize(
    "events",
    [
        [E.REQUESTED],
        [E.NOT_FOUND, E.REQUESTED],
        [E.FOUND, E.NOT_FOUND, E.REQUESTED],
        [E.BLOCKED, E.REQUESTED],
    ],
    ids=[
        "before-any-search",
        "no-record",
        "already-removed",
        "blocked-before-any-search",
    ],
)
def test_a_request_without_a_listing_is_invalid(events):
    with pytest.raises(InvalidTransition, match="requested"):
        replay(events)


@pytest.mark.parametrize("state", SETTLED)
@pytest.mark.parametrize("event", [E.FOUND, E.NOT_FOUND])
def test_every_search_result_is_decided_from_every_settled_state(state, event):
    assert (state, event) in TRANSITIONS


def test_only_not_found_leads_to_removed():
    assert {
        event for (_, event), state in TRANSITIONS.items() if state is S.REMOVED
    } == {E.NOT_FOUND}
