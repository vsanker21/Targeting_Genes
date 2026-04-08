"""Config output_json for M3–M7 export manifests and pipeline_results_index must match Snakefile rule outputs."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from snakefile_rule_block import rule_block
from snakefile_text_cache import snakefile_text

_ROOT = Path(__file__).resolve().parents[1]
_SNAKE = snakefile_text()

_CASES: tuple[tuple[str, str, str, str], ...] = (
    ("m3_export_manifest", "config/module3_inputs.yaml", "module3_export_manifest", "output_json"),
    ("m4_export_manifest", "config/module2_integration.yaml", "module4_export_manifest", "output_json"),
    ("m5_export_manifest", "config/module5_inputs.yaml", "module5_export_manifest", "output_json"),
    ("m6_export_manifest", "config/module6_inputs.yaml", "module6_export_manifest", "output_json"),
    ("m7_export_manifest", "config/module7_inputs.yaml", "module7_export_manifest", "output_json"),
    ("pipeline_results_index", "config/pipeline_inventory.yaml", "pipeline_results_index", "output_json"),
)


def _first_anonymous_string_output(blk: str) -> str:
    m = re.search(r"\boutput:\s*\n\s+\"([^\"]+)\"", blk)
    assert m, "expected a single quoted output path (anonymous output) in rule block"
    return m.group(1).replace("\\", "/")


def test_export_manifest_and_pipeline_index_output_json_matches_snakefile() -> None:
    for rule_name, cfg_rel, block_key, out_key in _CASES:
        cfg_path = _ROOT / cfg_rel
        doc = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        block = doc.get(block_key) or {}
        yaml_out = str(block.get(out_key, "") or "").strip().replace("\\", "/")
        assert yaml_out, f"{cfg_rel}: missing {block_key}.{out_key}"
        snake_out = _first_anonymous_string_output(rule_block(_SNAKE, rule_name))
        assert yaml_out == snake_out, (
            f"{rule_name}: {cfg_rel} {block_key}.{out_key}={yaml_out!r} != Snakefile output {snake_out!r}"
        )


def test_module_export_manifest_and_pipeline_index_config_blocks_enabled() -> None:
    """Writers short-circuit when enabled is false; default repo keeps these on."""
    for _rule_name, cfg_rel, block_key, _out_key in _CASES:
        doc = yaml.safe_load((_ROOT / cfg_rel).read_text(encoding="utf-8"))
        block = doc.get(block_key)
        assert block is not None, f"{cfg_rel} missing {block_key}"
        assert block.get("enabled") is True, (
            f"{cfg_rel} {block_key}.enabled must be true for default pipeline (got {block.get('enabled')!r})"
        )


def test_export_manifest_and_pipeline_index_enabled_yaml_is_bool() -> None:
    """Use YAML true/false (boolean), not unquoted yes/no strings that confuse truthiness."""
    for _rule_name, cfg_rel, block_key, _out_key in _CASES:
        doc = yaml.safe_load((_ROOT / cfg_rel).read_text(encoding="utf-8"))
        block = doc.get(block_key)
        assert block is not None, f"{cfg_rel} missing {block_key}"
        en = block.get("enabled")
        assert isinstance(en, bool), (
            f"{cfg_rel} {block_key}.enabled must be boolean (got {type(en).__name__}: {en!r})"
        )


def test_module_export_manifest_config_blocks_declare_optional_tags_list() -> None:
    """manifest_optional.apply_optional_tags reads YAML optional_tags; keep an explicit list in config."""
    for rule_name, cfg_rel, block_key, _out_key in _CASES:
        if rule_name == "pipeline_results_index":
            continue
        doc = yaml.safe_load((_ROOT / cfg_rel).read_text(encoding="utf-8"))
        block = doc.get(block_key) or {}
        assert "optional_tags" in block, f"{cfg_rel} {block_key} must declare optional_tags (use [] if none)"
        assert isinstance(block["optional_tags"], list), (
            f"{cfg_rel} {block_key}.optional_tags must be a YAML list (got {type(block['optional_tags']).__name__})"
        )


def test_module_export_manifest_optional_tags_entries_are_strings_when_present() -> None:
    """optional_tags must be tag names (str); writers compare to row['tag'] strings."""
    for rule_name, cfg_rel, block_key, _out_key in _CASES:
        if rule_name == "pipeline_results_index":
            continue
        doc = yaml.safe_load((_ROOT / cfg_rel).read_text(encoding="utf-8"))
        block = doc.get(block_key) or {}
        for i, item in enumerate(block.get("optional_tags") or []):
            assert isinstance(item, str), (
                f"{cfg_rel} {block_key}.optional_tags[{i}] must be str (got {type(item).__name__}: {item!r})"
            )


def test_export_manifest_and_pipeline_index_output_json_yaml_values_are_strings() -> None:
    """Writers pass output paths through str(); YAML must not use bare ints or other types."""
    for _rule_name, cfg_rel, block_key, out_key in _CASES:
        doc = yaml.safe_load((_ROOT / cfg_rel).read_text(encoding="utf-8"))
        block = doc.get(block_key) or {}
        val = block.get(out_key)
        assert isinstance(val, str) and val.strip(), (
            f"{cfg_rel} {block_key}.{out_key} must be a non-empty string (got {type(val).__name__}: {val!r})"
        )


def test_pipeline_inventory_list_shaped_keys() -> None:
    """pipeline_results_index uses list fields the writer iterates; keep YAML types strict."""
    inv = _ROOT / "config" / "pipeline_inventory.yaml"
    doc = yaml.safe_load(inv.read_text(encoding="utf-8"))
    pri = doc.get("pipeline_results_index")
    assert pri is not None, "pipeline_inventory.yaml missing pipeline_results_index"
    for key in ("manifest_paths", "provenance_paths", "optional_path_posix", "primary_deliverables"):
        v = pri.get(key)
        assert isinstance(v, list), f"pipeline_results_index.{key} must be a YAML list (got {type(v).__name__})"
    for i, p in enumerate(pri.get("manifest_paths") or []):
        assert isinstance(p, str), f"manifest_paths[{i}] must be str (got {type(p).__name__})"
    for i, item in enumerate(pri.get("primary_deliverables") or []):
        assert isinstance(item, dict), f"primary_deliverables[{i}] must be a mapping (got {type(item).__name__})"
        pid = item.get("id")
        pp = item.get("path_posix")
        assert isinstance(pid, str) and pid.strip(), f"primary_deliverables[{i}].id must be non-empty str"
        assert isinstance(pp, str) and pp.strip(), f"primary_deliverables[{i}].path_posix must be non-empty str"
        mod = item.get("module", 7)
        assert isinstance(mod, int) and 1 <= mod <= 7, f"primary_deliverables[{i}].module must be int 1–7"


def test_pipeline_inventory_provenance_path_and_module_types() -> None:
    """harvest_provenance_outputs expects path str and int() module from YAML."""
    inv = _ROOT / "config" / "pipeline_inventory.yaml"
    doc = yaml.safe_load(inv.read_text(encoding="utf-8"))
    pri = doc.get("pipeline_results_index") or {}
    for i, item in enumerate(pri.get("provenance_paths") or []):
        assert isinstance(item, dict), f"provenance_paths[{i}] must be a mapping (got {type(item).__name__})"
        p = item.get("path")
        mod = item.get("module")
        assert isinstance(p, str) and p.strip(), (
            f"provenance_paths[{i}].path must be non-empty str (got {p!r})"
        )
        assert isinstance(mod, int) and 3 <= mod <= 7, (
            f"provenance_paths[{i}].module must be int 3–7 (got {mod!r})"
        )


_MANIFEST_WRITERS: tuple[tuple[int, str, str, str], ...] = (
    (3, "scripts/write_module3_export_manifest.py", "config/module3_inputs.yaml", "module3_export_manifest"),
    (4, "scripts/write_module4_export_manifest.py", "config/module2_integration.yaml", "module4_export_manifest"),
    (5, "scripts/write_module5_export_manifest.py", "config/module5_inputs.yaml", "module5_export_manifest"),
    (6, "scripts/write_module6_export_manifest.py", "config/module6_inputs.yaml", "module6_export_manifest"),
    (7, "scripts/write_module7_export_manifest.py", "config/module7_inputs.yaml", "module7_export_manifest"),
)


def _block_fallback_export_manifest_path(script: Path, module: int) -> str:
    text = script.read_text(encoding="utf-8")
    suffix = f"module{module}_export_manifest.json"
    hits = [
        m.group(1).replace("\\", "/")
        for m in re.finditer(r'block\.get\("output_json",\s*"([^"]+)"\)', text)
        if m.group(1).replace("\\", "/").endswith(suffix)
    ]
    assert len(hits) == 1, f"{script}: expected one block.get output_json fallback for {suffix}, got {hits!r}"
    return hits[0]


def test_module_export_manifest_writer_fallback_output_json_matches_config() -> None:
    for mod, script_rel, cfg_rel, block_key in _MANIFEST_WRITERS:
        script = _ROOT / script_rel
        fallback = _block_fallback_export_manifest_path(script, mod)
        doc = yaml.safe_load((_ROOT / cfg_rel).read_text(encoding="utf-8"))
        yaml_out = str((doc.get(block_key) or {}).get("output_json", "") or "").strip().replace("\\", "/")
        assert yaml_out, f"{cfg_rel} missing {block_key}.output_json"
        assert fallback == yaml_out, f"{script_rel} code fallback {fallback!r} != yaml {yaml_out!r}"


def test_pipeline_results_index_writer_fallback_output_json_matches_config() -> None:
    text = (_ROOT / "scripts/write_pipeline_results_index.py").read_text(encoding="utf-8")
    m = re.search(r'cfg\.get\("output_json",\s*"([^"]+)"\)', text)
    assert m, "write_pipeline_results_index.py missing cfg.get output_json fallback"
    fallback = m.group(1).replace("\\", "/")
    doc = yaml.safe_load((_ROOT / "config/pipeline_inventory.yaml").read_text(encoding="utf-8"))
    yaml_out = str((doc.get("pipeline_results_index") or {}).get("output_json", "") or "").strip().replace(
        "\\", "/"
    )
    assert yaml_out
    assert fallback == yaml_out, (
        f"write_pipeline_results_index fallback {fallback!r} != pipeline_inventory.yaml {yaml_out!r}"
    )
