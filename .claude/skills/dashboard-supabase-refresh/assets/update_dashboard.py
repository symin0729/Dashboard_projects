"""
Supabase에서 최신 데이터를 집계해 index.html의 `const DATA = {...};` 줄을 교체한다.

로컬에서 수동 실행하거나, GitHub Actions 워크플로(update-dashboard.yml)에서 실행된다.
aggregate 모듈(aggregate_supabase.py를 aggregate.py로 배치)의 함수를 재사용한다.

사용법:
    SUPABASE_DB_URL=postgresql://... python update_dashboard.py
"""
import json
import re

import aggregate  # build_dashboard_data / load_from_supabase 를 제공하는 모듈

INDEX_PATH = "index.html"
DATA_LINE_PATTERN = re.compile(r"^const DATA = .*;$", re.MULTILINE)


def main():
    a, b = aggregate.load_from_supabase()
    data = aggregate.build_dashboard_data(a, b)
    new_line = f"const DATA = {json.dumps(data, ensure_ascii=False)};"

    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    if not DATA_LINE_PATTERN.search(html):
        raise SystemExit(f"error: {INDEX_PATH}에서 'const DATA = ...;' 줄을 찾지 못했습니다.")

    # 치환 문자열이 아니라 함수를 쓴다 — JSON의 백슬래시가 그룹 참조(\1 등)로
    # 오해되는 것을 막는다.
    updated = DATA_LINE_PATTERN.sub(lambda _: new_line, html, count=1)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"{INDEX_PATH} 갱신 완료")


if __name__ == "__main__":
    main()
