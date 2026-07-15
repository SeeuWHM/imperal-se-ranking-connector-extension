"""SE Ranking extension — entry point with module hot-reload."""
from __future__ import annotations

import sys
import os

_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _dir)

for _m in list(sys.modules):
    if _m in ("app", "api_client", "params", "skeleton", "handlers",
              "handlers_research", "handlers_settings", "handlers_competitors",
              "handlers_backlinks", "panels", "panels_workspace"):
        del sys.modules[_m]

from app import ext, chat  # noqa: E402, F401

import skeleton            # noqa: E402, F401
import handlers             # noqa: E402, F401
import handlers_research    # noqa: E402, F401
import handlers_settings    # noqa: E402, F401
import handlers_competitors  # noqa: E402, F401
import handlers_backlinks    # noqa: E402, F401
import panels                # noqa: E402, F401
import panels_workspace      # noqa: E402, F401
