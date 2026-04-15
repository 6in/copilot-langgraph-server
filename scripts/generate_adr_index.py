#!/usr/bin/env python3
"""docs/adr/INDEX.md を .planning/adr-categories.yaml に基づいて自動生成する。

D-03 準拠: ADR 本文は一切変更しない。
D-04 準拠: 欠番 0015-0017 を「欠番」として明示記録する。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ADR_DIR = REPO_ROOT / "docs" / "adr"
CATEGORIES_YAML = REPO_ROOT / ".planning" / "adr-categories.yaml"
INDEX_MD = ADR_DIR / "INDEX.md"

# ADR 0020 は "# ADR 0020:" 形式、他は "# 0001. タイトル" 形式
TITLE_RE = re.compile(r"^# (?:ADR )?(\d+)[.:]\s+(.+?)\s*$", re.MULTILINE)
# "**Date:** YYYY-MM-DD" と "**Date**: YYYY-MM-DD" の両方に対応
# 両方のパターンで `**` と `:` の順序が異なるため、`[*:\s]+` で柔軟に吸収する
DATE_RE = re.compile(r"^\*\*Date[*:\s]+(\d{4}-\d{2}-\d{2})", re.MULTILINE)


def parse_adr(path: Path) -> tuple[str, str, str] | None:
    """(番号, タイトル, 日付) を返す。パース失敗時は None。"""
    text = path.read_text(encoding="utf-8")
    t = TITLE_RE.search(text)
    d = DATE_RE.search(text)
    if not t:
        return None
    number = t.group(1).zfill(4)
    title = t.group(2).strip()
    date = d.group(1) if d else "-"
    return number, title, date


def load_categories() -> dict:
    return yaml.safe_load(CATEGORIES_YAML.read_text(encoding="utf-8"))


def build_index(adr_dir: Path, categories_data: dict) -> str:
    """INDEX.md の markdown 文字列を生成する。"""
    parsed: dict[str, tuple[str, str, str, str]] = {}
    for md in sorted(adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")):
        r = parse_adr(md)
        if r:
            parsed[r[0]] = (*r, md.name)

    cats_list = categories_data["categories"]
    adr_cats = categories_data["adr_categories"]
    missing = categories_data.get("missing", [])

    # カテゴリ別に ADR を集める（primary のみ）
    by_cat: dict[str, list] = {c: [] for c in cats_list}
    for num, meta in adr_cats.items():
        if num in parsed:
            by_cat[meta["primary"]].append(parsed[num])

    lines: list[str] = []
    lines.append("# ADR Index")
    lines.append("")
    lines.append(
        f"**Total:** {len(parsed)} 件（欠番 {len(missing)} 件: {', '.join(missing)}）"
    )
    lines.append("")
    lines.append(
        "> このファイルは `scripts/generate_adr_index.py` により自動生成されます。手動編集しないこと。"
    )
    lines.append("")

    for cat in cats_list:
        lines.append(f"## {cat}")
        lines.append("")
        entries = sorted(by_cat[cat], key=lambda x: x[0])
        if not entries:
            lines.append("_（該当 ADR なし）_")
            lines.append("")
            continue
        lines.append("| No. | タイトル | Date |")
        lines.append("|-----|---------|------|")
        for num, title, date, fname in entries:
            lines.append(f"| [{num}]({fname}) | {title} | {date} |")
        lines.append("")

    lines.append("## 欠番")
    lines.append("")
    lines.append("| No. | 備考 |")
    lines.append("|-----|------|")
    for m in missing:
        lines.append(f"| {m} | — 欠番 — |")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    data = load_categories()
    content = build_index(ADR_DIR, data)
    INDEX_MD.write_text(content, encoding="utf-8")
    print(f"Generated {INDEX_MD.relative_to(REPO_ROOT)} ({len(content)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
