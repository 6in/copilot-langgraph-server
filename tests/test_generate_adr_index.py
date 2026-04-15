"""generate_adr_index.py のユニットテスト。"""
import sys
from pathlib import Path

import pytest  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import generate_adr_index as gai  # noqa: E402


def test_parse_standard_adr():
    """標準フォーマット (# 0001. ...) がパースできる"""
    path = REPO_ROOT / "docs" / "adr" / "0001-nginx-prefix-strip-for-url-routing.md"
    result = gai.parse_adr(path)
    assert result is not None
    number, title, date = result
    assert number == "0001"
    assert "nginx" in title.lower() or "prefix" in title.lower()
    assert date.startswith("2026-")


def test_parse_adr_0020_alternate_format():
    """ADR 0020 の '# ADR 0020:' / '**Date**:' 形式がパースできる"""
    path = REPO_ROOT / "docs" / "adr" / "0020-fastmcp-docker-service-infrastructure.md"
    result = gai.parse_adr(path)
    assert result is not None
    number, title, date = result
    assert number == "0020"
    assert date.startswith("2026-")


def test_load_categories_structure():
    data = gai.load_categories()
    assert len(data["categories"]) == 7
    assert "Auth" in data["categories"]
    assert "LangGraph・Graph" in data["categories"]
    assert len(data["adr_categories"]) >= 30
    assert data["missing"] == ["0015", "0016", "0017"]


def test_build_index_has_all_categories():
    data = gai.load_categories()
    content = gai.build_index(gai.ADR_DIR, data)
    for cat in data["categories"]:
        assert f"## {cat}" in content


def test_build_index_records_missing():
    data = gai.load_categories()
    content = gai.build_index(gai.ADR_DIR, data)
    assert "## 欠番" in content
    assert "0015" in content and "0016" in content and "0017" in content


def test_build_index_includes_adr_0020():
    """ADR 0020 がインデックスに含まれていること（Pitfall 1 回避検証）"""
    data = gai.load_categories()
    content = gai.build_index(gai.ADR_DIR, data)
    assert "0020" in content
    # 0020 は MCP・Tools カテゴリにあるべき
    mcp_section = content.split("## MCP・Tools", 1)[1].split("## ", 1)[0]
    assert "0020" in mcp_section


def test_build_index_total_count():
    data = gai.load_categories()
    content = gai.build_index(gai.ADR_DIR, data)
    assert "**Total:**" in content and "件" in content
