-- 대시보드 원본 데이터 스키마 (템플릿 — 실제 컬럼에 맞게 수정할 것)
--
-- 이 파일이 테이블 스키마의 단일 원천이다. 타입은 inspect_csv.py로 실제 CSV 값을
-- 검사해 확정한다(추측 금지). 데이터는 load_csv_to_supabase.py가 TRUNCATE 후
-- append로 채운다.
--
-- 적용:  (session pooler, 5432) SUPABASE_DB_URL=postgresql://... python apply_schema.py
--        또는 Supabase 대시보드 SQL Editor에 붙여넣어 실행.
--
-- ★ 규칙 1: 컬럼명이 lowercase_snake_case가 아니면(예: CamelCase) 반드시 큰따옴표로 감싼다.
--           안 그러면 Postgres가 소문자로 접어 pandas.to_sql(따옴표로 조회)과 어긋나
--           "column does not exist"로 적재가 실패한다.
-- ★ 규칙 2: '#'/'*' 같은 억제 마커가 섞인 컬럼은 숫자처럼 보여도 text로 선언한다.
-- ★ 규칙 3: 결측 때문에 float로 읽히는 식별자(ID/NPI 등)는 bigint로 선언하고,
--           로더에서 Int64로 교정해 넣는다.

-- 예시 A: 소문자 컬럼 테이블 (따옴표 불필요)
create table if not exists table_a (
    entity_id        bigint,            -- 식별자 → bigint (로더에서 Int64 교정)
    entity_name      text,
    category         text,
    amount_usd       double precision,  -- 금액
    event_date       text,              -- 날짜 파싱이 필요 없으면 text로 두는 게 단순
    record_id        bigint
);

-- 예시 B: CamelCase 컬럼 테이블 (전부 큰따옴표로 감쌈)
create table if not exists table_b (
    "Entity_ID"        bigint,
    "Entity_Name"      text,
    "Brand"            text,
    "Total_Cost"       double precision,
    "Total_Claims"     bigint,
    "Supression_Flag"  text,            -- '#' 또는 '*' → text
    "GE65_Total"       double precision -- 억제 시 NULL
);
