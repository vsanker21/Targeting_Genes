"""AST extract of _ARTIFACTS relative paths from scripts/write_module3_export_manifest.py."""

from __future__ import annotations

import ast
from pathlib import Path


def _artifacts_list_ast(script_path: Path) -> ast.List | None:
    mod = ast.parse(script_path.read_text(encoding="utf-8"))
    for node in mod.body:
        val = None
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "_ARTIFACTS":
                    val = node.value
                    break
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "_ARTIFACTS" and node.value is not None:
                val = node.value
        if val is not None and isinstance(val, ast.List):
            return val
    return None


def artifact_rel_paths_from_write_module3_script(script_path: Path) -> set[str]:
    val = _artifacts_list_ast(script_path)
    if val is None:
        raise RuntimeError("parsed zero paths from _ARTIFACTS (AST shape changed?)")
    out: set[str] = set()
    for el in val.elts:
        if isinstance(el, ast.Tuple) and el.elts:
            fst = el.elts[0]
            if isinstance(fst, ast.Constant) and isinstance(fst.value, str):
                out.add(fst.value.replace("\\", "/"))
    if not out:
        raise RuntimeError("parsed zero paths from _ARTIFACTS (AST shape changed?)")
    return out


def artifact_rel_paths_in_order_from_write_module3_script(script_path: Path) -> list[str]:
    """Same paths as _ARTIFACTS first tuple elements, list order preserved (for duplicate detection)."""
    val = _artifacts_list_ast(script_path)
    if val is None:
        raise RuntimeError("missing _ARTIFACTS list (AST shape changed?)")
    out: list[str] = []
    for el in val.elts:
        if isinstance(el, ast.Tuple) and el.elts:
            fst = el.elts[0]
            if isinstance(fst, ast.Constant) and isinstance(fst.value, str):
                out.append(fst.value.replace("\\", "/"))
    if not out:
        raise RuntimeError("parsed zero paths from _ARTIFACTS (AST shape changed?)")
    return out


def artifact_tags_from_write_module3_script(script_path: Path) -> list[str]:
    val = _artifacts_list_ast(script_path)
    if val is None:
        raise RuntimeError("missing _ARTIFACTS list (AST shape changed?)")
    tags: list[str] = []
    for el in val.elts:
        if isinstance(el, ast.Tuple) and len(el.elts) >= 2:
            snd = el.elts[1]
            if isinstance(snd, ast.Constant) and isinstance(snd.value, str):
                tags.append(snd.value)
    if not tags:
        raise RuntimeError("parsed zero tags from _ARTIFACTS (AST shape changed?)")
    return tags
