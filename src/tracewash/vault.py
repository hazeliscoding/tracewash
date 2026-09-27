import base64
import json
import os
import secrets
from pathlib import Path
from typing import Self

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

FORMAT = 1
HEADER = "header.json"
KDF_PARAMS = {"memory_cost": 64 * 1024, "iterations": 3, "lanes": 4}
KEY_CONTEXT = b"tracewash vault data key v1"
NONCE_BYTES = 12


class VaultError(Exception):
    pass


class WrongPassphrase(VaultError):
    pass


def _passphrase_key(passphrase: str, salt: bytes, params: dict) -> bytes:
    return Argon2id(salt=salt, length=32, **params).derive(passphrase.encode())


def _seal(key: bytes, data: bytes, context: bytes) -> bytes:
    nonce = secrets.token_bytes(NONCE_BYTES)
    return nonce + AESGCM(key).encrypt(nonce, data, context)


def _open(key: bytes, sealed: bytes, context: bytes) -> bytes:
    return AESGCM(key).decrypt(sealed[:NONCE_BYTES], sealed[NONCE_BYTES:], context)


def _write_atomic(path: Path, data: bytes) -> None:
    partial = path.with_name(path.name + ".partial")
    partial.write_bytes(data)
    os.replace(partial, path)


class Vault:
    def __init__(self, path: Path, key: bytes):
        self.path = path
        self._key = key

    @classmethod
    def create(cls, path: Path, passphrase: str) -> Self:
        if (path / HEADER).exists():
            raise VaultError(f"a vault already exists at {path}")
        path.mkdir(parents=True, exist_ok=True)
        vault = cls(path, secrets.token_bytes(32))
        vault.change_passphrase(passphrase)
        return vault

    @classmethod
    def unlock(cls, path: Path, passphrase: str) -> Self:
        if not (path / HEADER).exists():
            raise VaultError(f"there is no vault at {path}. Run tracewash init first.")
        header = json.loads((path / HEADER).read_text(encoding="utf-8"))
        if header.get("format") != FORMAT:
            raise VaultError(
                f"this vault uses format {header.get('format')}, not {FORMAT}"
            )
        kdf = header["kdf"]
        salt = base64.b64decode(kdf["salt"])
        params = {name: kdf[name] for name in KDF_PARAMS}
        try:
            key = _open(
                _passphrase_key(passphrase, salt, params),
                base64.b64decode(header["key"]),
                KEY_CONTEXT,
            )
        except InvalidTag:
            raise WrongPassphrase("the passphrase is wrong") from None
        return cls(path, key)

    def change_passphrase(self, passphrase: str) -> None:
        # The passphrase only wraps the data key, so changing it rewrites the
        # header and leaves every encrypted file as it is.
        salt = secrets.token_bytes(16)
        wrapped = _seal(
            _passphrase_key(passphrase, salt, KDF_PARAMS), self._key, KEY_CONTEXT
        )
        header = {
            "format": FORMAT,
            "kdf": {
                "name": "argon2id",
                "salt": base64.b64encode(salt).decode(),
                **KDF_PARAMS,
            },
            "key": base64.b64encode(wrapped).decode(),
        }
        _write_atomic(self.path / HEADER, json.dumps(header, indent=2).encode())

    def write(self, name: str, data: bytes) -> None:
        target = self.path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        # The file's name is authenticated with its content, so a file copied
        # or renamed over another one fails to decrypt.
        _write_atomic(target, _seal(self._key, data, name.encode()))

    def read(self, name: str) -> bytes:
        try:
            return _open(self._key, (self.path / name).read_bytes(), name.encode())
        except InvalidTag:
            raise VaultError(
                f"{name} was changed or belongs to another vault"
            ) from None
