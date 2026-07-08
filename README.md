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

CSV가 교체되면 집계 스크립트(`aggregate.py`)를 다시 실행하여 `index.html` 내 `const DATA = {...}` 블록을 새 집계 결과로 교체한 뒤 재배포한다. 자동화 파이프라인은 이번 범위에 포함하지 않는다(PRD 5.3절 참조).
