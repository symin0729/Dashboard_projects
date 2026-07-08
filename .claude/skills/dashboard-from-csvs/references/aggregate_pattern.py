"""
Generic pattern for aggregate.py — the offline script that joins two CSVs
and prints one JSON blob for a dashboard's `const DATA = {...}` line.

This is a TEMPLATE, not a drop-in script. Replace every ALL_CAPS placeholder
and every column name with the real ones from the actual CSVs before running.
The shape (order of steps, what each block computes) is the part to keep —
see SKILL.md Step 2 for why each step exists.

Usage:
    python aggregate.py file_a.csv file_b.csv > dashboard_data.json
"""
import sys
import json
import pandas as pd

TOP_N = 30  # how many entities to include in the top-N table


def normalize_category(name):
    """
    Collapse formatting variants of the same category into one canonical form.
    e.g. product SKU suffixes, casing differences, punctuation differences.
    Return the value unchanged if there's nothing to normalize for this dataset.
    """
    if pd.isna(name):
        return name
    return str(name).strip()


def main(a_path, b_path):
    a = pd.read_csv(a_path)
    b = pd.read_csv(b_path)

    # --- normalize whatever field you'll group/join on ---
    # Example: unify casing/whitespace variants of a manufacturer, company, or category name.
    # a["CATEGORY_COL_norm"] = a["CATEGORY_COL"].str.strip()
    # a.loc[a["CATEGORY_COL_norm"].str.upper() == "SOME VARIANT", "CATEGORY_COL_norm"] = "Canonical Form"

    # --- join-key overlap ---
    overlap_keys = set(a["JOIN_KEY_COL_A"]) & set(b["JOIN_KEY_COL_B"])

    # --- overall stats block: feeds the top-level stat cards ---
    overall = {
        "a_rows": int(len(a)),
        "a_unique_keys": int(a["JOIN_KEY_COL_A"].nunique()),
        "a_total_METRIC": round(float(a["METRIC_COL_A"].sum()), 2),
        "b_rows": int(len(b)),
        "b_unique_keys": int(b["JOIN_KEY_COL_B"].nunique()),
        "b_total_METRIC": round(float(b["METRIC_COL_B"].sum()), 2),
        "overlap_keys": len(overlap_keys),
    }

    # --- per-category comparison ---
    cat_a = (
        a.groupby("CATEGORY_COL")
        .agg(total_METRIC=("METRIC_COL_A", "sum"), count=("METRIC_COL_A", "count"))
        .reset_index()
        .rename(columns={"CATEGORY_COL": "category"})
    )
    cat_b = (
        b.groupby("CATEGORY_COL")
        .agg(total_OUTCOME=("METRIC_COL_B", "sum"))
        .reset_index()
        .rename(columns={"CATEGORY_COL": "category"})
    )

    merged = cat_a.merge(cat_b, on="category", how="left")  # keep unmatched categories, don't inner-join them away

    # If the two metrics differ by an order of magnitude or more, standardize
    # instead of taking a raw ratio (see references/design_tradeoffs.md).
    have_both = merged.dropna(subset=["total_OUTCOME"])
    if len(have_both):
        avg_ratio = have_both["total_OUTCOME"].sum() / have_both["total_METRIC"].sum()
        merged["index_vs_avg"] = (merged["total_OUTCOME"] / merged["total_METRIC"]) / avg_ratio
    else:
        merged["index_vs_avg"] = None

    merged = merged.sort_values("total_METRIC", ascending=False).round(2)
    categories = json.loads(merged.to_json(orient="records"))

    # --- top-N entities (not categories) ---
    entities = (
        a.groupby(["JOIN_KEY_COL_A", "NAME_COL", "OTHER_LABEL_COLS"])
        .agg(total_METRIC=("METRIC_COL_A", "sum"), count=("METRIC_COL_A", "count"))
        .reset_index()
    )
    entities["has_match_in_b"] = entities["JOIN_KEY_COL_A"].isin(overlap_keys)
    b_metric_by_key = b.groupby("JOIN_KEY_COL_B")["METRIC_COL_B"].sum()
    entities["matched_METRIC"] = entities["JOIN_KEY_COL_A"].map(b_metric_by_key).round(2)

    top = entities.sort_values("total_METRIC", ascending=False).head(TOP_N).round(2)
    top_list = json.loads(top.to_json(orient="records"))

    out = {"overall": overall, "categories": categories, "top_n": top_list}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python aggregate.py <file_a.csv> <file_b.csv>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
