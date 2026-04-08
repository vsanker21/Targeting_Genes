#!/usr/bin/env python3
"""
Fetch LINCS / CLUE API JSON snapshots into GLIOMA_TARGET_DATA_ROOT (see config/required_downloads.yaml clue_api).

Requires a free academic user key from https://api.clue.io (register at https://clue.io/).
Provide credentials only via environment (never commit):

  CLUE_API_KEY=<your_user_key>
  OR
  CLUE_API_TOKEN_FILE=C:\\path\\outside\\repo\\clue_key.txt   (first non-empty line = key)

Then:

  python scripts/fetch_clue_api_subset.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

_SCRIPTS = Path(__file__).resolve().parent
_REPO = _SCRIPTS.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import download_all_required as dar  # noqa: E402
import download_external_datasets as ext  # noqa: E402


def main() -> int:
    key = dar.load_clue_api_key()
    if not key:
        print(
            "ERROR: No CLUE key. Set CLUE_API_KEY or CLUE_API_TOKEN_FILE (see docstring).",
            file=sys.stderr,
        )
        return 1
    cfg_path = _REPO / "config" / "required_downloads.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    root = ext.data_root()
    if not root.is_dir():
        print(f"ERROR: data_root is not a directory: {root}", file=sys.stderr)
        return 1
    print(f"CLUE: writing snapshots under {root.resolve()} …")
    dar.download_clue_lincs_subset(root, cfg, key)
    print("CLUE: done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
