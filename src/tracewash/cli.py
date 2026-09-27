import mimetypes
from datetime import datetime
from importlib import metadata
from pathlib import Path
from typing import Annotated

import typer

from tracewash import definitions, drop, paths, profile, prompts
from tracewash import evidence as evidence_store
from tracewash.states import Event, InvalidTransition, State
from tracewash.tracker import Tracker
from tracewash.vault import HEADER, Vault, VaultError

# Locals can hold profile values, so tracebacks must never print them.
app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)
brokers_app = typer.Typer(no_args_is_help=True, help="Broker definitions.")
app.add_typer(brokers_app, name="brokers")
profile_app = typer.Typer(no_args_is_help=True, help="Your profile, kept in the vault.")
app.add_typer(profile_app, name="profile")

# Brokers that need the owner come first, and the untouched ones last.
STATUS_ORDER = [
    State.LISTED_AGAIN,
    State.ACTION_REQUIRED,
    State.FAILED,
    State.LISTED,
    State.REQUESTED,
    State.REMOVED,
    State.NO_RECORD,
    State.NOT_CHECKED,
]


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"tracewash {metadata.version('tracewash')}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_print_version,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """Opt out of people-search sites and prove each removal."""


def _brokers() -> list[definitions.Broker]:
    try:
        return definitions.load_brokers()
    except definitions.DefinitionError as error:
        typer.echo(
            f"{error}\nRun tracewash brokers check to see every problem.", err=True
        )
        raise typer.Exit(1) from None


@app.command()
def status() -> None:
    """Show every broker grouped by its state."""
    brokers = _brokers()
    registry = drop.load_registry()
    covered = sum(1 for broker in brokers if drop.covering_entry(broker, registry))
    with Tracker(paths.tracker_path()) as tracker:
        states = tracker.states()
    grouped: dict[State, list[str]] = {}
    for broker in brokers:
        grouped.setdefault(states.get(broker.id, State.NOT_CHECKED), []).append(
            broker.id
        )
    lines = [f"{'brokers':<16} {len(brokers):>2} tracked, {covered} covered by DROP"]
    for state in STATUS_ORDER:
        ids = grouped.get(state, [])
        if ids:
            names = "" if state is State.NOT_CHECKED else ", ".join(ids)
            lines.append(f"{state:<16} {len(ids):>2} {names}".rstrip())
    typer.echo("\n".join(lines))


def _table(rows: list[tuple[str, ...]]) -> str:
    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    return "\n".join(
        "  ".join(
            cell.ljust(width) for cell, width in zip(row, widths, strict=True)
        ).rstrip()
        for row in rows
    )


@brokers_app.command("list")
def list_brokers() -> None:
    """Show every broker with its opt-out method and whether DROP covers it."""
    brokers = _brokers()
    registry = drop.load_registry()
    rows = [("broker", "name", "opt-out", "drop")]
    rows += [
        (
            broker.id,
            broker.name,
            broker.optout.method.value,
            "yes" if drop.covering_entry(broker, registry) else "no",
        )
        for broker in brokers
    ]
    typer.echo(_table(rows))


@brokers_app.command()
def check(
    directory: Annotated[
        Path | None,
        typer.Argument(
            exists=True,
            file_okay=False,
            help="A folder of definitions. Defaults to the ones tracewash ships.",
        ),
    ] = None,
) -> None:
    """Validate every broker definition."""
    paths = definitions.definition_paths(directory)
    invalid = 0
    for path in paths:
        try:
            definitions.load_broker(path)
        except definitions.DefinitionError as error:
            invalid += 1
            typer.echo(error, err=True)
    noun = "definition" if len(paths) == 1 else "definitions"
    verdict = f"{invalid} invalid" if invalid else "all valid"
    typer.echo(f"{len(paths)} {noun} checked, {verdict}")
    if invalid:
        raise typer.Exit(1)


def _fail(message: str) -> typer.Exit:
    typer.echo(f"tracewash: {message}", err=True)
    return typer.Exit(1)


def _unlock() -> Vault:
    passphrase = typer.prompt("Passphrase", hide_input=True)
    try:
        return Vault.unlock(paths.vault_dir(), passphrase)
    except VaultError as error:
        raise _fail(str(error)) from None


@app.command()
def init() -> None:
    """Create the vault and fill in your profile."""
    location = paths.vault_dir()
    if (location / HEADER).exists():
        raise _fail(f"a vault already exists at {location}")
    typer.echo(
        f"This creates your vault in {location}.\n"
        "Choose a passphrase you will remember. If it is lost, the vault can't be recovered."
    )
    passphrase = prompts.new_passphrase()
    details = prompts.ask_profile()
    vault = Vault.create(location, passphrase)
    profile.save(vault, details)
    typer.echo(f"Vault created. It holds {profile.summary(details)}.")


@profile_app.command("show")
def profile_show() -> None:
    """Show what the profile holds, as counts."""
    typer.echo(f"Your profile holds {profile.summary(profile.load(_unlock()))}.")


@profile_app.command("edit")
def profile_edit() -> None:
    """Change the profile. Press Enter to keep a value."""
    vault = _unlock()
    details = prompts.ask_profile(profile.load(vault))
    profile.save(vault, details)
    typer.echo(f"Profile saved. It holds {profile.summary(details)}.")


@app.command()
def passphrase() -> None:
    """Change the vault's passphrase."""
    vault = _unlock()
    vault.change_passphrase(prompts.new_passphrase("New passphrase"))
    typer.echo("Passphrase changed.")


def _known_broker(broker: str) -> None:
    if broker not in {known.id for known in _brokers()}:
        raise _fail(f"there is no broker called {broker}. See tracewash brokers list.")


def _local_time(at: datetime) -> str:
    return at.astimezone().strftime("%Y.%m.%d %H:%M")


@app.command()
def track(
    broker: Annotated[str, typer.Argument(help="The broker's id, such as spokeo.")],
    event: Annotated[Event, typer.Argument(help="What you saw or did.")],
    evidence: Annotated[
        Path | None,
        typer.Option(help="A screenshot or saved page that shows it."),
    ] = None,
) -> None:
    """Record a search you ran or a request you sent by hand."""
    _known_broker(broker)
    # The file's name can hold a name of its own, so it is never echoed back.
    if evidence is not None and not evidence.is_file():
        raise _fail("the evidence file doesn't exist")
    with Tracker(paths.tracker_path()) as tracker:
        # Checked before the passphrase, so a refused step stores no evidence.
        try:
            tracker.check(broker, event, with_evidence=evidence is not None)
        except InvalidTransition as error:
            raise _fail(str(error)) from None
        evidence_id = None
        if evidence is not None:
            media_type = (
                mimetypes.guess_type(evidence.name)[0] or "application/octet-stream"
            )
            stored = evidence_store.add(_unlock(), evidence.read_bytes(), media_type)
            evidence_id = stored.id
        entry = tracker.record(broker, event, evidence_id)
    proof = f", evidence {evidence_id[:8]}" if evidence_id else ""
    typer.echo(f"{broker}: {entry.state}{proof}")


@app.command()
def timeline(
    broker: Annotated[str, typer.Argument(help="The broker's id, such as spokeo.")],
) -> None:
    """Show every step recorded for a broker."""
    _known_broker(broker)
    with Tracker(paths.tracker_path()) as tracker:
        entries = tracker.timeline(broker)
    if not entries:
        typer.echo(f"{broker}: not checked yet")
        return
    for entry in entries:
        proof = f"evidence {entry.evidence[:8]}" if entry.evidence else ""
        typer.echo(
            f"{_local_time(entry.at)}  {entry.event:<10} {entry.state:<16} {proof}".rstrip()
        )
