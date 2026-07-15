"""
CSV 파일을 Supabase(Postgres) 테이블에 적재한다.

supabase/schema.sql로 미리 만든 테이블에 TRUNCATE 후 append하는 방식이라,
명시적으로 정의한 컬럼 타입이 보존된다. 따라서 실행 전에 apply_schema.py(또는
SQL Editor)로 스키마를 먼저 적용해야 한다.

연결 문자열은 환경변수 SUPABASE_DB_URL에서 읽는다. 대량 적재에는 세션 풀러
(포트 5432) 연결 문자열을 권장한다 — 트랜잭션 풀러(6543)는 대량 insert에서
prepared statement 관련 문제가 생길 수 있다.

사용법:
    SUPABASE_DB_URL=postgresql://...:5432/postgres python load_csv_to_supabase.py <csv> <table>
"""
import os
import sys

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

# 결측 때문에 float로 읽히는 식별자 컬럼을 bigint로 넣기 위해 nullable 정수형으로
# 변환할 컬럼 목록. 테이블별로 실제 ID 컬럼명을 채운다.
INT_COLS = {
    "table_a": ["entity_id"],
    "table_b": [],  # 이미 정수로 읽히면 비워둔다
}


def main(csv_path, table_name):
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("error: SUPABASE_DB_URL 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(csv_path)
    for col in INT_COLS.get(table_name, []):
        if col in df.columns:
            df[col] = df[col].astype("Int64")

    engine = create_engine(db_url)
    try:
        with engine.begin() as conn:
            conn.execute(text(f'TRUNCATE TABLE "{table_name}"'))
            df.to_sql(table_name, conn, if_exists="append", index=False)
    except ProgrammingError as e:
        if "does not exist" in str(e).lower() or "undefined" in str(e).lower():
            print(
                f"error: '{table_name}' 테이블이 없습니다. 먼저 스키마를 적용하세요:\n"
                f"    python apply_schema.py",
                file=sys.stderr,
            )
            sys.exit(1)
        raise

    print(f"{csv_path} -> Supabase 테이블 '{table_name}'에 {len(df)}행 적재 완료")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python load_csv_to_supabase.py <csv_path> <table_name>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
