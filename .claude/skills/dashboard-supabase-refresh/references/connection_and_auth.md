# Supabase 연결·인증 트러블슈팅

연결 문자열이 이 작업의 가장 큰 마찰 지점이다. 에러 메시지별로 원인이 명확히 갈리므로,
아래 표로 진단하면 추측 없이 바로 원인을 짚을 수 있다.

## 에러 → 원인 매트릭스

| 증상 | 원인 | 해결 |
|---|---|---|
| `could not translate host name "db.<ref>.supabase.co"` | 직접 연결(Direct) 호스트는 **IPv6 전용**. IPv4 환경에서 DNS가 안 풀림 | **세션 풀러** 문자열로 교체 (`...pooler.supabase.com`) |
| `password authentication failed for user "postgres"` | 네트워크·사용자명은 정상, **비밀번호만** 틀림 (대개 리셋이 실제 저장 안 됨) | 비밀번호 재설정 후 저장 확인. 몇 초 전파 시간 대기 |
| `Tenant or user not found` | 풀러 사용자명이 잘못됨 (`postgres`만 쓰거나 ref 누락) | 사용자명을 `postgres.<project-ref>` 형태로 |
| 대량 insert 중 prepared statement 관련 오류 | 트랜잭션 풀러(6543)는 대량 insert에 부적합 | 세션 풀러(**5432**) 사용 |
| `column "Xxx" does not exist` (적재 시) | CamelCase 컬럼을 스키마에서 따옴표 없이 만들어 소문자로 접힘 | schema.sql에서 해당 컬럼을 `"Xxx"`로 큰따옴표 처리 후 재적용 |

## 올바른 연결 문자열 얻는 법

Supabase 대시보드 상단의 초록색 **Connect** 버튼 → 모달에서 탭 선택:

- **Direct connection** — 쓰지 말 것 (IPv6 전용). "Enable IPv4 add-on"은 유료.
- **Session pooler (포트 5432)** — ★ 이것을 사용. IPv4 가능, 대량 적재·장기 연결에 적합.
- **Transaction pooler (포트 6543)** — 단발 쿼리엔 되지만 pandas 대량 insert엔 부적합.

형태:
```
postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
```
`<project-ref>`, `<region>`은 Supabase가 보여주는 문자열에 이미 들어 있다 — 임의로 바꾸지 말 것.

## 비밀번호를 모를 때 (흔함)

DB 비밀번호는 프로젝트 생성 시 한 번만 노출되고 다시 안 보인다. 모르면 **재설정**이 정상 경로:

1. Settings → Database → **Reset database password** (Connect 모달의 "Reset password"도 동일)
2. 가능하면 **영문+숫자만**으로 지정 — 특수문자(`@ : / ?`)는 URL에서 퍼센트 인코딩이 필요해 오류 소지가 크다
3. 저장 버튼까지 눌러 "updated" 확인 후, 그 자리에 뜬 값을 즉시 복사
4. 재설정 직후 몇 초는 전파에 걸릴 수 있음

## 접속 사전 검증 (항상 먼저)

본 작업을 시작하기 전에 연결부터 확인해, 잘못된 문자열이 조용히 뒤 단계로 흘러가지 않게 한다.
비밀번호를 출력하지 않는 형태로:
```bash
python -c "import os,psycopg2; psycopg2.connect(os.environ['SUPABASE_DB_URL'],connect_timeout=15); print('CONNECT_OK')"
```
`CONNECT_OK`가 뜨면 스키마 적용·적재로 진행한다.

## 자격증명 위생

- 연결 문자열/비밀번호를 **코드에 하드코딩하거나 커밋하지 말 것**. 로컬은 환경변수/`.env`(gitignore), CI는 GitHub Actions 시크릿.
- 셋업 중 비밀번호가 채팅·터미널에 노출됐다면, git 이력은 깨끗한지 확인(`git grep`로 프로젝트 ref나 `pooler.supabase` 검색 → 플레이스홀더 문서에만 매치되어야 정상)하되, 대화 노출은 지울 수 없으니 마지막에 한 번 더 재설정 후 **시크릿 값만** 교체하도록 권한다(로컬 재적재 불필요). 긴급 사고가 아니라 위생 차원임을 솔직히 전달.
