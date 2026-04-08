"""Snakefile + pipeline_inventory core: writers, run blocks, manifest_paths, provenance, rule all."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from snakefile_rule_block import rule_block
from snakefile_text_cache import snakefile_text

_ROOT = Path(__file__).resolve().parents[1]
_INV = _ROOT / "config" / "pipeline_inventory.yaml"
_SNAKE = snakefile_text()


def test_export_manifest_rules_include_writer_and_shared_optional_helper() -> None:
    for n in (3, 4, 5, 6, 7):
        blk = rule_block(_SNAKE, f"m{n}_export_manifest")
        assert f"write_module{n}_export_manifest.py" in blk, blk[:400]
        assert "manifest_optional.py" in blk, blk[:400]


def test_export_manifest_and_pipeline_index_snakemake_rules_defined_once() -> None:
    for name in (
        "m3_export_manifest",
        "m4_export_manifest",
        "m5_export_manifest",
        "m6_export_manifest",
        "m7_export_manifest",
        "pipeline_results_index",
    ):
        n = _SNAKE.count(f"rule {name}:")
        assert n == 1, f"expected exactly one `rule {name}:` in Snakefile, found {n}"


def test_export_manifest_rules_writer_script_binds_expected_path() -> None:
    """Named writer= input must use the same scripts/write_module*_export_manifest.py path Snakemake runs."""
    for n in (3, 4, 5, 6, 7):
        script = _ROOT / "scripts" / f"write_module{n}_export_manifest.py"
        assert script.is_file(), f"missing {script}"
        blk = rule_block(_SNAKE, f"m{n}_export_manifest")
        needle = f'writer=str(_ROOT / "scripts" / "write_module{n}_export_manifest.py")'
        assert needle in blk, f"m{n}_export_manifest missing input {needle}"


def test_export_manifest_rules_manifest_optional_script_input() -> None:
    """Each export-manifest rule must name manifest_optional.py (shared optional_tags helper)."""
    opt = _ROOT / "scripts" / "manifest_optional.py"
    assert opt.is_file(), f"missing {opt}"
    needle = 'manifest_opt=str(_ROOT / "scripts" / "manifest_optional.py")'
    for n in (3, 4, 5, 6, 7):
        blk = rule_block(_SNAKE, f"m{n}_export_manifest")
        assert needle in blk, f"m{n}_export_manifest missing input {needle}"


def test_export_manifest_rules_bind_config_inputs_expected_by_writers() -> None:
    """Snakemake must pass the same config YAML each write_module*_export_manifest.py loads."""
    cases: tuple[tuple[str, str], ...] = (
        ("m3_export_manifest", "module3_inputs.yaml"),
        ("m4_export_manifest", "module2_integration.yaml"),
        ("m5_export_manifest", "module5_inputs.yaml"),
        ("m6_export_manifest", "module6_inputs.yaml"),
        ("m7_export_manifest", "module7_inputs.yaml"),
    )
    for rule_name, cfg_name in cases:
        cfg_path = _ROOT / "config" / cfg_name
        assert cfg_path.is_file(), f"missing {cfg_path}"
        blk = rule_block(_SNAKE, rule_name)
        needle = f'str(_ROOT / "config" / "{cfg_name}")'
        assert needle in blk, f"{rule_name} must include input {needle} (writer reads this path)"


def test_pipeline_results_index_inv_binds_pipeline_inventory_yaml() -> None:
    inv = _ROOT / "config" / "pipeline_inventory.yaml"
    assert inv.is_file(), f"missing {inv}"
    blk = rule_block(_SNAKE, "pipeline_results_index")
    assert 'inv=str(_ROOT / "config" / "pipeline_inventory.yaml")' in blk, (
        "pipeline_results_index must pass pipeline_inventory.yaml (write_pipeline_results_index.py reads it)"
    )


def test_pipeline_results_index_idx_script_binds_writer() -> None:
    script = _ROOT / "scripts" / "write_pipeline_results_index.py"
    assert script.is_file(), f"missing {script}"
    blk = rule_block(_SNAKE, "pipeline_results_index")
    assert 'idx_script=str(_ROOT / "scripts" / "write_pipeline_results_index.py")' in blk, (
        "pipeline_results_index must name idx_script path expected by Snakemake DAG"
    )


def test_export_manifest_rules_run_invokes_writer_script_path() -> None:
    """run: subprocess must execute the same script as the writer= input (not a stale path)."""
    for n in (3, 4, 5, 6, 7):
        blk = rule_block(_SNAKE, f"m{n}_export_manifest")
        run = blk.split("run:", 1)[-1]
        path = f'str(_ROOT / "scripts" / "write_module{n}_export_manifest.py")'
        assert path in run, f"m{n}_export_manifest run block must invoke {path}"


def test_export_manifest_and_pipeline_index_run_use_sys_executable_and_check_call() -> None:
    """Run blocks should invoke the current Python (Snakemake env) via subprocess.check_call."""
    for name in (
        "m3_export_manifest",
        "m4_export_manifest",
        "m5_export_manifest",
        "m6_export_manifest",
        "m7_export_manifest",
        "pipeline_results_index",
    ):
        blk = rule_block(_SNAKE, name)
        run = blk.split("run:", 1)[-1]
        assert "subprocess.check_call" in run, f"{name} run must use subprocess.check_call"
        assert "sys.executable" in run, f"{name} run must pass sys.executable as argv0"


def test_export_manifest_and_pipeline_index_run_avoid_shell_true() -> None:
    """Prefer subprocess argv lists over shell=True for manifest/index writers."""
    for name in (
        "m3_export_manifest",
        "m4_export_manifest",
        "m5_export_manifest",
        "m6_export_manifest",
        "m7_export_manifest",
        "pipeline_results_index",
    ):
        run = rule_block(_SNAKE, name).split("run:", 1)[-1]
        assert "shell=True" not in run, f"{name} run must not use shell=True"


def test_export_manifest_rules_run_uses_repo_root_cwd() -> None:
    for n in (3, 4, 5, 6, 7):
        blk = rule_block(_SNAKE, f"m{n}_export_manifest")
        run = blk.split("run:", 1)[-1]
        assert "cwd=str(_ROOT)" in run, f"m{n}_export_manifest run must cwd=str(_ROOT)"


def test_export_manifest_m4567_run_passes_glioma_target_data_root_env() -> None:
    """M4–M7 writers resolve data_root-relative paths; Snakemake must pass GLIOMA_TARGET_DATA_ROOT."""
    for n in (4, 5, 6, 7):
        blk = rule_block(_SNAKE, f"m{n}_export_manifest")
        run = blk.split("run:", 1)[-1]
        assert "GLIOMA_TARGET_DATA_ROOT" in run, f"m{n}_export_manifest run missing GLIOMA_TARGET_DATA_ROOT"
        assert "env=env" in run, f"m{n}_export_manifest run must pass env= to check_call"


def test_m3_export_manifest_run_does_not_pass_data_root_env() -> None:
    """M3 manifest is curated under results/; avoid implying a data_root requirement in the rule run block."""
    blk = rule_block(_SNAKE, "m3_export_manifest")
    run = blk.split("run:", 1)[-1]
    assert "GLIOMA_TARGET_DATA_ROOT" not in run


def test_pipeline_results_index_run_invokes_idx_script_path() -> None:
    blk = rule_block(_SNAKE, "pipeline_results_index")
    run = blk.split("run:", 1)[-1]
    path = 'str(_ROOT / "scripts" / "write_pipeline_results_index.py")'
    assert path in run, f"pipeline_results_index run block must invoke {path}"


def test_pipeline_results_index_run_uses_repo_root_cwd() -> None:
    blk = rule_block(_SNAKE, "pipeline_results_index")
    run = blk.split("run:", 1)[-1]
    assert "cwd=str(_ROOT)" in run, "pipeline_results_index run must cwd=str(_ROOT)"


def test_pipeline_results_index_includes_index_script() -> None:
    blk = rule_block(_SNAKE, "pipeline_results_index")
    assert "write_pipeline_results_index.py" in blk
    assert "pipeline_inventory.yaml" in blk
    assert 'm3="results/module3/module3_export_manifest.json"' in blk
    assert 'm4="results/module4/module4_export_manifest.json"' in blk
    assert 'm5="results/module5/module5_export_manifest.json"' in blk
    assert 'm6="results/module6/module6_export_manifest.json"' in blk
    assert 'm7="results/module7/module7_export_manifest.json"' in blk


def _pipeline_inventory_provenance_rel_paths() -> list[str]:
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    block = inv_doc.get("pipeline_results_index") or {}
    out: list[str] = []
    for item in block.get("provenance_paths") or []:
        if not isinstance(item, dict):
            continue
        rel = str(item.get("path", "") or "").strip()
        if rel:
            out.append(rel.replace("\\", "/"))
    return out


def test_pipeline_inventory_manifest_paths_match_pipeline_results_index_rule() -> None:
    """config/pipeline_inventory.yaml manifest_paths must match named manifest inputs on the Snakemake rule."""
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    block = inv_doc.get("pipeline_results_index") or {}
    yaml_paths = {str(p).replace("\\", "/") for p in (block.get("manifest_paths") or [])}
    blk = rule_block(_SNAKE, "pipeline_results_index")
    snake_paths = set(re.findall(r'm[3-7]="([^"]+)"', blk))
    snake_manifests = {p for p in snake_paths if p.endswith("_export_manifest.json")}
    assert yaml_paths == snake_manifests, (
        "pipeline_inventory manifest_paths must equal export_manifest.json inputs on "
        f"pipeline_results_index; yaml={sorted(yaml_paths)} snake={sorted(snake_manifests)}"
    )


def test_pipeline_inventory_manifest_paths_are_canonical_ordered_m3_through_m7() -> None:
    """Stable merge order in write_pipeline_results_index: one canonical path per module, ascending."""
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    paths = [
        str(p).replace("\\", "/")
        for p in (inv_doc.get("pipeline_results_index") or {}).get("manifest_paths") or []
    ]
    expected = [f"results/module{n}/module{n}_export_manifest.json" for n in (3, 4, 5, 6, 7)]
    assert paths == expected, (
        "pipeline_inventory manifest_paths must match canonical names in module order "
        f"(got {paths!r}, expected {expected!r})"
    )


def test_pipeline_inventory_manifest_paths_entries_are_strings() -> None:
    """manifest_paths must be YAML strings so writers do not receive ints or merged anchors."""
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    paths = (inv_doc.get("pipeline_results_index") or {}).get("manifest_paths") or []
    for i, p in enumerate(paths):
        assert isinstance(p, str) and p.strip(), (
            f"manifest_paths[{i}] must be a non-empty string (got {type(p).__name__}: {p!r})"
        )


def test_pipeline_inventory_manifest_paths_have_no_duplicates() -> None:
    """Each manifest must appear once; duplicates confuse DAG consumers and merge order."""
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    paths = (inv_doc.get("pipeline_results_index") or {}).get("manifest_paths") or []
    norm = [str(p).replace("\\", "/").strip() for p in paths]
    assert len(norm) == len(set(norm)), f"manifest_paths must not repeat paths (got {norm})"


def test_pipeline_inventory_merge_lists_are_yaml_lists() -> None:
    """Writer code indexes manifest_paths / optional_path_posix / provenance_paths as sequences."""
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    pri = inv_doc.get("pipeline_results_index") or {}
    for key in ("manifest_paths", "optional_path_posix", "provenance_paths"):
        val = pri.get(key)
        assert isinstance(val, list), (
            f"pipeline_results_index.{key} must be a YAML list (got {type(val).__name__}: {val!r})"
        )


def test_pipeline_inventory_optional_path_posix_entries_are_strings() -> None:
    """optional_path_posix must be path strings (same keys as manifest path_posix), not nested structures."""
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    raw = (inv_doc.get("pipeline_results_index") or {}).get("optional_path_posix") or []
    for i, x in enumerate(raw):
        assert isinstance(x, str) and x.strip(), (
            f"optional_path_posix[{i}] must be a non-empty string (got {type(x).__name__}: {x!r})"
        )


def test_pipeline_inventory_optional_path_posix_entries_are_repo_relative_posix() -> None:
    """optional_path_posix keys must be normal forward-slash paths (writer uses Path.as_posix)."""
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    raw = (inv_doc.get("pipeline_results_index") or {}).get("optional_path_posix") or []
    for x in raw:
        s = str(x).strip().replace("\\", "/")
        assert s, "optional_path_posix entry must be non-empty"
        assert "\\" not in str(x), f"use forward slashes in optional_path_posix: {x!r}"
        assert s == Path(s).as_posix(), f"normalize optional_path_posix as posix: {x!r}"


def test_pipeline_inventory_optional_path_posix_has_no_duplicates() -> None:
    """Duplicate optional keys are noisy and can mask typos; keep the list deduped."""
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    raw = (inv_doc.get("pipeline_results_index") or {}).get("optional_path_posix") or []
    norm = [Path(str(x).strip().replace("\\", "/")).as_posix() for x in raw]
    assert len(norm) == len(set(norm)), f"optional_path_posix must not repeat paths (got {norm})"


def test_pipeline_inventory_provenance_paths_in_pipeline_results_index_rule() -> None:
    """Every pipeline_inventory provenance_paths entry must be a named input (DAG edge) on the rule."""
    blk = rule_block(_SNAKE, "pipeline_results_index")
    missing = [p for p in _pipeline_inventory_provenance_rel_paths() if p not in blk]
    assert not missing, (
        "provenance_paths from pipeline_inventory.yaml missing from rule pipeline_results_index "
        f"(add named input so the index rebuilds when they change): {missing}"
    )


def test_pipeline_inventory_provenance_paths_modules_non_decreasing() -> None:
    """Keep provenance_paths ordered by module for predictable diffs and review."""
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    pri = inv_doc.get("pipeline_results_index") or {}
    mods: list[int] = []
    for item in pri.get("provenance_paths") or []:
        assert isinstance(item, dict), "provenance_paths entries must be mappings (see path_and_module_yaml_types)"
        mods.append(int(item.get("module", 0) or 0))
    assert mods == sorted(mods), (
        "pipeline_inventory provenance_paths should list entries in non-decreasing module order "
        f"(got {mods})"
    )


def test_pipeline_inventory_provenance_paths_path_and_module_yaml_types() -> None:
    """path must be str; module must be YAML int (quoted scalars become str and break typing)."""
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    pri = inv_doc.get("pipeline_results_index") or {}
    for i, item in enumerate(pri.get("provenance_paths") or []):
        assert isinstance(item, dict), (
            f"provenance_paths[{i}] must be a mapping (got {type(item).__name__})"
        )
        assert "path" in item and "module" in item, f"provenance_paths[{i}] must have path and module keys"
        raw_path = item.get("path")
        assert isinstance(raw_path, str) and raw_path.strip(), (
            f"provenance_paths[{i}].path must be a non-empty string "
            f"(got {type(raw_path).__name__}: {raw_path!r})"
        )
        mod = item.get("module")
        assert isinstance(mod, int), (
            f"provenance_paths[{i}].module must be an int (got {type(mod).__name__}: {mod!r}); "
            "use unquoted YAML integers"
        )
        assert 3 <= mod <= 7, f"provenance_paths[{i}].module must be in 3..7 (got {mod})"


def test_pipeline_inventory_provenance_paths_have_no_duplicate_paths() -> None:
    """Same provenance JSON must not be listed twice (writer would re-harvest redundantly)."""
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    pri = inv_doc.get("pipeline_results_index") or {}
    norm: list[str] = []
    for item in pri.get("provenance_paths") or []:
        assert isinstance(item, dict)
        norm.append(str(item.get("path", "")).replace("\\", "/").strip())
    assert len(norm) == len(set(norm)), f"provenance_paths must not repeat path (got {norm})"


def test_pipeline_inventory_provenance_module_matches_results_prefix() -> None:
    """Each provenance path must live under results/module{module}/ per its module: field."""
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    pri = inv_doc.get("pipeline_results_index") or {}
    rx = re.compile(r"^results/module(\d+)/")
    for item in pri.get("provenance_paths") or []:
        assert isinstance(item, dict), "provenance_paths entries must be mappings (see path_and_module_yaml_types)"
        path = str(item.get("path", "") or "").replace("\\", "/").strip()
        mod = int(item.get("module", 0) or 0)
        assert path, "provenance_paths entry missing path"
        assert mod > 0, f"provenance_paths entry missing module for {path!r}"
        m = rx.match(path)
        assert m, f"provenance path must start with results/moduleN/: {path!r}"
        path_mod = int(m.group(1))
        assert path_mod == mod, (
            f"path prefix is module {path_mod} but YAML module is {mod}: {path!r}"
        )


def test_pipeline_inventory_path_suffix_and_repo_relative_conventions() -> None:
    """Inventory paths stay under results/, use expected extensions, and avoid absolute/parent escapes."""
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    pri = inv_doc.get("pipeline_results_index") or {}

    def _no_escape(label: str, s: str) -> None:
        assert not s.startswith("/"), f"{label} must be repo-relative (no leading slash): {s!r}"
        segs = s.split("/")
        assert ".." not in segs, f"{label} must not contain parent-dir segments: {s!r}"

    out_json = str(pri.get("output_json", "") or "").strip().replace("\\", "/")
    assert out_json.startswith("results/"), f"output_json should live under results/: {out_json!r}"
    assert out_json.endswith(".json"), f"output_json should be JSON: {out_json!r}"
    _no_escape("output_json", out_json)

    for i, p in enumerate(pri.get("manifest_paths") or []):
        s = str(p).replace("\\", "/").strip()
        assert s.startswith("results/"), f"manifest_paths[{i}] should be under results/: {s!r}"
        assert s.endswith("_export_manifest.json"), (
            f"manifest_paths[{i}] should end with _export_manifest.json: {s!r}"
        )
        _no_escape(f"manifest_paths[{i}]", s)

    for i, item in enumerate(pri.get("provenance_paths") or []):
        assert isinstance(item, dict)
        path = str(item.get("path", "")).replace("\\", "/").strip()
        assert path.endswith(".json"), f"provenance_paths[{i}].path should be .json: {path!r}"
        _no_escape(f"provenance_paths[{i}].path", path)

    for i, x in enumerate(pri.get("optional_path_posix") or []):
        s = Path(str(x).strip().replace("\\", "/")).as_posix()
        _no_escape(f"optional_path_posix[{i}]", s)


def test_rule_all_includes_pipeline_inventory_manifest_paths_and_index_output() -> None:
    """Default `snakemake` target should build every manifest the index consumes plus the index JSON."""
    inv_doc = yaml.safe_load(_INV.read_text(encoding="utf-8"))
    pri = inv_doc.get("pipeline_results_index") or {}
    expected = [str(p).replace("\\", "/") for p in (pri.get("manifest_paths") or [])]
    out_json = str(pri.get("output_json", "") or "").strip().replace("\\", "/")
    assert out_json
    all_blk = rule_block(_SNAKE, "all")
    missing = [p for p in [*expected, out_json] if p not in all_blk]
    assert not missing, (
        "rule all must list pipeline_inventory manifest_paths and pipeline_results_index.output_json; "
        f"missing: {missing}"
    )


def test_rule_all_quoted_repo_output_paths_are_unique() -> None:
    """Duplicate `rule all` inputs waste scheduling work and usually mean a bad merge."""
    blk = rule_block(_SNAKE, "all")
    paths = re.findall(r'"((?:results|references)/[^"]+)"', blk)
    assert paths, "expected quoted results/ or references/ paths in rule all"
    dupes = sorted({p for p in paths if paths.count(p) > 1})
    assert not dupes, f"rule all must not repeat the same path (duplicates: {dupes})"


def test_rule_all_optional_inputs_m7_deliverables_env() -> None:
    """Bundle env pulls m7_glioma_target_deliverables; avoids duplicating VIZ/DOCX paths when set."""
    assert "GLIOMA_TARGET_INCLUDE_M7_DELIVERABLES" in _SNAKE
    i = _SNAKE.find("def _rule_all_optional_inputs")
    assert i >= 0
    j = _SNAKE.find("\n\nrule all:", i)
    assert j > i
    snip = _SNAKE[i:j]
    assert "glioma_target_deliverables.flag" in snip
    assert "GLIOMA_TARGET_INCLUDE_M7_VIZ" in snip
    assert "GLIOMA_TARGET_INCLUDE_M7_DOCX" in snip


def _named_input_keys_before_output(rule_name: str) -> list[str]:
    blk = rule_block(_SNAKE, rule_name)
    assert "input:" in blk, f"{rule_name}: expected input section"
    head = blk.split("output:", 1)[0]
    return re.findall(r"(?m)^\s+([a-zA-Z_]\w*)\s*=", head)


def _anonymous_quoted_output_paths(rule_name: str) -> list[str]:
    blk = rule_block(_SNAKE, rule_name)
    assert "output:" in blk, f"{rule_name}: expected output section"
    rest = blk.split("output:", 1)[1]
    sec = rest.split("run:", 1)[0]
    return re.findall(r'(?m)^\s+"([^"]+)"\s*,?\s*$', sec)


def test_export_manifest_and_pipeline_index_named_inputs_unique() -> None:
    """Snakemake rejects duplicate input names; catch copy-paste mistakes early."""
    for rule_name in (
        "pipeline_results_index",
        "m3_export_manifest",
        "m4_export_manifest",
        "m5_export_manifest",
        "m6_export_manifest",
        "m7_export_manifest",
    ):
        names = _named_input_keys_before_output(rule_name)
        assert names, f"{rule_name}: expected at least one named input"
        dupes = sorted({n for n in names if names.count(n) > 1})
        assert not dupes, f"{rule_name}: duplicate input parameter name(s): {dupes}"


def test_export_manifest_and_pipeline_index_single_anonymous_json_output() -> None:
    """Writers emit one JSON file; keep a single quoted output path (no named multi-output drift)."""
    for rule_name in (
        "pipeline_results_index",
        "m3_export_manifest",
        "m4_export_manifest",
        "m5_export_manifest",
        "m6_export_manifest",
        "m7_export_manifest",
    ):
        paths = _anonymous_quoted_output_paths(rule_name)
        assert len(paths) == 1, (
            f"{rule_name}: expected exactly one anonymous quoted output path, got {paths!r}"
        )
        out = paths[0].replace("\\", "/")
        assert out.endswith(".json"), f"{rule_name}: output must be .json (got {out!r})"
