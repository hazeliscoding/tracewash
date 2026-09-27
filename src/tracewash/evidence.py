import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from tracewash.vault import Vault, VaultError


@dataclass(frozen=True)
class Evidence:
    id: str
    captured_at: datetime
    sha256: str
    media_type: str
    source_url: str | None = None


def add(
    vault: Vault, data: bytes, media_type: str, source_url: str | None = None
) -> Evidence:
    # A random ID can go into the tracker: unlike a content hash, it can't be
    # matched by hashing a guessed screenshot or search URL.
    stored = Evidence(
        id=secrets.token_hex(16),
        captured_at=datetime.now(UTC),
        sha256=hashlib.sha256(data).hexdigest(),
        media_type=media_type,
        source_url=source_url,
    )
    vault.write(f"evidence/{stored.id}.data", data)
    record = {**stored.__dict__, "captured_at": stored.captured_at.isoformat()}
    vault.write(f"evidence/{stored.id}.json", json.dumps(record).encode())
    return stored


def load(vault: Vault, evidence_id: str) -> tuple[Evidence, bytes]:
    # An ID becomes part of a path, so anything else could reach outside the
    # evidence folder.
    if not re.fullmatch(r"[0-9a-f]{32}", evidence_id):
        raise VaultError(f"{evidence_id!r} is not an evidence ID")
    if not (vault.path / "evidence" / f"{evidence_id}.json").exists():
        raise VaultError(f"there is no evidence {evidence_id}")
    record = json.loads(vault.read(f"evidence/{evidence_id}.json"))
    record["captured_at"] = datetime.fromisoformat(record["captured_at"]).astimezone(
        UTC
    )
    return Evidence(**record), vault.read(f"evidence/{evidence_id}.data")
