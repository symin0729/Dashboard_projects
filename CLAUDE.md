# CLAUDE.md

이 파일은 이 저장소에서 작업하는 Claude Code(claude.ai/code)에게 제공하는 가이드다.

## 이 프로젝트는 무엇인가

Novartis Open Payments(제조사가 의료인에게 지급한 내역)와 CMS Medicare Part D Prescriber 데이터(2022년, 캘리포니아 중심)를 NPI(National Provider Identifier) 기준으로 결합하여, 제품별 지급-처방 지수와 고액 지급 의사 Top 30 목록을 제공하는 정적 웹 대시보드다. 주 사용자는 영업 관리자 및 리더십이다. 백엔드도, 빌드 단계도, 프레임워크도 없이 단일 정적 HTML 파일로 배포된다(예: GitHub Pages).

전체 요구사항은 [PRD_지급처방_대시보드.md](PRD_지급처방_대시보드.md)(한국어)에 있다. 지표, 조인 로직, 범위를 변경하기 전에 반드시 읽을 것 — 아래 설계 결정이 *무엇*인지뿐 아니라 *왜* 그렇게 되었는지가 문서에 담겨 있다.

## 아키텍처

두 개의 조각으로만 구성되며, 그 외 도구는 없다:

- **[aggregate.py](aggregate.py)** — 오프라인 pandas 스크립트. 원본 `open_payments.csv`와 `part_d_prescriber.csv`(커밋되지 않음 — `.gitignore` 참조)를 받아 조인/집계한 뒤 단일 JSON 블롭을 stdout으로 출력한다.
  ```
  python aggregate.py open_payments.csv part_d_prescriber.csv > dashboard_data.json
  ```
- **[index.html](index.html)** — 자체 완결형 페이지(인라인 `<style>`, `<script>`, CDN의 Chart.js). 집계 스크립트가 출력한 JSON을 `<script>` 블록의 `const DATA = {...}` 줄에 그대로 붙여넣는다. 통계 카드, 제품 필터/차트, 고액 지급 의사 테이블 등 모든 렌더링은 `DATA`를 기반으로 한 순수 DOM 조작이다 — 빌드 도구나 설치할 의존성이 없다.

**데이터 갱신 절차**: 갱신된 CSV로 `aggregate.py`를 다시 실행하고, 출력된 JSON을 복사하여 `index.html`의 `const DATA = {...}` 줄을 수동으로 교체한다. 이는 의도적으로 수동 절차다(PRD 5.3절 참조) — 이를 자동화하는 파이프라인은 없다.

**미리보기 방법**: 브라우저에서 `index.html`을 열거나, 아무 정적 파일 서버로 이 디렉터리를 서빙하면 된다. 이 저장소에는 dev 서버, package.json, 테스트 스위트가 없다.

## `aggregate.py` 수정 시 지켜야 할 핵심 도메인 로직

- **제조사명 정규화**: `payment_manufacturer` 필드에 대소문자 표기 차이("Novartis Pharmaceuticals Corporation" vs 전체 대문자 버전)가 존재하며, 그룹화 전에 반드시 통일해야 한다 — `mfr_norm` 로직 참조.
- **브랜드명 정규화**: `base_brand()`는 Part D의 `Brnd_Name` 제형 변형(펜/시린지 접미사 등)을 3개 기본 브랜드(COSENTYX, ENTRESTO, LUCENTIS)로 축약한다. Open Payments의 `product_1`에는 22개 브랜드가 있지만, 두 데이터셋 모두에 존재하는 것은 Entresto와 Cosentyx뿐이다 — Lucentis는 대응하는 지급 데이터가 없어 상관관계 지수 계산에서 제외된다. 모든 Open Payments 제품에 대응하는 처방 데이터가 있다고 가정하지 말 것; JSON에서는 교집합이 없는 20개 브랜드의 필드가 `null`로 인코딩된다.
- **지수 계산**: `index_vs_avg`는 원시 지급액/처방약가 비율이 아니라 표준화된 지수다(Entresto+Cosentyx 결합 평균 = 1.0). 두 총액의 규모 차이가 약 193배에 달해 직접 비교가 불가능하기 때문이다. 두 데이터셋 모두에 존재하는 제품에 대해서만 계산된다.
- **NPI 조인은 의도적으로 부분적임**: Open Payments의 7,292개 NPI 중 약 1,677개(23%)만 처방 데이터와 매칭된다. 대시보드는 교집합 여부와 무관하게 모든 의사의 지급 데이터를 표시하지만(`has_prescribing_data` 플래그), 처방 연계 지표는 데이터가 존재할 때만 계산한다 — 모든 의사 레코드에 처방 관련 필드가 채워져 있다고 가정하지 말 것.
- 원본 CSV는 민감한 소스 데이터로 gitignore 처리되어 있다 — 오직 집계된 JSON 요약만 커밋되며, `index.html`에 직접 내장된다.

## 컴플라이언스/프레이밍 제약사항

대시보드는 지급-처방 지수가 상관관계일 뿐 인과관계가 아니라는 화면 내 고지 문구를 유지해야 하며, 지급을 통해 처방을 유도하는 것으로 해석될 수 있는 방식으로 표현해서는 안 된다(Anti-Kickback Statute 위반 소지). `index.html`을 수정할 때 이 고지 문구를 그대로 유지할 것.
