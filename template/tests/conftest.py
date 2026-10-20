from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def static_root(tmp_path: Path, settings: Any) -> Path:
    """An existing, empty `STATIC_ROOT` for every test.

    WhiteNoise warns when `STATIC_ROOT` does not exist, and in a checkout it
    does not until `collectstatic` runs (the image runs it at build time).
    Pointing it at a folder that exists removes the warning's cause, so no
    test needs it ignored, and nothing is written into `src/`.
    """
    settings.STATIC_ROOT = tmp_path
    return tmp_path
