-- 지급-처방 대시보드 원본 데이터 스키마
--
-- Supabase(Postgres)에 두 원본 테이블을 명시적으로 정의한다. 컬럼 타입은
-- 실제 CSV 값을 검사해 확정했다(NPI=bigint, 금액=double precision, 억제 플래그=text 등).
-- 데이터는 load_csv_to_supabase.py가 TRUNCATE 후 append로 채운다 —
-- 이 파일이 스키마의 단일 원천(source of truth)이며, 타입은 이 파일에서만 바꾼다.
--
-- 적용:  SUPABASE_DB_URL=postgresql://... python apply_schema.py
--        또는 Supabase 대시보드 SQL Editor에 붙여넣어 실행.
--
-- 주의: Part D 컬럼명은 CamelCase이므로 반드시 큰따옴표로 감싼다.
--       (따옴표 없이 만들면 Postgres가 소문자로 접어 pandas.to_sql과 어긋난다.)

create table if not exists open_payments (
    covered_recipient_npi          bigint,
    recipient_first_name           text,
    recipient_last_name            text,
    recipient_city                 text,
    recipient_state                text,
    covered_recipient_type         text,
    recipient_primary_type         text,
    recipient_specialty            text,
    submitting_manufacturer        text,
    payment_manufacturer           text,
    payment_amount_usd             double precision,
    date_of_payment                text,
    payment_count                  bigint,
    payment_form                   text,
    payment_nature                 text,
    physician_ownership_indicator  text,
    third_party_payment_indicator  text,
    related_product_indicator      text,
    product_1                      text,
    product_2                      text,
    product_3                      text,
    product_4                      double precision,  -- 현재 데이터에선 전부 비어 있음
    product_5                      double precision,  -- 현재 데이터에선 전부 비어 있음
    record_id                      bigint,
    dispute_status                 text,
    program_year                   bigint,
    payment_publication_date       text
);

create table if not exists part_d_prescriber (
    "Prscrbr_NPI"           bigint,
    "Prscrbr_Last_Org_Name" text,
    "Prscrbr_First_Name"    text,
    "Prscrbr_City"          text,
    "Prscrbr_State_Abrvtn"  text,
    "Prscrbr_State_FIPS"    bigint,
    "Prscrbr_Type"          text,
    "Prscrbr_Type_Src"      text,
    "Brnd_Name"             text,
    "Gnrc_Name"             text,
    "Tot_Clms"              bigint,
    "Tot_30day_Fills"       double precision,
    "Tot_Day_Suply"         bigint,
    "Tot_Drug_Cst"          double precision,
    "Tot_Benes"             double precision,  -- 억제 시 NULL
    "GE65_Sprsn_Flag"       text,              -- '#' 또는 '*' (CMS 개인정보 억제)
    "GE65_Tot_Clms"         double precision,
    "GE65_Tot_30day_Fills"  double precision,
    "GE65_Tot_Drug_Cst"     double precision,
    "GE65_Tot_Day_Suply"    double precision,
    "GE65_Bene_Sprsn_Flag"  text,
    "GE65_Tot_Benes"        double precision
);
