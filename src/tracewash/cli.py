from importlib import metadata
from pathlib import Path
from typing import Annotated

import typer

from tracewash import definitions

# Locals can hold profile values, so tracebacks must never print them.
app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)
brokers_app = typer.Typer(no_args_is_help=True, help="Broker definitions.")
app.add_typer(brokers_app, name="brokers")

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
    """Show every broker with its opt-out method."""
    try:
        brokers = definitions.load_brokers()
    except definitions.DefinitionError as error:
        typer.echo(
            f"{error}\nRun tracewash brokers check to see every problem.", err=True
        )
        raise typer.Exit(1) from None
    rows = [("broker", "name", "opt-out")]
    rows += [(broker.id, broker.name, broker.optout.method.value) for broker in brokers]
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
