"""
aggregate.py의 집계 결과(Supabase에서 읽은 최신 데이터)를 index.html의
`const DATA = {...};` 줄에 그대로 반영하는 스크립트.

로컬에서 수동 실행하거나, GitHub Actions 워크플로(update-dashboard.yml)에서
자동으로 실행된다.

사용법:
    SUPABASE_DB_URL=postgresql://... python update_dashboard.py
"""
import json
import re

import aggregate

INDEX_PATH = "index.html"
DATA_LINE_PATTERN = re.compile(r"^const DATA = .*;$", re.MULTILINE)


def main():
    op, pdd = aggregate.load_from_supabase()
    data = aggregate.build_dashboard_data(op, pdd)
    new_line = f"const DATA = {json.dumps(data, ensure_ascii=False)};"

    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    if not DATA_LINE_PATTERN.search(html):
        raise SystemExit(f"error: {INDEX_PATH}에서 'const DATA = ...;' 줄을 찾지 못했습니다.")

    updated = DATA_LINE_PATTERN.sub(lambda _: new_line, html, count=1)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print(f"{INDEX_PATH} 갱신 완료 (products={len(data['products'])}, top_physicians={len(data['top_physicians'])})")


if __name__ == "__main__":
    main()
