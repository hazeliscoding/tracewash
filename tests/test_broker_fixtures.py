from pathlib import Path

import pytest
from canary_guard import FAKE_PROFILE
from make_fixture import MARKER, find_leftovers

from tracewash.definitions import load_brokers
from tracewash.search import read_search_page

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "brokers"
BROKERS = load_brokers()
FIXTURES = sorted(FIXTURES_DIR.glob("*/*.html"))


def read_fixture(broker, kind):
    html = (FIXTURES_DIR / broker.id / f"{kind}.html").read_text(encoding="utf-8")
    return read_search_page(html, broker.search)


@pytest.mark.parametrize("broker", BROKERS, ids=lambda broker: broker.id)
def test_the_listing_fixture_shows_the_fake_profile(broker):
    listing = read_fixture(broker, "listing")

    assert listing.results
    assert not listing.no_results
    first = listing.results[0]
    for part in (FAKE_PROFILE["first_name"], FAKE_PROFILE["last_name"]):
        assert part.casefold() in first.name.casefold()
    for field in ("age", "location", "link"):
        if getattr(broker.search, field):
            assert getattr(first, field), f"{field} selector found nothing"


@pytest.mark.parametrize("broker", BROKERS, ids=lambda broker: broker.id)
def test_the_no_results_fixture_shows_no_results(broker):
    empty = read_fixture(broker, "no-results")

    assert empty.no_results
    assert empty.results == []


@pytest.mark.parametrize(
    "path", FIXTURES, ids=lambda path: f"{path.parent.name}/{path.name}"
)
def test_every_fixture_came_from_the_cleaner(path):
    html = path.read_text(encoding="utf-8")

    assert html.startswith(f"<!-- {MARKER} -->")
    assert find_leftovers(html) == []


def test_every_fixture_folder_belongs_to_a_broker():
    folders = {path.parent.name for path in FIXTURES}

    assert folders <= {broker.id for broker in BROKERS}
