"""
지급-처방 상관관계 대시보드용 데이터 집계 스크립트.

Supabase(Postgres)의 open_payments, part_d_prescriber 테이블을 읽어
제품별 요약과 고액 지급 의사 Top N을 JSON으로 출력한다.
출력된 JSON은 update_dashboard.py가 index.html의 `const DATA = {...}` 블록에 삽입한다.

연결 문자열은 환경변수 SUPABASE_DB_URL에서 읽는다.

사용법:
    SUPABASE_DB_URL=postgresql://... python aggregate.py > dashboard_data.json
"""
import os
import sys
import json
import pandas as pd
from sqlalchemy import create_engine

TOP_N = 30


def base_brand(name):
    if pd.isna(name):
        return name
    name = str(name)
    if name.startswith("Cosentyx"):
        return "COSENTYX"
    if name.startswith("Entresto"):
        return "ENTRESTO"
    if name.startswith("Lucentis"):
        return "LUCENTIS"
    return name.upper()


def build_dashboard_data(op, pdd):
    # 제조사명 대소문자 정규화 (콤마 포함 정식 법인명은 그대로 유지)
    op["mfr_norm"] = op["payment_manufacturer"].str.strip()
    op.loc[
        op["mfr_norm"].str.upper() == "NOVARTIS PHARMACEUTICALS CORPORATION",
        "mfr_norm",
    ] = "Novartis Pharmaceuticals Corporation"

    pdd["base_brand"] = pdd["Brnd_Name"].apply(base_brand)

    overlap_npi = set(op["covered_recipient_npi"]) & set(pdd["Prscrbr_NPI"])

    overall = {
        "op_rows": int(len(op)),
        "op_unique_npi": int(op["covered_recipient_npi"].nunique()),
        "op_total_payment": round(float(op["payment_amount_usd"].sum()), 2),
        "op_ca_rows": int((op["recipient_state"] == "CA").sum()),
        "op_food_bev_rows": int((op["payment_nature"] == "Food and Beverage").sum()),
        "op_n_products": int(op["product_1"].nunique()),
        "op_n_specialty": int(op["recipient_specialty"].nunique()),
        "pd_rows": int(len(pdd)),
        "pd_unique_npi": int(pdd["Prscrbr_NPI"].nunique()),
        "pd_total_drug_cost": round(float(pdd["Tot_Drug_Cst"].sum()), 2),
        "pd_suppressed_rows": int(pdd["GE65_Sprsn_Flag"].isin(["#", "*"]).sum()),
        "overlap_npi": len(overlap_npi),
        "generated": "CMS Open Payments & Part D Prescriber Public Use File",
    }

    prod_pay = (
        op.groupby("product_1")
        .agg(
            total_payment=("payment_amount_usd", "sum"),
            payment_count=("payment_amount_usd", "count"),
            unique_physicians=("covered_recipient_npi", pd.Series.nunique),
        )
        .reset_index()
        .rename(columns={"product_1": "product"})
    )

    prod_presc = (
        pdd.groupby("base_brand")
        .agg(
            total_drug_cost=("Tot_Drug_Cst", "sum"),
            total_claims=("Tot_Clms", "sum"),
            unique_prescribers=("Prscrbr_NPI", pd.Series.nunique),
        )
        .reset_index()
        .rename(columns={"base_brand": "product"})
    )

    merged = prod_pay.merge(prod_presc, on="product", how="left")
    have_both = merged.dropna(subset=["total_drug_cost"])
    avg_ratio = have_both["total_drug_cost"].sum() / have_both["total_payment"].sum()
    merged["index_vs_avg"] = (
        merged["total_drug_cost"] / merged["total_payment"]
    ) / avg_ratio
    merged = merged.sort_values("total_payment", ascending=False).round(2)
    products = json.loads(merged.to_json(orient="records"))

    phys = (
        op.groupby(
            [
                "covered_recipient_npi",
                "recipient_first_name",
                "recipient_last_name",
                "recipient_city",
                "recipient_state",
                "recipient_specialty",
            ]
        )
        .agg(
            total_payment=("payment_amount_usd", "sum"),
            payment_count=("payment_amount_usd", "count"),
        )
        .reset_index()
    )
    phys["has_prescribing_data"] = phys["covered_recipient_npi"].isin(overlap_npi)
    presc_by_npi = pdd.groupby("Prscrbr_NPI")["Tot_Drug_Cst"].sum()
    phys["total_drug_cost"] = phys["covered_recipient_npi"].map(presc_by_npi).round(2)
    prods_by_npi = op.groupby("covered_recipient_npi")["product_1"].apply(
        lambda s: sorted(set(x for x in s.dropna()))
    )
    phys["products"] = phys["covered_recipient_npi"].map(prods_by_npi)
    top = phys.sort_values("total_payment", ascending=False).head(TOP_N).round(2)
    # NPI는 식별자이므로 정수로 출력한다(소수점 표기 방지).
    top["covered_recipient_npi"] = top["covered_recipient_npi"].astype("Int64")
    top_list = json.loads(top.to_json(orient="records"))

    return {"overall": overall, "products": products, "top_physicians": top_list}


def load_from_supabase():
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("error: SUPABASE_DB_URL 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    engine = create_engine(db_url)
    op = pd.read_sql_table("open_payments", engine)
    pdd = pd.read_sql_table("part_d_prescriber", engine)
    return op, pdd


def main():
    op, pdd = load_from_supabase()
    out = build_dashboard_data(op, pdd)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
