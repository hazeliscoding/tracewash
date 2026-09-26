import pytest
from definition_samples import VALID

from tracewash.definitions import Broker
from tracewash.search import read_search_page, search_url

SEARCH = Broker(**VALID).search

LISTING = """<html><body>
  <div class="result">
    <a class="profile" href="/p/1"><span class="name">Marisol Quillfeather</span></a>
    <span class="age">41</span>
    <span class="location">Quillmoor, OR</span>
  </div>
  <div class="result"><span class="name">  </span></div>
  <div class="result"><span class="name">Marisol Q Quillfeather</span></div>
</body></html>"""


def test_it_reads_each_result_with_its_fields():
    page = read_search_page(LISTING, SEARCH)

    first, second = page.results
    assert (first.name, first.age, first.location, first.link) == (
        "Marisol Quillfeather",
        "41",
        "Quillmoor, OR",
        "/p/1",
    )
    assert (second.name, second.age, second.location, second.link) == (
        "Marisol Q Quillfeather",
        None,
        None,
        None,
    )
    assert not page.no_results


def test_it_spots_the_no_results_page():
    page = read_search_page('<p class="no-results">Nothing found</p>', SEARCH)

    assert page.results == []
    assert page.no_results


def test_search_url_fills_in_and_transforms_the_values():
    url = search_url(
        SEARCH, {"first_name": "Mary Ann", "last_name": "O'Neil", "state": "OR"}
    )

    assert url == "https://www.peoplesearch.example/Mary-Ann-ONeil/OR"


def test_search_url_lowercases_and_escapes():
    search = SEARCH.model_copy(
        update={
            "url": "https://www.peoplesearch.example/s?q={first_name:slug,lower}&c={city}"
        }
    )

    url = search_url(search, {"first_name": "Mary Ann", "city": "Salt Lake City"})

    assert url == "https://www.peoplesearch.example/s?q=mary-ann&c=Salt%20Lake%20City"


def test_search_url_names_a_missing_value():
    with pytest.raises(ValueError, match="state"):
        search_url(SEARCH, {"first_name": "Marisol", "last_name": "Quillfeather"})
