"""Sanity checks for scripts shared by export manifests and pipeline_results_index."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

_WRITER_CONFIG: tuple[tuple[int, str], ...] = (
    (3, "module3_inputs.yaml"),
    (4, "module2_integration.yaml"),
    (5, "module5_inputs.yaml"),
    (6, "module6_inputs.yaml"),
    (7, "module7_inputs.yaml"),
)


def test_export_manifest_writers_load_expected_config_paths() -> None:
    """Each writer's load_* must open the same config file Snakemake passes as an input."""
    for mod, cfg_name in _WRITER_CONFIG:
        script = _ROOT / f"scripts/write_module{mod}_export_manifest.py"
        text = script.read_text(encoding="utf-8")
        needle = f'repo_root() / "config" / "{cfg_name}"'
        assert needle in text, f"{script.name}: expected {needle} in load helper"


def test_write_pipeline_results_index_load_cfg_uses_pipeline_inventory_yaml() -> None:
    text = (_ROOT / "scripts/write_pipeline_results_index.py").read_text(encoding="utf-8")
    assert 'repo_root() / "config" / "pipeline_inventory.yaml"' in text, (
        "load_cfg must read config/pipeline_inventory.yaml (same file as Snakemake inv=)"
    )


def test_write_pipeline_results_index_imports_datetime_timezone_and_generated_utc() -> None:
    text = (_ROOT / "scripts/write_pipeline_results_index.py").read_text(encoding="utf-8")
    assert re.search(r"^from datetime import datetime, timezone\s*$", text, re.MULTILINE)
    assert '"generated_utc": datetime.now(tz=timezone.utc).isoformat(),' in text


def test_write_pipeline_results_index_core_stdlib_imports() -> None:
    text = (_ROOT / "scripts/write_pipeline_results_index.py").read_text(encoding="utf-8")
    assert re.search(r"^import json\s*$", text, re.MULTILINE)
    assert re.search(r"^from pathlib import Path\s*$", text, re.MULTILINE)
    assert re.search(r"^from collections import OrderedDict\s*$", text, re.MULTILINE)
    assert re.search(r"^import yaml\s*$", text, re.MULTILINE)


def test_write_pipeline_results_index_load_cfg_uses_yaml_safe_load_utf8() -> None:
    text = (_ROOT / "scripts/write_pipeline_results_index.py").read_text(encoding="utf-8")
    assert 'return yaml.safe_load(p.read_text(encoding="utf-8"))' in text, (
        "load_cfg should use yaml.safe_load on UTF-8 pipeline_inventory.yaml"
    )


def test_write_pipeline_results_index_cli_entrypoint() -> None:
    text = (_ROOT / "scripts/write_pipeline_results_index.py").read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in text
    assert "raise SystemExit(main(sys.argv[1:]))" in text


def test_write_pipeline_results_index_emits_indented_json() -> None:
    text = (_ROOT / "scripts/write_pipeline_results_index.py").read_text(encoding="utf-8")
    assert "json.dumps(doc, indent=2)" in text


def test_write_pipeline_results_index_writes_utf8_json() -> None:
    text = (_ROOT / "scripts/write_pipeline_results_index.py").read_text(encoding="utf-8")
    assert 'out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")' in text


def test_write_pipeline_results_index_main_accepts_argv() -> None:
    text = (_ROOT / "scripts/write_pipeline_results_index.py").read_text(encoding="utf-8")
    assert "def main(argv: list[str] | None = None) -> int:" in text, (
        "main must accept argv for CLI and Snakemake subprocess parity"
    )


def test_write_pipeline_results_index_reads_glioma_target_pipeline_index_strict_env() -> None:
    text = (_ROOT / "scripts/write_pipeline_results_index.py").read_text(encoding="utf-8")
    assert 'os.environ.get("GLIOMA_TARGET_PIPELINE_INDEX_STRICT"' in text, (
        "strict mode must honor GLIOMA_TARGET_PIPELINE_INDEX_STRICT (see module docstring)"
    )


def test_write_pipeline_results_index_argparse_strict_flag() -> None:
    text = (_ROOT / "scripts/write_pipeline_results_index.py").read_text(encoding="utf-8")
    assert (
        '        "--strict",' in text
    ), "CLI --strict must remain registered (GLIOMA_TARGET_PIPELINE_INDEX_STRICT / CI gates)"


def test_write_pipeline_results_index_index_schema_constant_and_summary() -> None:
    text = (_ROOT / "scripts/write_pipeline_results_index.py").read_text(encoding="utf-8")
    assert re.search(r"^INDEX_SCHEMA = \d+\s*$", text, re.MULTILINE), (
        "INDEX_SCHEMA must be a module-level integer (bump when summary shape changes)"
    )
    assert '"index_schema": INDEX_SCHEMA' in text, "summary dict must emit index_schema for downstream parsers"


def test_write_pipeline_results_index_provenance_job_path_keys() -> None:
    """Module docstring documents output, output_rnk, input, input_tsv, gts_input — keep extractors aligned."""
    text = (_ROOT / "scripts/write_pipeline_results_index.py").read_text(encoding="utf-8")
    assert (
        'return job.get("input") or job.get("gts_input") or job.get("input_tsv")' in text
    ), "_job_input_paths must harvest input | gts_input | input_tsv"
    assert 'return job.get("output") or job.get("output_rnk")' in text, (
        "_job_output_paths must harvest output | output_rnk"
    )


def test_write_pipeline_results_index_mkdir_parent_before_write() -> None:
    text = (_ROOT / "scripts/write_pipeline_results_index.py").read_text(encoding="utf-8")
    assert "out_path.parent.mkdir(parents=True, exist_ok=True)" in text


def test_write_pipeline_results_index_uses_future_annotations() -> None:
    path = _ROOT / "scripts/write_pipeline_results_index.py"
    head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:28])
    assert "from __future__ import annotations" in head


def test_manifest_optional_uses_future_annotations() -> None:
    path = _ROOT / "scripts/manifest_optional.py"
    head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:16])
    assert "from __future__ import annotations" in head


def test_manifest_optional_defines_apply_optional_tags_to_artifacts() -> None:
    text = (_ROOT / "scripts/manifest_optional.py").read_text(encoding="utf-8")
    assert "def apply_optional_tags_to_artifacts(" in text, (
        "export manifest writers call manifest_optional.apply_optional_tags_to_artifacts"
    )


def test_manifest_optional_loads_and_exposes_apply() -> None:
    path = _ROOT / "scripts" / "manifest_optional.py"
    spec = importlib.util.spec_from_file_location("manifest_optional_ci", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(getattr(mod, "apply_optional_tags_to_artifacts", None))
