import pytest
from definition_samples import VALID, changed, write_definition

from tracewash.definitions import (
    BROKERS_DIR,
    DefinitionError,
    OptOutMethod,
    load_broker,
    load_brokers,
)


def test_a_valid_definition_loads(tmp_path):
    broker = load_broker(write_definition(tmp_path, VALID))

    assert broker.id == "peoplesearch"
    assert broker.optout.method is OptOutMethod.FORM
    assert broker.search.result == "div.result"


@pytest.mark.parametrize(
    ("path", "value", "error"),
    [
        ("color", "teal", "color"),
        ("id", "People Search", "id"),
        ("domains", ["https://www.peoplesearch.example"], "domains"),
        ("search.url", "https://www.peoplesearch.example/{ssn}", "ssn"),
        ("search.url", "https://www.peoplesearch.example/{listing_url}", "listing_url"),
        ("search.url", "https://www.peoplesearch.example/{city:upper}", "upper"),
        ("search.url", "http://www.peoplesearch.example/{city}", "https"),
        ("search.url", "https://tracker.example/{city}", "tracker.example"),
        ("search.result", "div.result >", "search.result"),
        ("search.no_results", None, "no_results"),
        ("optout.url", None, "url"),
        ("optout.method", "email", "email"),
        ("optout.needs", ["shoe_size"], "optout.needs"),
        ("optout.confirm", "carrier pigeon", "confirm"),
        ("recheck_days", 0, "recheck_days"),
    ],
    ids=[
        "unknown-key",
        "id-not-a-slug",
        "domain-with-scheme",
        "unknown-placeholder",
        "listing-url-in-search",
        "unknown-transform",
        "plain-http",
        "host-outside-domains",
        "broken-selector",
        "missing-no-results",
        "form-without-url",
        "email-without-address",
        "unknown-needed-field",
        "unknown-confirmation",
        "zero-recheck",
    ],
)
def test_an_invalid_definition_is_rejected(tmp_path, path, value, error):
    data = changed(path, value)
    definition = write_definition(tmp_path, data, stem="peoplesearch")

    with pytest.raises(DefinitionError, match=error):
        load_broker(definition)


def test_the_id_must_match_the_file_name(tmp_path):
    definition = write_definition(tmp_path, VALID, stem="other")

    with pytest.raises(DefinitionError, match="other"):
        load_broker(definition)


def test_a_file_that_is_not_a_mapping_is_rejected(tmp_path):
    definition = tmp_path / "peoplesearch.yaml"
    definition.write_text("- just\n- a list\n", encoding="utf-8")

    with pytest.raises(DefinitionError, match="mapping"):
        load_broker(definition)


def test_the_error_names_the_file(tmp_path):
    definition = write_definition(tmp_path, changed("recheck_days", 0))

    with pytest.raises(DefinitionError, match="peoplesearch.yaml"):
        load_broker(definition)


def test_every_shipped_definition_loads():
    for broker in load_brokers(BROKERS_DIR):
        assert broker.id


def test_an_opt_out_can_ask_for_a_street_an_age_and_a_birth_date(tmp_path):
    data = changed(
        "optout.needs", ["first_name", "last_name", "street", "age", "birth_date"]
    )

    broker = load_broker(write_definition(tmp_path, data))

    assert [str(field) for field in broker.optout.needs][-3:] == [
        "street",
        "age",
        "birth_date",
    ]
