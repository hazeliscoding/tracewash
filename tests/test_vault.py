import json

import pytest

from tracewash import paths
from tracewash.vault import Vault, VaultError, WrongPassphrase

PASSPHRASE = "correct horse battery staple"


@pytest.fixture
def vault():
    return Vault.create(paths.vault_dir(), PASSPHRASE)


def test_what_is_written_reads_back_after_unlocking(vault, canary_profile):
    vault.write("profile.bin", json.dumps(canary_profile).encode())

    reopened = Vault.unlock(paths.vault_dir(), PASSPHRASE)

    assert json.loads(reopened.read("profile.bin")) == canary_profile


def test_files_on_disk_hold_only_ciphertext(vault, canary_profile):
    vault.write("profile.bin", canary_profile["email"].encode())

    for path in paths.vault_dir().rglob("*"):
        if path.is_file():
            assert canary_profile["email"].encode() not in path.read_bytes()


def test_a_wrong_passphrase_is_refused(vault):
    with pytest.raises(WrongPassphrase):
        Vault.unlock(paths.vault_dir(), "not the passphrase")


def test_changing_the_passphrase_keeps_the_data(vault):
    vault.write("profile.bin", b"kept")

    vault.change_passphrase("a brand new passphrase")

    with pytest.raises(WrongPassphrase):
        Vault.unlock(paths.vault_dir(), PASSPHRASE)
    assert (
        Vault.unlock(paths.vault_dir(), "a brand new passphrase").read("profile.bin")
        == b"kept"
    )


def test_a_tampered_file_is_refused(vault):
    vault.write("profile.bin", b"original")
    path = paths.vault_dir() / "profile.bin"
    data = bytearray(path.read_bytes())
    data[-1] ^= 1
    path.write_bytes(bytes(data))

    with pytest.raises(VaultError, match="profile.bin"):
        vault.read("profile.bin")


def test_a_file_moved_to_another_name_is_refused(vault):
    vault.write("evidence/a.bin", b"evidence a")
    (paths.vault_dir() / "evidence" / "a.bin").rename(
        paths.vault_dir() / "evidence" / "b.bin"
    )

    with pytest.raises(VaultError, match="b.bin"):
        vault.read("evidence/b.bin")


def test_creating_a_second_vault_in_the_same_place_is_refused(vault):
    with pytest.raises(VaultError, match="already exists"):
        Vault.create(paths.vault_dir(), PASSPHRASE)


def test_unlocking_before_init_says_what_to_do():
    with pytest.raises(VaultError, match="tracewash init"):
        Vault.unlock(paths.vault_dir(), PASSPHRASE)


def test_the_vault_lives_in_tracewash_home(tracewash_home):
    assert paths.vault_dir() == tracewash_home / "vault"
    assert paths.tracker_path() == tracewash_home / "tracker.sqlite3"
