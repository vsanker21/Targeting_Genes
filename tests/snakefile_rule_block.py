"""Slice a Snakemake Snakefile from `rule name:` through the next top-level `rule `."""

from __future__ import annotations


def rule_block(snakefile_text: str, name: str) -> str:
    i = snakefile_text.find(f"rule {name}:")
    assert i >= 0, f"missing rule {name}"
    j = snakefile_text.find("\nrule ", i + 1)
    return snakefile_text[i:] if j < 0 else snakefile_text[i:j]
