"""SE Ranking extension — entry point with module hot-reload."""
from __future__ import annotations

import sys
import os

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)

for _m in list(sys.modules):
    if _m in ("app", "api_client", "params", "skeleton", "handlers", "panels"):
        del sys.modules[_m]

from app import ext, chat  # noqa: E402, F401

import skeleton  # noqa: E402, F401
import handlers  # noqa: E402, F401
import panels    # noqa: E402, F401
