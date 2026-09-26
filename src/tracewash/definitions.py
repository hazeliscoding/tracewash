import string
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Self
from urllib.parse import urlsplit

import soupsieve
import yaml
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

BROKERS_DIR = Path(__file__).parent / "brokers"


class DefinitionError(Exception):
    pass


class FieldName(StrEnum):
    FIRST_NAME = "first_name"
    MIDDLE_NAME = "middle_name"
    LAST_NAME = "last_name"
    CITY = "city"
    STATE = "state"
    STATE_NAME = "state_name"
    ZIP = "zip"
    EMAIL = "email"
    PHONE = "phone"
    BIRTH_YEAR = "birth_year"
    LISTING_URL = "listing_url"


class OptOutMethod(StrEnum):
    FORM = "form"
    EMAIL = "email"
    MANUAL = "manual"


class Confirmation(StrEnum):
    NONE = "none"
    EMAIL = "email"
    PHONE = "phone"


# Brokers spell names differently in their URLs (Jane-Doe, jane-doe), so a
# placeholder can take transforms: {first_name:slug,lower}.
TRANSFORMS = {"slug", "lower"}


def _check_https(value: str) -> str:
    if urlsplit(value).scheme != "https":
        raise ValueError("must be an https:// URL")
    return value


def _check_search_url(value: str) -> str:
    for _, field, spec, conversion in string.Formatter().parse(value):
        if field is None:
            continue
        if field not in FieldName:
            raise ValueError(f"unknown field {field!r} in the URL")
        if field == FieldName.LISTING_URL:
            raise ValueError(
                "listing_url comes from the search, so its URL can't use it"
            )
        if conversion:
            raise ValueError(f"{{{field}!{conversion}}} is not supported")
        for transform in filter(None, spec.split(",")):
            if transform not in TRANSFORMS:
                raise ValueError(
                    f"unknown transform {transform!r}; use {', '.join(sorted(TRANSFORMS))}"
                )
    return value


def _check_selector(value: str) -> str:
    try:
        soupsieve.compile(value)
    except soupsieve.SelectorSyntaxError as error:
        # soupsieve appends the selector and a caret on extra lines.
        reason = str(error).splitlines()[0]
        raise ValueError(f"not a valid CSS selector: {reason}") from None
    return value


HttpsUrl = Annotated[str, AfterValidator(_check_https)]
SearchUrl = Annotated[HttpsUrl, AfterValidator(_check_search_url)]
Selector = Annotated[str, AfterValidator(_check_selector)]
Domain = Annotated[str, Field(pattern=r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")]
EmailAddress = Annotated[str, Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Search(Model):
    url: SearchUrl
    result: Selector
    name: Selector
    age: Selector | None = None
    location: Selector | None = None
    link: Selector | None = None
    no_results: Selector


class OptOut(Model):
    method: OptOutMethod
    url: HttpsUrl | None = None
    email: EmailAddress | None = None
    needs: list[FieldName] = []
    confirm: Confirmation = Confirmation.NONE

    @model_validator(mode="after")
    def _has_somewhere_to_go(self) -> Self:
        if self.method is OptOutMethod.EMAIL:
            if not self.email:
                raise ValueError("an email opt-out needs an email address")
        elif not self.url:
            raise ValueError(f"a {self.method} opt-out needs a url")
        return self


class Broker(Model):
    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    name: str
    operator: str | None = None
    domains: list[Domain] = Field(min_length=1)
    search: Search
    optout: OptOut
    recheck_days: int = Field(default=30, ge=1)
    request_delay_seconds: int = Field(default=10, ge=0)

    # tracewash talks only to broker sites, so every URL a definition gives it
    # must sit on one of that broker's declared domains.
    @model_validator(mode="after")
    def _urls_stay_on_broker_domains(self) -> Self:
        for url in (self.search.url, self.optout.url):
            if url is None:
                continue
            host = urlsplit(url).hostname or ""
            if not any(host == d or host.endswith(f".{d}") for d in self.domains):
                raise ValueError(f"{host} is not one of the broker's domains")
        return self


def _describe(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in detail['loc']) or 'definition'}: {detail['msg']}"
        for detail in error.errors()
    )


def load_broker(path: Path) -> Broker:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise DefinitionError(f"{path.name}: not valid YAML: {error}") from None
    if not isinstance(data, dict):
        raise DefinitionError(f"{path.name}: must be a mapping of keys to values")
    try:
        broker = Broker.model_validate(data)
    except ValidationError as error:
        raise DefinitionError(f"{path.name}: {_describe(error)}") from None
    if broker.id != path.stem:
        raise DefinitionError(
            f"{path.name}: id {broker.id!r} must match the file name {path.stem!r}"
        )
    return broker


def load_brokers(directory: Path = BROKERS_DIR) -> list[Broker]:
    return [load_broker(path) for path in sorted(directory.glob("*.yaml"))]
