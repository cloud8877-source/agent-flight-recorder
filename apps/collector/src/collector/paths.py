from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    if env := os.environ.get("AFR_REPO_ROOT"):
        return Path(env)
    docker = Path("/app")
    if (docker / "infra").is_dir():
        return docker
    return Path(__file__).resolve().parents[4]


def infra_dir() -> Path:
    if env := os.environ.get("AFR_INFRA_PATH"):
        return Path(env)
    return repo_root() / "infra"


def schema_path(backend: str) -> Path:
    return infra_dir() / backend / "schema.sql"