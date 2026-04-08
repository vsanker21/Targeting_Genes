"""Shared contracts for write_module*_export_manifest.py (index + optional tagging)."""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_export_manifest_writers_emit_matching_outline_module() -> None:
    for n in (3, 4, 5, 6, 7):
        path = _ROOT / f"scripts/write_module{n}_export_manifest.py"
        text = path.read_text(encoding="utf-8")
        needle = f'"outline_module": {n},'
        assert needle in text, f"{path.name}: expected JSON doc key {needle!r} for pipeline_results_index.by_outline_module"


def test_export_manifest_writers_emit_generated_utc_and_artifacts() -> None:
    for n in (3, 4, 5, 6, 7):
        path = _ROOT / f"scripts/write_module{n}_export_manifest.py"
        text = path.read_text(encoding="utf-8")
        assert '"generated_utc":' in text, f"{path.name}: missing generated_utc in manifest doc"
        assert '"artifacts":' in text, f"{path.name}: missing artifacts in manifest doc"


def test_export_manifest_writers_apply_optional_tags() -> None:
    line = "manifest_optional.apply_optional_tags_to_artifacts(artifacts, block.get(\"optional_tags\") or [])"
    for n in (3, 4, 5, 6, 7):
        path = _ROOT / f"scripts/write_module{n}_export_manifest.py"
        text = path.read_text(encoding="utf-8")
        assert line in text, f"{path.name}: expected optional_tags merge via manifest_optional"
        assert "import manifest_optional" in text, f"{path.name}: must import manifest_optional"


def test_export_manifest_writers_have_cli_entrypoint() -> None:
    for n in (3, 4, 5, 6, 7):
        path = _ROOT / f"scripts/write_module{n}_export_manifest.py"
        text = path.read_text(encoding="utf-8")
        assert 'if __name__ == "__main__":' in text, f"{path.name}: missing __main__ guard"
        assert "raise SystemExit(main())" in text, f"{path.name}: expected raise SystemExit(main())"


def test_export_manifest_writers_main_returns_int() -> None:
    for n in (3, 4, 5, 6, 7):
        path = _ROOT / f"scripts/write_module{n}_export_manifest.py"
        text = path.read_text(encoding="utf-8")
        assert "def main() -> int:" in text, f"{path.name}: main() should return int exit code"


def test_export_manifest_writers_use_future_annotations() -> None:
    for n in (3, 4, 5, 6, 7):
        path = _ROOT / f"scripts/write_module{n}_export_manifest.py"
        head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:30])
        assert "from __future__ import annotations" in head, (
            f"{path.name}: use from __future__ import annotations near top"
        )


def test_export_manifest_writers_emit_indented_json() -> None:
    """Stable, diff-friendly manifests in git and for humans."""
    for n in (3, 4, 5, 6, 7):
        path = _ROOT / f"scripts/write_module{n}_export_manifest.py"
        text = path.read_text(encoding="utf-8")
        if n == 4:
            assert "json.dumps(payload, indent=2)" in text, f"{path.name}: use indent=2 for JSON"
        else:
            assert "json.dumps(doc, indent=2)" in text, f"{path.name}: use indent=2 for JSON"


def test_export_manifest_writers_write_manifest_json_as_utf8() -> None:
    for n in (3, 4, 5, 6, 7):
        path = _ROOT / f"scripts/write_module{n}_export_manifest.py"
        text = path.read_text(encoding="utf-8")
        if n == 4:
            line = 'out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")'
        else:
            line = 'out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")'
        assert line in text, f"{path.name}: manifest output must be UTF-8 ({line!r})"


def test_export_manifest_writers_mkdir_parent_before_write() -> None:
    line = "out_path.parent.mkdir(parents=True, exist_ok=True)"
    for n in (3, 4, 5, 6, 7):
        path = _ROOT / f"scripts/write_module{n}_export_manifest.py"
        text = path.read_text(encoding="utf-8")
        assert line in text, f"{path.name}: create output parent dir before write_text"


def test_export_manifest_writers_read_config_with_yaml_safe_load_utf8() -> None:
    for n in (3, 4, 5, 6, 7):
        path = _ROOT / f"scripts/write_module{n}_export_manifest.py"
        text = path.read_text(encoding="utf-8")
        assert "yaml.safe_load" in text, f"{path.name}: load YAML config with safe_load"
        assert 'read_text(encoding="utf-8")' in text, f"{path.name}: read config as UTF-8"


def test_export_manifest_writers_import_json_and_pathlib_path() -> None:
    for n in (3, 4, 5, 6, 7):
        path = _ROOT / f"scripts/write_module{n}_export_manifest.py"
        text = path.read_text(encoding="utf-8")
        assert re.search(r"^import json\s*$", text, re.MULTILINE), f"{path.name}: top-level import json"
        assert re.search(r"^from pathlib import Path\s*$", text, re.MULTILINE), (
            f"{path.name}: from pathlib import Path"
        )


def test_export_manifest_writers_import_yaml_typing_any_and_datetime_utc() -> None:
    gen = '"generated_utc": datetime.now(tz=timezone.utc).isoformat(),'
    for n in (3, 4, 5, 6, 7):
        path = _ROOT / f"scripts/write_module{n}_export_manifest.py"
        text = path.read_text(encoding="utf-8")
        assert re.search(r"^import yaml\s*$", text, re.MULTILINE), f"{path.name}: import yaml"
        assert re.search(r"^from typing import Any\s*$", text, re.MULTILINE), (
            f"{path.name}: from typing import Any"
        )
        assert re.search(r"^from datetime import datetime, timezone\s*$", text, re.MULTILINE), (
            f"{path.name}: from datetime import datetime, timezone"
        )
        assert gen in text, f"{path.name}: generated_utc must use timezone.utc"
