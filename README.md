# 지급-처방 상관관계 분석 대시보드

Novartis Open Payments와 CMS Medicare Part D Prescriber 데이터(2022년, 캘리포니아 중심)를 NPI 기준으로 결합하여 제품별 지급-처방 지수와 고액 지급 의사 목록을 제공하는 정적 웹 대시보드다. 요구사항 정의는 `PRD_지급처방_대시보드.md`를 참조한다.

## 구성

`index.html` 파일 하나로 동작하는 정적 페이지다. 원본 CSV는 포함하지 않으며, 제품별 요약과 고액 지급 의사 Top 30만 사전 집계하여 JSON으로 내장했다. Chart.js는 CDN에서 불러온다.

## GitHub Pages 배포 절차

1. GitHub에서 새 public 저장소를 생성한다 (예: `payment-prescription-dashboard`).
2. 이 폴더의 `index.html`을 저장소 루트에 추가한다.
3. 로컬에서 다음 명령으로 커밋 및 푸시한다.

```
git init
git add index.html README.md
git commit -m "Add payment-prescription dashboard"
git branch -M main
git remote add origin https://github.com/<사용자명>/<저장소명>.git
git push -u origin main
```

4. GitHub 저장소의 Settings → Pages에서 Source를 `main` 브랜치, 폴더는 `/ (root)`로 지정한다.
5. 수 분 후 `https://<사용자명>.github.io/<저장소명>/` 주소에서 대시보드에 접근할 수 있다.

## 데이터 갱신

원본 데이터는 Supabase(관리형 Postgres)에 `open_payments`, `part_d_prescriber` 테이블로 보관한다.

테이블 스키마는 [supabase/schema.sql](supabase/schema.sql)에 정의되어 있다(단일 원천).

1. (최초 1회, 또는 스키마 변경 시) 스키마를 적용한다.
   ```
   SUPABASE_DB_URL=postgresql://...:5432/postgres python apply_schema.py
   ```
2. 새 CSV가 도착하면 테이블 데이터를 교체한다(TRUNCATE 후 append — 스키마 타입 보존).
   ```
   SUPABASE_DB_URL=postgresql://...:5432/postgres python load_csv_to_supabase.py open_payments.csv open_payments
   SUPABASE_DB_URL=postgresql://...:5432/postgres python load_csv_to_supabase.py part_d_prescriber.csv part_d_prescriber
   ```
3. GitHub 저장소의 Actions 탭에서 "Update dashboard from Supabase" 워크플로를 수동으로 Run한다. `aggregate.py`가 Supabase에서 재집계하고 `update_dashboard.py`가 `index.html`의 `const DATA = {...}` 블록을 갱신·커밋한다(변경이 있을 때만). 몇 분 후 GitHub Pages에 반영된다.

> 대량 적재에는 **세션 풀러(포트 5432)** 연결 문자열을 쓴다. 직접 연결 호스트(`db.<ref>.supabase.co`)는 IPv6 전용이라 IPv4 환경에서 접속되지 않으므로, `...pooler.supabase.com` 형태의 풀러 문자열을 사용한다.

트리거는 의도적으로 사람이 누르는 버튼(`workflow_dispatch`)이다 — 스케줄 기반 자동 실행이나 실시간 연동은 이번 범위에 포함하지 않는다(PRD 5.3절 참조).

최초 설정 시 필요한 것:
- Supabase 프로젝트의 Connection string(Settings → Database, URI 형식)을 로컬 환경변수 `SUPABASE_DB_URL`로 설정.
- 같은 값을 저장소 Settings → Secrets and variables → Actions에 `SUPABASE_DB_URL` 시크릿으로 등록.
