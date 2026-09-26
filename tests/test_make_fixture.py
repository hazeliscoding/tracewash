import make_fixture
import pytest
import yaml
from bs4 import BeautifulSoup
from make_fixture import CleaningError, clean, find_leftovers, load_values

# A second fake person, planted as the "real" owner. Nothing about them may
# survive cleaning.
REAL = {
    "first_name": "Delphine",
    "last_name": "Arkwright",
    "city": "Brackenridge",
    "state": "WA",
    "state_name": "Washington",
    "age": 57,
    "phones": ["(206) 555-0188"],
    "emails": ["delphine.arkwright@example.net"],
    "streets": ["77 Larkspur Lane"],
}

LISTING = """<!DOCTYPE html>
<html>
<head>
  <title>Delphine Arkwright in Brackenridge, WA | People Search</title>
  <meta property="og:title" content="Delphine Arkwright">
  <script type="application/ld+json">{"name": "Delphine Arkwright", "telephone": "206-555-0188"}</script>
  <style>.card { color: teal }</style>
</head>
<body>
  <form><input name="q" value="Delphine Arkwright"></form>
  <h1>3 results for Delphine Arkwright</h1>
  <!-- record 206.555.0188 -->
  <div class="results">
    <div class="card" data-name="Delphine Arkwright" id="p-9981234">
      <a class="profile" href="/Delphine-Arkwright/WA/Brackenridge/p9981234">
        <span class="name">Delphine Arkwright</span>
      </a>
      <span class="age">Age 57</span>
      <span class="location">Resides in Brackenridge, WA</span>
      <span class="phone">(206) 555-0188</span>
      <span class="email">delphine.arkwright@example.net</span>
      <span class="street">77 Larkspur Lane</span>
      <span class="relatives">Tobias Arkwright, Wren Halloway</span>
    </div>
    <div class="card" id="p-1112223">
      <a class="profile" href="/Delphine-Arkwright/OR/Coldwater/p1112223">
        <span class="name">Delphine Arkwright</span>
      </a>
      <span class="age">Age 33</span>
      <span class="location">Coldwater, OR</span>
    </div>
    <div class="card">
      <span class="name">DELPHINE R ARKWRIGHT</span>
      <span class="location">Fennmoor, ID</span>
    </div>
  </div>
  <aside><h2>People also searched</h2><a href="/Osric-Pellham">Osric Pellham</a></aside>
</body>
</html>
"""

NO_RESULTS = """<html><body>
  <div class="no-results">No people found for Marisol Quillfeather</div>
  <p class="nearby">People near Brackenridge, WA</p>
</body></html>
"""

PLANTED = [
    "Delphine",
    "Arkwright",
    "Brackenridge",
    "Washington",
    "555-0188",
    "example.net",
    "Larkspur",
    "Tobias",
    "Halloway",
    "Osric",
    "Pellham",
    "Coldwater",
    "Fennmoor",
    "9981234",
    "1112223",
    "record",
    "teal",
]


@pytest.fixture
def values_file(tmp_path):
    path = tmp_path / "fixture-values.yaml"
    path.write_text(yaml.safe_dump(REAL), encoding="utf-8")
    return path


@pytest.fixture
def rules(values_file):
    return load_values(values_file)


def test_nothing_real_survives_a_listing_page(rules):
    fixture = clean(LISTING, rules, "listing")

    for planted in PLANTED:
        assert planted.casefold() not in fixture.casefold(), planted


def test_only_your_result_is_kept_with_the_fake_values(rules):
    page = BeautifulSoup(clean(LISTING, rules, "listing"), "html.parser")

    [card] = page.select(".card")
    assert card.select_one(".name").get_text(strip=True) == "Marisol Quillfeather"
    assert card.select_one(".age").get_text(strip=True) == "41"
    assert card.select_one(".location").get_text(strip=True) == "Quillmoor, OR"
    assert card.select_one(".phone").get_text(strip=True) == "555-0147"
    assert card.select_one("a.profile")["href"] == "#"


def test_the_fixture_starts_with_the_marker(rules):
    assert clean(LISTING, rules, "listing").startswith(
        f"<!-- {make_fixture.MARKER} -->"
    )


def test_a_no_results_page_keeps_only_the_phrases_asked_for(rules):
    fixture = clean(NO_RESULTS, rules, "no-results", keep=["No people found"])

    assert "No people found" in fixture
    assert "Quillfeather" not in fixture
    assert "Brackenridge" not in fixture


def test_a_kept_phrase_survives_next_to_your_swapped_values(rules):
    page = BeautifulSoup(
        clean(LISTING, rules, "listing", keep=["Resides in"]), "html.parser"
    )

    location = page.select_one(".card .location").get_text(strip=True)
    assert location == "Resides in Quillmoor, OR"


def test_a_card_selector_finds_your_result_when_results_look_different(rules):
    page = LISTING.replace(
        '<div class="card" id="p-1112223">',
        '<div class="card featured" id="p-1112223">',
    ).replace('<div class="card">', '<div class="card sponsored">')
    with pytest.raises(CleaningError, match="--card"):
        clean(page, rules, "listing")

    cleaned = BeautifulSoup(
        clean(page, rules, "listing", card="div.card"), "html.parser"
    )

    [card] = cleaned.select("div.card")
    assert card.select_one(".name").get_text(strip=True) == "Marisol Quillfeather"


@pytest.mark.parametrize(
    ("page", "keep", "problem"),
    [
        (LISTING, ["results for Delphine"], "first_name"),
        ("<p>Call (999) 000-1234</p>", ["Call (999) 000-1234"], "555-01xx"),
        ("<p>Write to help@example.org</p>", ["help@example.org"], "example.com"),
    ],
    ids=["your-value", "unknown-phone", "unknown-email"],
)
def test_it_refuses_when_something_real_survives(rules, page, keep, problem):
    with pytest.raises(CleaningError, match=problem):
        clean(page, rules, "no-results", keep=keep)


def test_it_refuses_a_listing_without_your_name(rules):
    with pytest.raises(CleaningError, match="--card"):
        clean("<div class='card'>Someone Else</div>", rules, "listing")


def test_find_leftovers_accepts_fake_contact_details():
    page = "<p>555-0147 marisol.quillfeather@example.com</p>"

    assert find_leftovers(page) == []


def test_a_missing_values_file_says_how_to_create_it(tmp_path):
    with pytest.raises(CleaningError, match="fixture-values.example.yaml"):
        load_values(tmp_path / "fixture-values.yaml")


def test_a_values_file_with_an_unknown_key_is_rejected(tmp_path):
    path = tmp_path / "fixture-values.yaml"
    path.write_text(yaml.safe_dump({**REAL, "phone": "555-0199"}), encoding="utf-8")

    with pytest.raises(CleaningError, match="phone"):
        load_values(path)


def test_main_writes_the_fixture(tmp_path, values_file, monkeypatch):
    monkeypatch.setattr(make_fixture, "FIXTURES_DIR", tmp_path / "fixtures")
    saved = tmp_path / "saved.html"
    saved.write_text(LISTING, encoding="utf-8")

    make_fixture.main(
        ["peoplesearch", "listing", str(saved), "--values", str(values_file)]
    )

    written = tmp_path / "fixtures" / "peoplesearch" / "listing.html"
    assert "Marisol Quillfeather" in written.read_text(encoding="utf-8")


def test_main_writes_nothing_when_it_refuses(tmp_path, values_file, monkeypatch):
    monkeypatch.setattr(make_fixture, "FIXTURES_DIR", tmp_path / "fixtures")
    saved = tmp_path / "saved.html"
    saved.write_text("<p>Call (999) 000-1234</p>", encoding="utf-8")

    with pytest.raises(SystemExit) as exit_info:
        make_fixture.main(
            ["peoplesearch", "no-results", str(saved), "--values", str(values_file)]
            + ["--keep", "Call (999) 000-1234"]
        )

    assert exit_info.value.code != 0
    assert not (tmp_path / "fixtures").exists()


def test_folder_mode_cleans_every_page_with_its_options(
    tmp_path, values_file, monkeypatch
):
    monkeypatch.setattr(make_fixture, "FIXTURES_DIR", tmp_path / "fixtures")
    options = tmp_path / "options.yaml"
    options.write_text(yaml.safe_dump({"peoplesearch": {"keep": ["No people found"]}}))
    monkeypatch.setattr(make_fixture, "OPTIONS_PATH", options)
    saved = tmp_path / "saved"
    saved.mkdir()
    (saved / "peoplesearch-listing.html").write_text(LISTING, encoding="utf-8")
    (saved / "peoplesearch-no-results.html").write_text(NO_RESULTS, encoding="utf-8")

    make_fixture.main(["--folder", str(saved), "--values", str(values_file)])

    written = tmp_path / "fixtures" / "peoplesearch"
    assert "Marisol Quillfeather" in (written / "listing.html").read_text(
        encoding="utf-8"
    )
    assert "No people found" in (written / "no-results.html").read_text(
        encoding="utf-8"
    )


def test_folder_mode_reports_each_failure_and_carries_on(
    tmp_path, values_file, monkeypatch, capsys
):
    monkeypatch.setattr(make_fixture, "FIXTURES_DIR", tmp_path / "fixtures")
    monkeypatch.setattr(make_fixture, "OPTIONS_PATH", tmp_path / "none.yaml")
    saved = tmp_path / "saved"
    saved.mkdir()
    (saved / "otherpeople-listing.html").write_text("<p>nobody</p>", encoding="utf-8")
    (saved / "peoplesearch-listing.html").write_text(LISTING, encoding="utf-8")
    (saved / "notes.html").write_text("<p>notes</p>", encoding="utf-8")

    with pytest.raises(SystemExit) as exit_info:
        make_fixture.main(["--folder", str(saved), "--values", str(values_file)])

    assert exit_info.value.code == 1
    out = capsys.readouterr().out
    assert "otherpeople listing: couldn't find" in out
    assert "peoplesearch listing: wrote" in out
    assert "skipped 1 file" in out
    assert (tmp_path / "fixtures" / "peoplesearch" / "listing.html").exists()


def test_a_kept_phrase_only_matches_whole_words(rules):
    fixture = clean("<p>Page one</p>", rules, "no-results", keep=["Age"])

    assert BeautifulSoup(fixture, "html.parser").p.get_text(strip=True) == "text"


def test_a_lone_initial_is_not_a_leftover(tmp_path):
    path = tmp_path / "fixture-values.yaml"
    path.write_text(yaml.safe_dump({**REAL, "middle_name": "R"}), encoding="utf-8")

    fixture = clean('<div class="r-0 r-flex">x</div>', load_values(path), "no-results")

    assert 'class="r-0 r-flex"' in fixture


def test_uuids_in_attributes_are_dropped(rules):
    page = '<div id="slot-b3eb4cec-5dc2-4a95-a95f-4e926c81d7a0" class="ad">x</div>'

    assert "b3eb4cec" not in clean(page, rules, "no-results")
