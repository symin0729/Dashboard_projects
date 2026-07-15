# CLAUDE.md

이 파일은 이 저장소에서 작업하는 Claude Code(claude.ai/code)에게 제공하는 가이드다.

## 이 프로젝트는 무엇인가

Novartis Open Payments(제조사가 의료인에게 지급한 내역)와 CMS Medicare Part D Prescriber 데이터(2022년, 캘리포니아 중심)를 NPI(National Provider Identifier) 기준으로 결합하여, 제품별 지급-처방 지수와 고액 지급 의사 Top 30 목록을 제공하는 정적 웹 대시보드다. 주 사용자는 영업 관리자 및 리더십이다. 원본 데이터는 Supabase(관리형 Postgres)에 보관하지만, 프론트엔드 자체는 빌드 단계도 프레임워크도 없이 단일 정적 HTML 파일로 배포된다(예: GitHub Pages) — Supabase는 갱신 스크립트만 접근하는 데이터 소스이며 상시 구동 백엔드가 아니다.

전체 요구사항은 [PRD_지급처방_대시보드.md](PRD_지급처방_대시보드.md)(한국어)에 있다. 지표, 조인 로직, 범위를 변경하기 전에 반드시 읽을 것 — 아래 설계 결정이 *무엇*인지뿐 아니라 *왜* 그렇게 되었는지가 문서에 담겨 있다.

## 아키텍처

원본 데이터는 Supabase에 `open_payments`, `part_d_prescriber` 두 테이블로 보관한다. 프론트엔드는 여전히 완전한 정적 페이지이며 Supabase를 직접 호출하지 않는다 — 갱신 시점에만 아래 스크립트들이 Supabase에 접근해 JSON을 재생성한다.

아래 Python 스크립트를 실행하기 전 의존성을 설치한다: `pip install -r requirements.txt`(pandas, sqlalchemy, psycopg2-binary). 테스트 스위트·린터·빌드 단계는 없다.

**셸 주의(PowerShell)**: 이 저장소의 기본 셸은 Windows PowerShell이라 문서 전반의 `SUPABASE_DB_URL=... python ...`(bash 인라인 환경변수) 구문이 동작하지 않는다. PowerShell에서는 `$env:SUPABASE_DB_URL = 'postgresql://...'`로 먼저 설정한 뒤 `python ...`을 실행한다. bash 도구를 쓸 때만 인라인 구문을 그대로 쓸 수 있다.

- **[supabase/schema.sql](supabase/schema.sql)** — 두 테이블의 스키마 단일 원천. 컬럼 타입은 실제 CSV 값을 검사해 확정했다(NPI=`bigint`, 금액=`double precision`, 억제 플래그=`text` 등). Part D 컬럼명은 CamelCase라 반드시 큰따옴표로 감싼다 — 안 그러면 Postgres가 소문자로 접어 `to_sql`과 어긋난다. 타입 변경은 이 파일에서만 한다.
- **[apply_schema.py](apply_schema.py)** — `supabase/schema.sql`을 Supabase에 적용한다(`create table if not exists`). 최초 1회 및 스키마 변경 시 실행.
- **[load_csv_to_supabase.py](load_csv_to_supabase.py)** — CSV 한 개를 스키마로 미리 만든 테이블에 **TRUNCATE 후 append**로 적재한다(명시적 타입 보존). 스키마가 없으면 명확한 에러로 안내한다. 대량 적재에는 세션 풀러(포트 5432) 연결 문자열을 권장한다(트랜잭션 풀러 6543은 대량 insert에서 문제 소지).
  ```
  SUPABASE_DB_URL=postgresql://...:5432/postgres python load_csv_to_supabase.py open_payments.csv open_payments
  SUPABASE_DB_URL=postgresql://...:5432/postgres python load_csv_to_supabase.py part_d_prescriber.csv part_d_prescriber
  ```
- **[aggregate.py](aggregate.py)** — Supabase의 두 테이블을 `pandas.read_sql_table`로 읽어 조인/집계한 뒤 단일 JSON 블롭을 stdout으로 출력한다(`SUPABASE_DB_URL` 환경변수 필요). 집계 로직 자체(브랜드 정규화, 지수 계산 등)는 CSV 시절과 동일하다.
- **[update_dashboard.py](update_dashboard.py)** — `aggregate.py`의 집계 결과로 `index.html`의 `const DATA = {...}` 줄을 정규식으로 교체한다. 로컬 실행과 GitHub Actions에서 공통으로 사용한다.
- **[index.html](index.html)** — 자체 완결형 페이지(인라인 `<style>`, `<script>`, CDN의 Chart.js). 통계 카드, 제품 필터/차트, 고액 지급 의사 테이블 등 모든 렌더링은 `DATA`를 기반으로 한 순수 DOM 조작이다 — 빌드 도구나 설치할 의존성이 없다.
- **[architecture.html](architecture.html)** — 데이터 → 웹 → 라이브 파이프라인을 비개발자에게 설명하는 독립 실행형 안내 문서(대시보드 자체와는 별개). `index.html`의 데이터 흐름을 바꿨다면 이 문서의 설명도 함께 맞춰야 한다.
- **[.github/workflows/update-dashboard.yml](.github/workflows/update-dashboard.yml)** — `workflow_dispatch`(수동 버튼) 트리거. `update_dashboard.py`를 실행해 `index.html`을 재생성하고, 변경이 있으면 커밋·푸시한다. `SUPABASE_DB_URL`은 저장소의 Actions 시크릿으로 등록해야 한다.

**데이터 갱신 절차**: ① (최초 1회 또는 스키마 변경 시) `python apply_schema.py`로 스키마 적용. ② 새 CSV로 `load_csv_to_supabase.py`를 실행해 Supabase 테이블 데이터를 교체한다. ③ GitHub 저장소의 Actions 탭에서 "Update dashboard from Supabase" 워크플로를 수동으로 Run한다. 트리거는 의도적으로 사람이 누르는 버튼이다(PRD 5.3절 참조) — 스케줄이나 실시간 연동은 하지 않는다.

**미리보기 방법**: 브라우저에서 `index.html`을 열거나, 아무 정적 파일 서버로 이 디렉터리를 서빙하면 된다. 이 저장소에는 dev 서버, package.json, 테스트 스위트가 없다.

## `aggregate.py` 수정 시 지켜야 할 핵심 도메인 로직

- **제조사명 정규화**: `payment_manufacturer` 필드에 대소문자 표기 차이("Novartis Pharmaceuticals Corporation" vs 전체 대문자 버전)가 존재하며, 그룹화 전에 반드시 통일해야 한다 — `mfr_norm` 로직 참조.
- **브랜드명 정규화**: `base_brand()`는 Part D의 `Brnd_Name` 제형 변형(펜/시린지 접미사 등)을 3개 기본 브랜드(COSENTYX, ENTRESTO, LUCENTIS)로 축약한다. Open Payments의 `product_1`에는 22개 브랜드가 있지만, 두 데이터셋 모두에 존재하는 것은 Entresto와 Cosentyx뿐이다 — Lucentis는 대응하는 지급 데이터가 없어 상관관계 지수 계산에서 제외된다. 모든 Open Payments 제품에 대응하는 처방 데이터가 있다고 가정하지 말 것; JSON에서는 교집합이 없는 20개 브랜드의 필드가 `null`로 인코딩된다.
- **지수 계산**: `index_vs_avg`는 원시 지급액/처방약가 비율이 아니라 표준화된 지수다(Entresto+Cosentyx 결합 평균 = 1.0). 두 총액의 규모 차이가 약 193배에 달해 직접 비교가 불가능하기 때문이다. 두 데이터셋 모두에 존재하는 제품에 대해서만 계산된다.
- **NPI 조인은 의도적으로 부분적임**: Open Payments의 7,292개 NPI 중 약 1,677개(23%)만 처방 데이터와 매칭된다. 대시보드는 교집합 여부와 무관하게 모든 의사의 지급 데이터를 표시하지만(`has_prescribing_data` 플래그), 처방 연계 지표는 데이터가 존재할 때만 계산한다 — 모든 의사 레코드에 처방 관련 필드가 채워져 있다고 가정하지 말 것.
- 원본 CSV는 민감한 소스 데이터로 gitignore 처리되어 있다 — Supabase 업로드 후 로컬 파일은 폐기하며, 오직 집계된 JSON 요약만 커밋되어 `index.html`에 직접 내장된다. `SUPABASE_DB_URL`도 하드코딩하거나 커밋하지 말 것 — 로컬은 환경변수/`.env`(gitignore됨), CI는 GitHub Actions 시크릿으로만 주입한다.

## 컴플라이언스/프레이밍 제약사항

대시보드는 지급-처방 지수가 상관관계일 뿐 인과관계가 아니라는 화면 내 고지 문구를 유지해야 하며, 지급을 통해 처방을 유도하는 것으로 해석될 수 있는 방식으로 표현해서는 안 된다(Anti-Kickback Statute 위반 소지). `index.html`을 수정할 때 이 고지 문구를 그대로 유지할 것.
