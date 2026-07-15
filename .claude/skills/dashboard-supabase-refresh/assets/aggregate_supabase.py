"""
집계 스크립트를 CSV 대신 Supabase에서 읽도록 바꾸는 형태(shape) 예시.

핵심: 집계 로직(build_dashboard_data)은 CSV 시절과 100% 동일하게 두고, 데이터를
"어디서 읽는지"만 바꾼다. 아래처럼 세 부분으로 나누면 update_dashboard.py가
집계 함수를 그대로 재사용할 수 있다(서브프로세스/파싱 불필요).

  1) build_dashboard_data(a, b): 순수 함수 — 두 DataFrame → 대시보드 JSON dict
  2) load_from_supabase():        Supabase에서 두 DataFrame을 읽어옴
  3) main():                      위 둘을 이어 stdout으로 JSON 출력

--- 바꾸기 전 (CSV) ---
    def main(a_path, b_path):
        a = pd.read_csv(a_path)
        b = pd.read_csv(b_path)
        ...집계...
        print(json.dumps(out, ensure_ascii=False))

--- 바꾼 후 (Supabase) ---  아래가 그 형태다.
"""
import os
import sys
import json

import pandas as pd
from sqlalchemy import create_engine

TABLE_A = "table_a"
TABLE_B = "table_b"


def build_dashboard_data(a, b):
    # ▼▼▼ 여기에 기존 CSV 버전의 집계 로직을 '그대로' 옮긴다 ▼▼▼
    #   - 카테고리 정규화, 조인 키 overlap, overall 통계,
    #     카테고리별 표준화 지수, top-N 목록 등
    #   - 식별자를 출력에 담는다면 직렬화 직전에 Int64로 캐스팅해 정수로 내보낸다:
    #         top["entity_id"] = top["entity_id"].astype("Int64")
    out = {"overall": {}, "categories": [], "top_n": []}
    # ▲▲▲ 집계 로직 끝 ▲▲▲
    return out


def load_from_supabase():
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("error: SUPABASE_DB_URL 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)
    engine = create_engine(db_url)
    a = pd.read_sql_table(TABLE_A, engine)
    b = pd.read_sql_table(TABLE_B, engine)
    return a, b


def main():
    a, b = load_from_supabase()
    out = build_dashboard_data(a, b)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
