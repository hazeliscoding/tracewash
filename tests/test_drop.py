from definition_samples import VALID, sample
from import_ca_registry import parse_registry

from tracewash import drop
from tracewash.definitions import Broker

HEADER = (
    '"Data broker name:","Doing Business As (DBA), if applicable:",'
    '"Data broker primary website:","Data broker primary contact email address:"\n'
)


def entry(*domains):
    return drop.RegistryEntry(name="Some Broker, LLC", domains=domains)


def test_a_broker_is_covered_when_an_entry_lists_its_domain():
    covering = entry("otherpeople.example", "peoplesearch.example")

    assert (
        drop.covering_entry(Broker(**VALID), [entry("x.example"), covering]) == covering
    )


def test_a_subdomain_in_the_registry_counts_as_the_brokers_domain():
    covering = entry("pro.peoplesearch.example")

    assert drop.covering_entry(Broker(**VALID), [covering]) == covering


def test_a_broker_missing_from_the_registry_is_not_covered():
    assert drop.covering_entry(Broker(**VALID), [entry("otherpeople.example")]) is None


def test_a_lookalike_domain_does_not_count():
    assert (
        drop.covering_entry(Broker(**VALID), [entry("notpeoplesearch.example")]) is None
    )


def test_parse_registry_reads_every_website_as_a_bare_domain():
    csv_text = (
        HEADER
        + '"People Search, Inc.","PS","https://www.PeopleSearch.example/about; '
        + 'otherpeople.example, http://pro.peoplesearch.example","a@peoplesearch.example"\n'
    )

    assert parse_registry(csv_text) == [
        drop.RegistryEntry(
            name="People Search, Inc.",
            domains=(
                "peoplesearch.example",
                "otherpeople.example",
                "pro.peoplesearch.example",
            ),
        )
    ]


def test_parse_registry_skips_entries_without_a_website():
    csv_text = HEADER + '"Quiet Data, LLC","","N/A",""\n'

    assert parse_registry(csv_text) == []


def test_the_shipped_registry_loads():
    assert len(drop.load_registry()) > 500


def test_brokers_elsewhere_are_not_matched_by_accident():
    broker = Broker(**sample("otherpeople"))

    assert drop.covering_entry(broker, [entry("peoplesearch.example")]) is None
