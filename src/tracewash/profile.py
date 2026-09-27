from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tracewash.vault import Vault

PROFILE_FILE = "profile.json"


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Address(Model):
    street: str = ""
    city: str = Field(min_length=1)
    state: str = Field(pattern=r"^[A-Z]{2}$")
    zip: str = ""


class Profile(Model):
    first_name: str = Field(min_length=1)
    middle_name: str = ""
    last_name: str = Field(min_length=1)
    other_names: list[str] = []
    emails: list[str] = []
    phones: list[str] = []
    # The first address is the current one.
    addresses: list[Address] = Field(min_length=1)
    birth_year: int | None = None

    @field_validator("birth_year")
    @classmethod
    def _plausible_year(cls, year: int | None) -> int | None:
        if year is not None and not 1900 <= year <= datetime.now(UTC).year:
            raise ValueError("the birth year is out of range")
        return year


def save(vault: Vault, profile: Profile) -> None:
    vault.write(PROFILE_FILE, profile.model_dump_json().encode())


def load(vault: Vault) -> Profile:
    return Profile.model_validate_json(vault.read(PROFILE_FILE))


def _count(number: int, noun: str, plural: str | None = None) -> str:
    return f"{number} {noun if number == 1 else plural or noun + 's'}"


def summary(profile: Profile) -> str:
    # Counts only: profile values never reach the terminal or the logs.
    parts = ["your name"]
    if profile.other_names:
        parts.append(_count(len(profile.other_names), "other name"))
    parts.append(_count(len(profile.emails), "email"))
    parts.append(_count(len(profile.phones), "phone number"))
    parts.append(_count(len(profile.addresses), "address", "addresses"))
    if profile.birth_year:
        parts.append("a birth year")
    return ", ".join(parts[:-1]) + " and " + parts[-1]
