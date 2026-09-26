import re
import string
from dataclasses import dataclass
from urllib.parse import quote

from bs4 import BeautifulSoup, Tag

from tracewash.definitions import Search


@dataclass(frozen=True)
class Result:
    name: str
    age: str | None
    location: str | None
    link: str | None


@dataclass(frozen=True)
class SearchPage:
    results: list[Result]
    no_results: bool


def _text(card: Tag, selector: str | None) -> str | None:
    element = card.select_one(selector) if selector else None
    if element is None:
        return None
    return " ".join(element.stripped_strings) or None


def read_search_page(html: str, search: Search) -> SearchPage:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for card in soup.select(search.result):
        name = _text(card, search.name)
        # Ads and placeholders often reuse the result markup without a name.
        if not name:
            continue
        link = card.select_one(search.link) if search.link else None
        results.append(
            Result(
                name=name,
                age=_text(card, search.age),
                location=_text(card, search.location),
                link=link.get("href") if link else None,
            )
        )
    return SearchPage(results, soup.select_one(search.no_results) is not None)


def _transform(value: str, spec: str) -> str:
    for transform in filter(None, spec.split(",")):
        if transform == "slug":
            value = "-".join(re.sub(r"[^\w\s-]", "", value).split())
        elif transform == "lower":
            value = value.lower()
    return value


def search_url(search: Search, values: dict[str, str]) -> str:
    parts = []
    for literal, field, spec, _ in string.Formatter().parse(search.url):
        parts.append(literal)
        if field is None:
            continue
        if not values.get(field):
            raise ValueError(f"the search URL needs {field}")
        parts.append(quote(_transform(str(values[field]), spec), safe=""))
    return "".join(parts)
