#!/usr/bin/env python3
"""Resolve config/data_sources.yaml after expanding {data_root} from env or file."""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Install PyYAML: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg_path = root / "config" / "data_sources.yaml"
    env_root = os.environ.get("GLIOMA_TARGET_DATA_ROOT", "").strip()
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    dr = env_root or data.get("data_root", "")
    if not dr:
        print("No data_root in YAML and GLIOMA_TARGET_DATA_ROOT unset.", file=sys.stderr)
        sys.exit(1)

    def expand(s: str) -> str:
        return s.replace("{data_root}", dr.replace("\\", "/"))

    def walk(x):
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(i) for i in x]
        if isinstance(x, str) and "{data_root}" in x:
            return expand(x)
        return x

    resolved = walk(data)
    resolved["data_root"] = dr.replace("\\", "/")
    out = yaml.dump(resolved, default_flow_style=False, sort_keys=False, allow_unicode=True)
    print(out, end="")


if __name__ == "__main__":
    main()
