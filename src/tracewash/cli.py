from importlib import metadata
from pathlib import Path
from typing import Annotated

import typer

from tracewash import definitions, drop, paths, profile, prompts
from tracewash.vault import HEADER, Vault, VaultError

# Locals can hold profile values, so tracebacks must never print them.
app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)
brokers_app = typer.Typer(no_args_is_help=True, help="Broker definitions.")
app.add_typer(brokers_app, name="brokers")
profile_app = typer.Typer(no_args_is_help=True, help="Your profile, kept in the vault.")
app.add_typer(profile_app, name="profile")

# Canned until the tracker exists (M2). The first line keeps it from passing
# for real results.
SAMPLE_STATUS = """\
sample output: tracewash does not track brokers yet

brokers         15 tracked, 4 covered by DROP
removed          6 proven by rescan
requested        5 next recheck 2026.10.09
action required  2 fastpeoplesearch: captcha, spokeo: confirm email
listed again     1 whitepages
"""


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


@app.command()
def status() -> None:
    """Show brokers by state, next rechecks and required actions."""
    typer.echo(SAMPLE_STATUS, nl=False)


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
    try:
        brokers = definitions.load_brokers()
    except definitions.DefinitionError as error:
        typer.echo(
            f"{error}\nRun tracewash brokers check to see every problem.", err=True
        )
        raise typer.Exit(1) from None
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
