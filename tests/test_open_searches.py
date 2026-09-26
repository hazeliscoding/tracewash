import webbrowser

import open_searches
import yaml
from definition_samples import VALID, write_definition
from test_make_fixture import REAL

from tracewash import definitions


def test_it_opens_your_search_and_the_fake_one(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(definitions, "BROKERS_DIR", tmp_path)
    write_definition(tmp_path, VALID)
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
