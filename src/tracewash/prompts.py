import re
from datetime import UTC, datetime

import typer

from tracewash.profile import Address, Profile

MIN_PASSPHRASE = 12

# Prompts never show a stored value. With one on file, Enter keeps it and a
# dash clears an optional one.


def new_passphrase(label: str = "Passphrase") -> str:
    # Click hides the reason when hidden input fails validation, so the loop
    # is written out to say what's wrong.
    while True:
        value = typer.prompt(label, hide_input=True)
        if len(value) < MIN_PASSPHRASE:
            typer.echo(f"Use at least {MIN_PASSPHRASE} characters.")
        elif typer.prompt("Repeat it", hide_input=True) == value:
            return value
        else:
            typer.echo("The two entries don't match.")


def _text(label: str, current: str = "", required: bool = False) -> str:
    if current:
        hint = "Enter keeps it" if required else "Enter keeps it, - clears it"
        answer = typer.prompt(f"{label} ({hint})", default="", show_default=False)
        answer = answer.strip()
        if not answer:
            return current
        return "" if answer == "-" and not required else answer
    if required:
        return typer.prompt(label).strip()
    return typer.prompt(f"{label} (optional)", default="", show_default=False).strip()


def _list(label: str, current: list[str]) -> list[str]:
    text = _text(f"{label}, separated by commas", ", ".join(current))
    return [item.strip() for item in text.split(",") if item.strip()]


def _state(value: str) -> str:
    value = value.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", value):
        raise typer.BadParameter("use the two-letter code, such as OR")
    return value


def _birth_year(current: int | None) -> int | None:
    def checked(value: str) -> str:
        value = value.strip()
        if value not in ("", "-") and not (
            value.isdigit() and 1900 <= int(value) <= datetime.now(UTC).year
        ):
            raise typer.BadParameter("use a four-digit year")
        return value

    if current:
        label = "Birth year (Enter keeps it, - clears it)"
    else:
        label = "Birth year (optional)"
    answer = typer.prompt(label, default="", show_default=False, value_proc=checked)
    if not answer:
        return current
    return None if answer == "-" else int(answer)


def _address(when: str) -> Address:
    return Address(
        street=_text(f"{when} street address"),
        city=_text(f"{when} city", required=True),
        state=typer.prompt(f"{when} state, two letters", value_proc=_state),
        zip=_text(f"{when} ZIP code"),
    )


def _addresses(current: list[Address]) -> list[Address]:
    if current and not typer.confirm(
        f"Replace your {len(current)} stored address(es)?", default=False
    ):
        return current
    addresses = [_address("Current")]
    while typer.confirm("Add a past address?", default=False):
        addresses.append(_address("Past"))
    return addresses


def ask_profile(current: Profile | None = None) -> Profile:
    return Profile(
        first_name=_text("First name", current.first_name if current else "", True),
        middle_name=_text("Middle name", current.middle_name if current else ""),
        last_name=_text("Last name", current.last_name if current else "", True),
        other_names=_list(
            "Other names you have used", current.other_names if current else []
        ),
        emails=_list("Emails", current.emails if current else []),
        phones=_list("Phone numbers", current.phones if current else []),
        addresses=_addresses(current.addresses if current else []),
        birth_year=_birth_year(current.birth_year if current else None),
    )
