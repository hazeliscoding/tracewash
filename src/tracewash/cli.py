from importlib import metadata
from typing import Annotated

import typer

# Locals can hold profile values, so tracebacks must never print them.
app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


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
