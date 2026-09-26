"""Open each broker's two fixture searches in your browser.

For every broker, it opens a search for you, using your fixture values, and a
search for the fake profile, which should find nothing. Save each page as
"Webpage, Complete" under the name it prints, then run make_fixture.py.
"""

import argparse
import sys
import webbrowser
from pathlib import Path

import yaml
from make_fixture import VALUES_PATH, load_fake_profile

from tracewash.definitions import load_brokers
from tracewash.search import search_url

SEARCH_FIELDS = (
    "first_name",
    "middle_name",
    "last_name",
    "city",
    "state",
    "state_name",
    "zip",
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("brokers", nargs="*", help="broker ids (default: every broker)")
    parser.add_argument("--values", type=Path, default=VALUES_PATH)
    args = parser.parse_args(argv)
    if not args.values.exists():
        sys.exit(f"open_searches: {args.values} doesn't exist yet")
    real = yaml.safe_load(args.values.read_text(encoding="utf-8"))
    searches = (("listing", real), ("no-results", load_fake_profile()))
    for broker in load_brokers():
        if args.brokers and broker.id not in args.brokers:
            continue
        for kind, profile in searches:
            values = {
                field: str(profile[field])
                for field in SEARCH_FIELDS
                if profile.get(field)
            }
            try:
                url = search_url(broker.search, values)
            except ValueError as error:
                print(f"{broker.id}: {error}, so search by hand")
                continue
            # The URL holds your name, so it goes to the browser and is never
            # printed.
            webbrowser.open_new_tab(url)
            print(f"{broker.id}: save as {broker.id}-{kind}.html")


if __name__ == "__main__":
    main()
