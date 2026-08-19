"""
normalizer.py
-------------
Groups near-duplicate category values (e.g. "Online", "online ", "on-line")
into a single canonical label per column, before the file reaches the rest
of the cleaning pipeline. Without this step, "Online" and "online" would be
counted as two different segments in every downstream chart and KPI.

Two-stage approach:
  1. Deterministic normalization (case, whitespace, separators) — handles
     the vast majority of real-world messiness safely and predictably.
     "on-line", "Online ", "ON_LINE" all reduce to the same key.
  2. Optional fuzzy clustering (stdlib difflib, no extra dependency) for
     near-duplicates that survive stage 1 — typos, small spelling
     variations. Clusters values whose similarity ratio exceeds a
     threshold, using union-find, then maps each cluster to its most
     frequent original spelling. Skipped for very short strings (<4 chars)
     to avoid falsely merging distinct short codes (e.g. "US" vs "UK").

Every merge is recorded in a NormalizationReport so nothing changes
silently — the report can be shown to the user before/after cleaning.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import pandas as pd

MIN_LENGTH_FOR_FUZZY = 4  # shorter strings only merge on exact (stage 1) match


def _basic_key(value: str) -> str:
    """
    Deterministic normalization key: lowercase, separators (-, _, /) turned
    into spaces, whitespace collapsed and trimmed. Two values that produce
    the same key are considered identical.
    """
    s = str(value).strip().lower()
    s = re.sub(r"[-_/]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


@dataclass
class NormalizationReport:
    column: str
    groups: list[dict] = field(default_factory=list)  # [{canonical, members: [(value, count), ...]}]

    @property
    def changed_count(self) -> int:
        return sum(1 for g in self.groups if len(g["members"]) > 1)

    def summary(self) -> str:
        lines = [f"Column '{self.column}': {self.changed_count} group(s) merged."]
        for g in self.groups:
            if len(g["members"]) > 1:
                members_str = ", ".join(f"'{v}' ({c})" for v, c in g["members"])
                lines.append(f"  -> '{g['canonical']}'  <=  {members_str}")
        return "\n".join(lines)


def _union_find_clusters(keys: list[str], threshold: float) -> dict[str, int]:
    """
    Clusters normalized keys whose pairwise similarity exceeds `threshold`
    using union-find. Pairs where either key is shorter than
    MIN_LENGTH_FOR_FUZZY are never merged here — short strings produce
    unstable similarity ratios and risk merging genuinely distinct values
    (e.g. country codes "US" / "UK"). O(n^2) comparisons, which is fine
    for the realistic number of distinct category values in a sales file.
    """
    parent = {k: k for k in keys}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            k1, k2 = keys[i], keys[j]
            if min(len(k1), len(k2)) < MIN_LENGTH_FOR_FUZZY:
                continue
            if SequenceMatcher(None, k1, k2).ratio() >= threshold:
                union(k1, k2)

    roots = {k: find(k) for k in keys}
    unique_roots = {r: idx for idx, r in enumerate(sorted(set(roots.values())))}
    return {k: unique_roots[r] for k, r in roots.items()}


def build_canonical_mapping(
    series: pd.Series, fuzzy: bool = True, fuzzy_threshold: float = 0.88
) -> tuple[dict, NormalizationReport]:
    """
    Analyzes a categorical column and builds a {raw_value: canonical_value}
    mapping, plus a human-readable report of what got merged.

    The canonical label chosen per group is the most frequent original
    (raw) spelling in that group — the tool doesn't invent new labels, it
    picks the one the data already agrees on most.
    """
    raw_values = series.dropna().astype(str)
    counts = Counter(raw_values)

    # Stage 1: group raw values by their basic normalization key
    key_to_raws: dict[str, Counter] = {}
    for raw, cnt in counts.items():
        key = _basic_key(raw)
        key_to_raws.setdefault(key, Counter())[raw] += cnt

    distinct_keys = list(key_to_raws.keys())

    # Stage 2: optionally cluster similar keys further
    if fuzzy and len(distinct_keys) > 1:
        key_cluster = _union_find_clusters(distinct_keys, fuzzy_threshold)
    else:
        key_cluster = {k: i for i, k in enumerate(distinct_keys)}

    cluster_to_keys: dict[int, list[str]] = {}
    for k, cid in key_cluster.items():
        cluster_to_keys.setdefault(cid, []).append(k)

    mapping: dict[str, str] = {}
    report = NormalizationReport(column=str(series.name))

    for keys_in_cluster in cluster_to_keys.values():
        merged_counts: Counter = Counter()
        for k in keys_in_cluster:
            merged_counts.update(key_to_raws[k])

        canonical = merged_counts.most_common(1)[0][0]
        members = sorted(merged_counts.items(), key=lambda x: -x[1])

        for raw in merged_counts:
            mapping[raw] = canonical

        report.groups.append({"canonical": canonical, "members": members})

    report.groups.sort(key=lambda g: -sum(c for _, c in g["members"]))
    return mapping, report


def normalize_column(
    df: pd.DataFrame, column: str, fuzzy: bool = True, fuzzy_threshold: float = 0.88
) -> tuple[pd.DataFrame, NormalizationReport]:
    """Applies the canonical mapping to one column, returns the updated frame + report."""
    mapping, report = build_canonical_mapping(df[column], fuzzy=fuzzy, fuzzy_threshold=fuzzy_threshold)
    df = df.copy()
    df[column] = df[column].astype(str).map(lambda v: mapping.get(v, v))
    return df, report


CATEGORICAL_COLUMNS = ["Product", "Category", "Country", "Customer_Segment"]


def normalize_categorical_columns(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    fuzzy: bool = True,
    fuzzy_threshold: float = 0.88,
) -> tuple[pd.DataFrame, list[NormalizationReport]]:
    """
    Runs normalize_column across all categorical columns (Product, Category,
    Country, Customer_Segment by default). Returns the cleaned frame and one
    report per column, so the caller (e.g. Streamlit) can show the user
    exactly what got merged before trusting the numbers.
    """
    columns = columns or CATEGORICAL_COLUMNS
    reports = []
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            continue
        out, report = normalize_column(out, col, fuzzy=fuzzy, fuzzy_threshold=fuzzy_threshold)
        reports.append(report)
    return out, reports
