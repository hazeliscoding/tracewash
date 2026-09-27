from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class State(StrEnum):
    NOT_CHECKED = "not checked"
    LISTED = "listed"
    REQUESTED = "requested"
    ACTION_REQUIRED = "action required"
    REMOVED = "removed"
    NO_RECORD = "no record"
    LISTED_AGAIN = "listed again"
    FAILED = "failed"


class Event(StrEnum):
    FOUND = "found"
    NOT_FOUND = "not-found"
    REQUESTED = "requested"
    BLOCKED = "blocked"
    FAILED = "failed"


class InvalidTransition(Exception):
    pass


S, E = State, Event

# The only way a broker's state changes. A request needs a listing to act on,
# and only a search that finds nothing leads to removed.
TRANSITIONS: dict[tuple[State, Event], State] = {
    (S.NOT_CHECKED, E.FOUND): S.LISTED,
    (S.NOT_CHECKED, E.NOT_FOUND): S.NO_RECORD,
    (S.NO_RECORD, E.FOUND): S.LISTED,
    (S.NO_RECORD, E.NOT_FOUND): S.NO_RECORD,
    (S.LISTED, E.FOUND): S.LISTED,
    (S.LISTED, E.NOT_FOUND): S.REMOVED,
    (S.LISTED, E.REQUESTED): S.REQUESTED,
    (S.REQUESTED, E.FOUND): S.REQUESTED,
    (S.REQUESTED, E.NOT_FOUND): S.REMOVED,
    (S.REQUESTED, E.REQUESTED): S.REQUESTED,
    (S.REMOVED, E.FOUND): S.LISTED_AGAIN,
    (S.REMOVED, E.NOT_FOUND): S.REMOVED,
    (S.LISTED_AGAIN, E.FOUND): S.LISTED_AGAIN,
    (S.LISTED_AGAIN, E.NOT_FOUND): S.REMOVED,
    (S.LISTED_AGAIN, E.REQUESTED): S.REQUESTED,
}

# Blocked and failed pause a broker. The next event applies to the state from
# before the pause, so a CAPTCHA before the first search can't end in removed.
PAUSES = {E.BLOCKED: S.ACTION_REQUIRED, E.FAILED: S.FAILED}


@dataclass(frozen=True)
class Step:
    event: Event
    state: State


def replay(events: Iterable[Event | str]) -> list[Step]:
    steps, settled = [], S.NOT_CHECKED
    for event in map(Event, events):
        if event in PAUSES:
            state = PAUSES[event]
        elif (settled, event) in TRANSITIONS:
            settled = state = TRANSITIONS[settled, event]
        else:
            raise InvalidTransition(f"{event} can't follow {settled}")
        steps.append(Step(event, state))
    return steps


def state_after(events: Iterable[Event | str]) -> State:
    steps = replay(events)
    return steps[-1].state if steps else S.NOT_CHECKED
