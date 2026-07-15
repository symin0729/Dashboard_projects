"""
supabase/schema.sql을 Supabase(Postgres)에 적용한다(테이블 생성).

최초 1회 설정 시, 그리고 스키마를 바꿨을 때 실행한다. create table if not exists이므로
반복 실행해도 기존 테이블을 덮어쓰지 않는다(타입을 바꾸려면 먼저 DROP 필요).

대량 적재에는 세션 풀러(포트 5432) 연결 문자열을 권장한다.

사용법:
    SUPABASE_DB_URL=postgresql://...:5432/postgres python apply_schema.py
"""
import os
import sys

from sqlalchemy import create_engine, text

SCHEMA_PATH = os.path.join("supabase", "schema.sql")


def main():
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("error: SUPABASE_DB_URL 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        sql = f.read()

    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text(sql))
    print(f"{SCHEMA_PATH} 적용 완료")


if __name__ == "__main__":
    main()
