from importlib import metadata
from typing import Annotated

import typer

# Locals can hold profile values, so tracebacks must never print them.
app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)

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
