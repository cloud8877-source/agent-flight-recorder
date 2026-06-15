from __future__ import annotations

import os


def storage_backend() -> str:
    return os.environ.get("AFR_STORAGE_BACKEND", "sqlite").lower()