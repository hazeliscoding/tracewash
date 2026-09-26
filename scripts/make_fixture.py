"""Turn a saved broker page into a fixture that holds only fake data.

Save the page in your browser as "Webpage, Complete", then run
`uv run scripts/make_fixture.py <broker> listing|no-results <saved page>`.
Your real details come from .tracewash/fixture-values.yaml.
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import soupsieve
import yaml
from bs4 import (
    BeautifulSoup,
    CData,
    Comment,
    Declaration,
    Doctype,
    ProcessingInstruction,
    Tag,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "brokers"
FAKE_PROFILE_PATH = ROOT / "tests" / "fixtures" / "fake-profile.yaml"
VALUES_PATH = ROOT / ".tracewash" / "fixture-values.yaml"
EXAMPLE_VALUES = "scripts/fixture-values.example.yaml"
MARKER = "Cleaned by scripts/make_fixture.py. Every value in this page is fake."
KINDS = ("listing", "no-results")

# Each field of the values file and the fake profile field that replaces it.
FIELDS = {
    "first_name": "first_name",
    "middle_name": None,
    "last_name": "last_name",
    "other_names": "full_name",
    "city": "city",
    "state": "state",
    "state_name": "state_name",
    "age": "age",
    "birth_year": "birth_year",
    "phones": "phone",
    "emails": "email",
    "streets": "street",
}
DROPPED_TAGS = [
    "script",
    "style",
    "noscript",
    "iframe",
    "svg",
    "template",
    "link",
    "meta",
    "base",
    "object",
    "embed",
    "canvas",
    "video",
    "audio",
    "source",
    "track",
]
# Enough for selectors to match. Any other attribute can carry personal data.
KEPT_ATTRIBUTES = {
    "class",
    "id",
    "role",
    "itemprop",
    "itemscope",
    "itemtype",
    "data-testid",
    "data-test",
    "data-qa",
    "data-cy",
}
FILLER = "text"

# Long digit runs are record IDs, which point back to the real listing.
_RECORD_ID = re.compile(r"\d{4,}")
_PHONE = re.compile(
    r"(?<!\d)(?:\+?1[\s.-]*)?\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}(?!\d)"
    r"|(?<!\d)\d{3}[\s.-]\d{4}(?!\d)"
)
_FAKE_PHONE = re.compile(r"555[\s.-]*01\d\d$")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_NOT_PUNCTUATION = re.compile(r"[^\s,.;:()/-]")


class CleaningError(Exception):
    pass


@dataclass(frozen=True)
class Rule:
    field: str
    pattern: str
    length: int


def _pattern(field: str, value: str) -> str:
    if field == "phones":
        digits = re.sub(r"\D", "", value).removeprefix("1")
        area, local = (digits[:-7], digits[-7:]) if len(digits) > 7 else ("", digits)
        # Brokers write the same number as (206) 555-0188, 206.555.0188 or
        # 555-0188, so match the digits with any separators.
        prefix = rf"(?:(?:\+?1[\s.-]*)?\(?{area}\)?[\s.-]*)?" if area else ""
        return rf"(?:(?<!\d){prefix}{local[:3]}[\s.-]*{local[3:]}(?!\d))"
    if field == "emails":
        return rf"(?i:{re.escape(value)})"
    if field in ("age", "birth_year"):
        return rf"(?:(?<!\d){re.escape(value)}(?!\d))"
    words = r"\s+".join(map(re.escape, value.split()))
    # A state abbreviation is matched case-sensitively, or "wa" would match
    # inside ordinary text.
    flags = "" if field == "state" else "i"
    return rf"(?{flags}:(?<!\w){words}(?!\w))"


def load_values(path: Path) -> list[Rule]:
    if not path.exists():
        raise CleaningError(
            f"{path} doesn't exist. Copy {EXAMPLE_VALUES} there and fill in your details."
        )
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise CleaningError(f"{path.name} must map fields to values")
    unknown = sorted(set(data) - set(FIELDS))
    if unknown:
        raise CleaningError(
            f"{path.name} has unknown fields: {', '.join(unknown)}. "
            f"Use {', '.join(FIELDS)}."
        )
    if not (data.get("first_name") and data.get("last_name")):
        raise CleaningError(f"{path.name} needs at least first_name and last_name")
    rules = []
    for field, value in data.items():
        for item in value if isinstance(value, list) else [value]:
            text = "" if item is None else str(item).strip()
            if text:
                rules.append(Rule(field, _pattern(field, text), len(text)))
    return sorted(rules, key=lambda rule: rule.length, reverse=True)


def load_fake_profile() -> dict[str, str]:
    data = yaml.safe_load(FAKE_PROFILE_PATH.read_text(encoding="utf-8"))
    profile = {field: str(value) for field, value in data.items()}
    profile["full_name"] = f"{profile['first_name']} {profile['last_name']}"
    return profile


def _hits(card: Tag, rules: list[Rule]) -> int:
    text = card.get_text(" ")
    return len({rule.field for rule in rules if re.search(rule.pattern, text)})


def _signature(tag: Tag) -> tuple[str, tuple[str, ...]]:
    return tag.name, tuple(sorted(tag.get("class") or ()))


def _repeated_ancestor(element: Tag) -> tuple[Tag, list[Tag]] | None:
    # A search result is the nearest ancestor that repeats among its siblings:
    # the cards in a result list share a tag and classes.
    while element.parent is not None and element.name not in ("html", "body"):
        siblings = [
            sibling
            for sibling in element.parent.find_all(recursive=False)
            if _signature(sibling) == _signature(element)
        ]
        if len(siblings) > 1:
            return element, siblings
        element = element.parent
    return None


def _keep_one_card(soup: BeautifulSoup, rules: list[Rule], selector: str | None) -> Tag:
    if selector:
        try:
            results = soup.select(selector)
        except soupsieve.SelectorSyntaxError as error:
            raise CleaningError(
                f"--card is not a valid CSS selector: {error}"
            ) from None
        groups = [(card, results) for card in results]
    else:
        last_names = [rule.pattern for rule in rules if rule.field == "last_name"]
        nodes = soup.find_all(
            string=lambda text: any(re.search(pattern, text) for pattern in last_names)
        )
        groups = [found for node in nodes if (found := _repeated_ancestor(node.parent))]
    if not groups:
        raise CleaningError(
            "couldn't find a repeated search result with your last name. "
            "Pass --card with a CSS selector that matches each result."
        )
    card, siblings = max(groups, key=lambda group: _hits(group[0], rules))
    if not _hits(card, rules):
        raise CleaningError("none of the results matched your details")
    for sibling in siblings:
        if sibling is not card:
            sibling.decompose()
    return card


def _phrase(phrase: str) -> str:
    return r"\s+".join(map(re.escape, phrase.split()))


def _rewrite(
    text: str, pattern: re.Pattern, rules: list[Rule], fake: dict
) -> str | None:
    # Keep only the kept phrases, the swapped values and the punctuation between
    # them. Any other word could be a relative's or a neighbor's name.
    pieces, end = [], 0
    for match in pattern.finditer(text):
        pieces.append(_NOT_PUNCTUATION.sub("", text[end : match.start()]))
        if match.lastgroup == "keep":
            pieces.append(match.group())
        else:
            target = FIELDS[rules[int(match.lastgroup[1:])].field]
            replacement = fake[target] if target else ""
            pieces.append(
                replacement.upper() if match.group().isupper() else replacement
            )
        end = match.end()
    if not end:
        return None
    pieces.append(_NOT_PUNCTUATION.sub("", text[end:]))
    return " ".join("".join(pieces).split())


def _kept_attributes(tag: Tag) -> dict:
    kept = {}
    for name, value in tag.attrs.items():
        if name == "href":
            kept["href"] = "#"
        elif name in KEPT_ATTRIBUTES:
            if isinstance(value, list):
                tokens = [token for token in value if not _RECORD_ID.search(token)]
                if tokens:
                    kept[name] = tokens
            elif not _RECORD_ID.search(value):
                kept[name] = value
    return kept


def find_leftovers(html: str, rules: list[Rule] = ()) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    strings = [str(node) for node in soup.find_all(string=True)]
    for tag in soup.find_all(True):
        for value in tag.attrs.values():
            strings.append(" ".join(value) if isinstance(value, list) else str(value))
    text = "\n".join(strings)
    problems = [
        f"your {field} is still in the page"
        for field in dict.fromkeys(
            rule.field for rule in rules if re.search(rule.pattern, text)
        )
    ]
    if any(not _FAKE_PHONE.search(match.group()) for match in _PHONE.finditer(text)):
        problems.append("a phone number outside 555-01xx is in the page")
    if any(
        not match.group().lower().endswith("@example.com")
        for match in _EMAIL.finditer(text)
    ):
        problems.append("an email address outside example.com is in the page")
    return problems


def clean(
    html: str,
    rules: list[Rule],
    kind: str,
    keep: list[str] = (),
    card: str | None = None,
) -> str:
    fake = load_fake_profile()
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(DROPPED_TAGS):
        tag.decompose()
    hidden = (Comment, CData, ProcessingInstruction, Declaration)
    for node in soup.find_all(string=lambda text: isinstance(text, hidden)):
        node.extract()
    kept_card = _keep_one_card(soup, rules, card) if kind == "listing" else None
    kept = [f"(?P<keep>(?i:{'|'.join(map(_phrase, keep))}))"] if keep else []
    values = [f"(?P<r{index}>{rule.pattern})" for index, rule in enumerate(rules)]
    in_card = re.compile("|".join(kept + values))
    elsewhere = re.compile(kept[0]) if kept else None
    for node in soup.find_all(string=True):
        if isinstance(node, Doctype) or not node.strip():
            continue
        inside = kept_card is not None and any(
            parent is kept_card for parent in node.parents
        )
        pattern = in_card if inside else elsewhere
        rewritten = _rewrite(str(node), pattern, rules, fake) if pattern else None
        node.replace_with(rewritten or FILLER)
    for tag in soup.find_all(True):
        tag.attrs = _kept_attributes(tag)
    fixture = f"<!-- {MARKER} -->\n{soup.prettify()}"
    problems = find_leftovers(fixture, rules)
    if problems:
        raise CleaningError("refusing to write the fixture: " + "; ".join(problems))
    return fixture


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("broker", help="the broker's id, such as spokeo")
    parser.add_argument("kind", choices=KINDS)
    parser.add_argument("page", type=Path, help="the page you saved")
    parser.add_argument(
        "--values",
        type=Path,
        default=VALUES_PATH,
        help="your real details (default: .tracewash/fixture-values.yaml)",
    )
    parser.add_argument(
        "--keep",
        action="append",
        default=[],
        metavar="PHRASE",
        help="keep text that contains this phrase, such as a no-results message",
    )
    parser.add_argument(
        "--card",
        metavar="SELECTOR",
        help="a CSS selector for each search result, when yours isn't found",
    )
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", args.broker):
        parser.error("the broker id is lowercase letters, digits and hyphens")
    try:
        rules = load_values(args.values)
        page = args.page.read_text(encoding="utf-8", errors="replace")
        fixture = clean(page, rules, args.kind, args.keep, args.card)
    except CleaningError as error:
        sys.exit(f"make_fixture: {error}")
    out = FIXTURES_DIR / args.broker / f"{args.kind}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(fixture, encoding="utf-8", newline="\n")
    print(f"wrote {out}. Review the diff before you commit it.")


if __name__ == "__main__":
    main()
