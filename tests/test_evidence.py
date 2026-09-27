import hashlib
from datetime import UTC, datetime

import pytest

from tracewash import evidence, paths
from tracewash.vault import Vault, VaultError


@pytest.fixture
def vault():
    return Vault.create(paths.vault_dir(), "correct horse battery staple")


def test_evidence_reads_back_with_its_time_and_hash(vault, canary_profile):
    shot = f"screenshot showing {canary_profile['email']}".encode()
    before = datetime.now(UTC)

    stored = evidence.add(vault, shot, "image/png")

    record, data = evidence.load(vault, stored.id)
    assert data == shot
    assert record.sha256 == hashlib.sha256(shot).hexdigest()
    assert record.media_type == "image/png"
    assert before <= record.captured_at <= datetime.now(UTC)
    assert record.captured_at.tzinfo is UTC


def test_ids_are_random_even_for_the_same_content(vault):
    first = evidence.add(vault, b"same", "image/png")
    second = evidence.add(vault, b"same", "image/png")

    assert first.id != second.id


def test_an_id_says_nothing_about_the_content(vault):
    stored = evidence.add(vault, b"search page", "text/html")

    assert stored.id not in hashlib.sha256(b"search page").hexdigest()
    assert len(stored.id) == 32


def test_an_unknown_id_is_refused(vault):
    with pytest.raises(VaultError, match="no evidence"):
        evidence.load(vault, "0" * 32)


def test_an_id_that_is_not_an_evidence_id_is_refused(vault):
    with pytest.raises(VaultError, match="not an evidence ID"):
        evidence.load(vault, "../profile")
