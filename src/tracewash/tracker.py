import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

from tracewash.states import Event, InvalidTransition, State, replay

# Only IDs, events and times: no column can hold a profile value.
SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    broker TEXT NOT NULL,
    event TEXT NOT NULL,
    at TEXT NOT NULL,
    evidence TEXT
);
CREATE INDEX IF NOT EXISTS events_by_broker ON events (broker, id);
"""


class ProofRequired(InvalidTransition):
    pass


@dataclass(frozen=True)
class Entry:
    at: datetime
    event: Event
    state: State
    evidence: str | None


class Tracker:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.executescript(SCHEMA)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def close(self) -> None:
        self._db.close()

    def timeline(self, broker: str) -> list[Entry]:
        rows = self._db.execute(
            "SELECT event, at, evidence FROM events WHERE broker = ? ORDER BY id",
            (broker,),
        ).fetchall()
        # States aren't stored: replaying the events through the table is the
        # only way to get one.
        steps = replay(event for event, _, _ in rows)
        return [
            Entry(
                datetime.fromisoformat(at).astimezone(UTC),
                step.event,
                step.state,
                evidence,
            )
            for (_, at, evidence), step in zip(rows, steps, strict=True)
        ]

    def state(self, broker: str) -> State:
        timeline = self.timeline(broker)
        return timeline[-1].state if timeline else State.NOT_CHECKED

    def states(self) -> dict[str, State]:
        brokers = self._db.execute("SELECT DISTINCT broker FROM events ORDER BY broker")
        return {broker: self.state(broker) for (broker,) in brokers.fetchall()}

    def record(self, broker: str, event: Event, evidence: str | None = None) -> Entry:
        history = [entry.event for entry in self.timeline(broker)]
        state = replay([*history, event])[-1].state
        if state is State.REMOVED and evidence is None:
            raise ProofRequired(
                f"marking {broker} removed needs evidence, "
                "such as a screenshot of the search that found nothing"
            )
        at = datetime.now(UTC)
        with self._db:
            self._db.execute(
                "INSERT INTO events (broker, event, at, evidence) VALUES (?, ?, ?, ?)",
                (broker, str(event), at.isoformat(), evidence),
            )
        return Entry(at, Event(event), state, evidence)
