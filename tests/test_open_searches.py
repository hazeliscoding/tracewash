import webbrowser

import open_searches
import yaml
from definition_samples import VALID, changed, write_definition
from test_make_fixture import REAL

from tracewash import definitions


def test_it_opens_your_search_and_the_fake_one(tmp_path, monkeypatch, capsys):
    brokers = tmp_path / "brokers"
    brokers.mkdir()
    monkeypatch.setattr(definitions, "BROKERS_DIR", brokers)
    write_definition(brokers, VALID)
    values = tmp_path / "fixture-values.yaml"
    values.write_text(yaml.safe_dump(REAL), encoding="utf-8")
    opened = []
    monkeypatch.setattr(webbrowser, "open_new_tab", opened.append)

    open_searches.main(["--values", str(values)])

    assert opened == [
        "https://www.peoplesearch.example/Delphine-Arkwright/WA",
        "https://www.peoplesearch.example/Marisol-Quillfeather/OR",
    ]
    out = capsys.readouterr().out
    assert "peoplesearch-listing.html" in out
    assert "peoplesearch-no-results.html" in out
    assert "Delphine" not in out


def test_it_says_when_you_have_to_fill_in_the_search_yourself(
    tmp_path, monkeypatch, capsys
):
    brokers = tmp_path / "brokers"
    brokers.mkdir()
    monkeypatch.setattr(definitions, "BROKERS_DIR", brokers)
    write_definition(
        brokers, changed("search.url", "https://www.peoplesearch.example/find")
    )
    values = tmp_path / "fixture-values.yaml"
    values.write_text(yaml.safe_dump(REAL), encoding="utf-8")
    monkeypatch.setattr(webbrowser, "open_new_tab", lambda url: None)

    open_searches.main(["--values", str(values)])

    out = capsys.readouterr().out
    assert (
        "peoplesearch: search for yourself there, then save as peoplesearch-listing.html"
        in out
    )
    assert "search for Marisol Quillfeather there" not in out
    assert "search for the fake name there" in out
