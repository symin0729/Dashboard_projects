"""
CSV 컬럼 타입 진단 — schema.sql의 컬럼 타입을 결정하기 위한 도구.

각 컬럼의 dtype, null 개수, 그리고 "숫자로 변환 불가한 값"의 개수와 예시를 출력한다.
숫자 컬럼처럼 보여도 '#'/'*'(CMS 개인정보 억제 마커 등)가 섞여 있으면 여기서 드러나며,
그런 컬럼은 schema.sql에서 반드시 text로 선언해야 한다.

사용법:
    python inspect_csv.py <csv1> [<csv2> ...]
"""
import sys
import pandas as pd


def inspect(path):
    print(f"\n===== {path} =====")
    df = pd.read_csv(path)
    print(f"rows={len(df)}")
    for col in df.columns:
        s = df[col]
        dtype = str(s.dtype)
        n_null = int(s.isna().sum())
        coerced = pd.to_numeric(s, errors="coerce")
        n_nonnum = int((coerced.isna() & s.notna()).sum())
        note = ""
        if n_nonnum > 0:
            bad = s[coerced.isna() & s.notna()].astype(str).unique()[:5]
            note = " | 비숫자 예시: " + ", ".join(repr(x) for x in bad)
        print(f"  {col:34s} dtype={dtype:9s} nulls={n_null:6d} nonnumeric={n_nonnum:6d}{note}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python inspect_csv.py <csv1> [<csv2> ...]", file=sys.stderr)
        sys.exit(1)
    for p in sys.argv[1:]:
        inspect(p)
