import os
from pathlib import Path

import platformdirs


def home() -> Path:
    configured = os.environ.get("TRACEWASH_HOME")
    if configured:
        return Path(configured)
    return Path(platformdirs.user_data_dir("tracewash", appauthor=False))


def vault_dir() -> Path:
    return home() / "vault"


def tracker_path() -> Path:
    return home() / "tracker.sqlite3"
