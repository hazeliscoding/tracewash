import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from tracewash.definitions import Broker

REGISTRY_PATH = Path(__file__).parent / "data" / "ca_registry.json"

_DOMAIN = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$")


@dataclass(frozen=True)
class RegistryEntry:
    name: str
    domains: tuple[str, ...]


def normalize_domain(website: str) -> str | None:
    text = website.strip().lower()
    # Registry websites come with and without a scheme; urlsplit only finds the
    # host after "//".
    host = urlsplit(text if "://" in text else f"//{text}").hostname or ""
    host = host.removeprefix("www.").rstrip(".")
    return host if _DOMAIN.match(host) else None


def load_registry() -> list[RegistryEntry]:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return [
        RegistryEntry(entry["name"], tuple(entry["domains"]))
        for entry in data["brokers"]
    ]


def covering_entry(
    broker: Broker, registry: list[RegistryEntry]
) -> RegistryEntry | None:
    for entry in registry:
        for listed in entry.domains:
            if any(
                listed == own or listed.endswith(f".{own}") for own in broker.domains
            ):
                return entry
    return None
