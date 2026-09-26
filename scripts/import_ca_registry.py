"""Refresh the California data broker registry snapshot behind the DROP flags.

Run `uv run scripts/import_ca_registry.py`, review the diff, and commit it.
"""

import argparse
import csv
import io
import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

from tracewash.drop import REGISTRY_PATH, RegistryEntry, normalize_domain

SOURCE = "https://cppa.ca.gov/data_broker_registry/registry.csv"


def parse_registry(csv_text: str) -> list[RegistryEntry]:
    entries = []
    for row in csv.DictReader(io.StringIO(csv_text)):
        # One cell lists every site, split by semicolons, commas or spaces.
        websites = re.split(r"[;,\s]+", row["Data broker primary website:"])
        domains = tuple(dict.fromkeys(filter(None, map(normalize_domain, websites))))
        if domains:
            entries.append(
                RegistryEntry(name=row["Data broker name:"].strip(), domains=domains)
            )
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--csv", type=Path, help="read a downloaded registry.csv instead"
    )
    args = parser.parse_args()
    if args.csv:
        text = args.csv.read_text(encoding="utf-8-sig")
    else:
        with urllib.request.urlopen(SOURCE, timeout=60) as response:
            text = response.read().decode("utf-8-sig")
    entries = sorted(parse_registry(text), key=lambda entry: entry.name.casefold())
    snapshot = {
        "source": SOURCE,
        "retrieved": datetime.now(UTC).strftime("%Y.%m.%d"),
        "brokers": [
            {"name": entry.name, "domains": list(entry.domains)} for entry in entries
        ],
    }
    REGISTRY_PATH.parent.mkdir(exist_ok=True)
    REGISTRY_PATH.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {len(entries)} registry entries to {REGISTRY_PATH}")


if __name__ == "__main__":
    main()
