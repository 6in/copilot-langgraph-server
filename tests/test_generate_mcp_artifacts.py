"""generate_mcp_artifacts.py のユニットテスト。

ジェネレータを subprocess ではなく import して関数を直接テストする。
tests/test_generate_adr_index.py と同じ sys.path.insert 方式を採用。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import generate_mcp_artifacts as gen  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_tool(tools: list[dict], name: str) -> dict:
    for t in tools:
        if t["name"] == name:
            return t
    raise KeyError(name)


# ---------------------------------------------------------------------------
# load_tools
# ---------------------------------------------------------------------------


def test_load_tools_has_six_tools():
    """実 YAML を読み込んで 6 ツールが返る。"""
    tools = gen.load_tools()
    assert len(tools) == 6
    names = [t["name"] for t in tools]
    assert names == [
        "ping",
        "web_search",
        "db_query",
        "claude_code",
        "execute_python",
        "get_current_datetime",
    ]


# ---------------------------------------------------------------------------
# build_helper
# ---------------------------------------------------------------------------


def test_build_helper_header_and_imports():
    """build_helper 出力が DO NOT EDIT で始まり、utils import を含む。"""
    tools = gen.load_tools()
    text = gen.build_helper(tools)
    assert text.startswith("# DO NOT EDIT"), f"helper should start with DO NOT EDIT, got: {text[:60]!r}"
    assert "from mcp_helper_utils import _call_tool, _clean_content" in text


def test_build_helper_has_four_functions():
    """build_helper 出力に search / query_db / get_datetime / ping の 4 関数が生成される。

    claude_code / execute_python は python_wrapper が無いので含まれない。
    """
    tools = gen.load_tools()
    text = gen.build_helper(tools)
    # 関数定義は行頭 (インデントなし) に現れる
    assert re.search(r"^def search\(", text, re.MULTILINE), "search function missing"
    assert re.search(r"^def query_db\(", text, re.MULTILINE), "query_db function missing"
    assert re.search(r"^def get_datetime\(", text, re.MULTILINE), "get_datetime function missing"
    assert re.search(r"^def ping\(", text, re.MULTILINE), "ping function missing"
    # claude_code / execute_python は含まれない
    assert "def claude_code" not in text
    assert "def execute_python" not in text
    # ちょうど 4 つ
    def_count = len(re.findall(r"^def ", text, re.MULTILINE))
    assert def_count == 4, f"expected 4 top-level defs, got {def_count}"


def test_build_helper_web_search_uses_clean_content():
    """search 関数本体に _clean_content(r["content"]) 呼び出しが含まれる。"""
    tools = gen.load_tools()
    text = gen.build_helper(tools)
    assert '_clean_content(r["content"])' in text


def test_build_helper_db_query_maps_pool_to_pool_name():
    """query_db 関数本体で Python 側 pool が MCP 側 pool_name にマッピングされる。"""
    tools = gen.load_tools()
    text = gen.build_helper(tools)
    assert '"pool_name": pool' in text, "db_query wrapper must map Python `pool` arg to MCP `pool_name`"


# ---------------------------------------------------------------------------
# build_js
# ---------------------------------------------------------------------------


def test_build_js_header_and_array():
    """build_js 出力が DO NOT EDIT で始まり AVAILABLE_TOOLS 配列を含む。"""
    tools = gen.load_tools()
    text = gen.build_js(tools)
    assert text.startswith("// DO NOT EDIT"), f"js should start with DO NOT EDIT, got: {text[:60]!r}"
    assert "export const AVAILABLE_TOOLS = [" in text


def test_build_js_privileged_tag():
    """claude_code と execute_python の 2 ツールに privileged: true が付与される。"""
    tools = gen.load_tools()
    text = gen.build_js(tools)
    # JS オブジェクトリテラルの privileged: true を数える
    count = text.count("privileged: true")
    assert count == 2, f"expected privileged: true for 2 tools, got {count}"


def test_build_js_order():
    """build_js の name: "..." 出現順が YAML tools 順と一致する。"""
    tools = gen.load_tools()
    text = gen.build_js(tools)
    # 配列ブロック内の name のみを抽出する (JSDoc テーブルを除外)
    array_block = text.split("export const AVAILABLE_TOOLS = [")[1].split("];")[0]
    found = re.findall(r'name:\s*"([^"]+)"', array_block)
    assert found == [
        "ping",
        "web_search",
        "db_query",
        "claude_code",
        "execute_python",
        "get_current_datetime",
    ], f"unexpected JS array order: {found}"


# ---------------------------------------------------------------------------
# build_docs
# ---------------------------------------------------------------------------


def test_build_docs_header_and_table():
    """build_docs 出力が HTML コメント DO NOT EDIT で始まり、6 セクションを含む。"""
    tools = gen.load_tools()
    text = gen.build_docs(tools)
    assert text.startswith("<!-- DO NOT EDIT"), f"docs should start with HTML DO NOT EDIT: {text[:60]!r}"
    assert "# MCP Tools Catalog" in text
    # 各ツールの詳細セクション
    sections = re.findall(r"^## `([^`]+)`", text, re.MULTILINE)
    assert sections == [
        "ping",
        "web_search",
        "db_query",
        "claude_code",
        "execute_python",
        "get_current_datetime",
    ], f"unexpected docs sections order: {sections}"


def test_build_docs_privileged_warning():
    """claude_code セクションに Privileged 警告段落が含まれる。"""
    tools = gen.load_tools()
    text = gen.build_docs(tools)
    # claude_code セクションのみを切り出す
    parts = text.split("## `claude_code`", 1)
    assert len(parts) == 2, "claude_code section missing"
    after = parts[1].split("## `", 1)[0]
    assert "**Privileged:**" in after, "claude_code section must contain Privileged warning"


# ---------------------------------------------------------------------------
# Determinism & trailing newline
# ---------------------------------------------------------------------------


def test_determinism():
    """同一入力に対して build_helper / build_js / build_docs の戻り値がバイト完全一致する。"""
    tools = gen.load_tools()
    for fn in (gen.build_helper, gen.build_js, gen.build_docs):
        out1 = fn(tools)
        out2 = fn(tools)
        assert out1 == out2, f"{fn.__name__} is not deterministic"


def test_trailing_newline():
    """build_helper / build_js / build_docs は末尾に単一の `\\n` を持つ。

    drift 検知 (check_all) のバイト完全一致比較で偽陽性を避けるための必須規約。
    """
    tools = gen.load_tools()
    for fn in (gen.build_helper, gen.build_js, gen.build_docs):
        out = fn(tools)
        assert out.endswith("\n"), f"{fn.__name__} must end with a single newline"
        assert not out.endswith("\n\n"), f"{fn.__name__} must not end with double newline"


# ---------------------------------------------------------------------------
# _generate_wrapper_body
# ---------------------------------------------------------------------------


def test_generate_wrapper_body_passthrough():
    """引数なし passthrough (ping) は単純な _call_tool 呼び出しを生成する。"""
    tools = gen.load_tools()
    ping_tool = _get_tool(tools, "ping")
    body = gen._generate_wrapper_body(ping_tool)
    assert 'return _call_tool("ping")' in body
    # 引数辞書が無いので括弧内は ("ping") のみ
    assert "_call_tool(\"ping\",\n" not in body


def test_generate_wrapper_body_extract_key():
    """extract_key (db_query) は result.get("rows", [result]) パターンを生成する。"""
    tools = gen.load_tools()
    db_tool = _get_tool(tools, "db_query")
    body = gen._generate_wrapper_body(db_tool)
    assert 'result = _call_tool("db_query"' in body
    assert 'return result.get("rows", [result])' in body
    assert '"pool_name": pool' in body
    assert 'if "error" in result' in body


def test_generate_wrapper_body_web_search():
    """web_search_results (web_search) は results[] と _clean_content を生成する。"""
    tools = gen.load_tools()
    ws_tool = _get_tool(tools, "web_search")
    body = gen._generate_wrapper_body(ws_tool)
    assert 'result.get("results", [result])' in body
    assert 'r["content"] = _clean_content(r["content"])' in body


# ---------------------------------------------------------------------------
# check_all (drift detection)
# ---------------------------------------------------------------------------


def test_check_all_detects_drift_missing(tmp_path, monkeypatch, capsys):
    """on-disk ファイルが無ければ check_all は 1 を返し [drift] missing を出力する。"""
    tools = gen.load_tools()
    helper_path = tmp_path / "mcp_helper.py"
    js_path = tmp_path / "tool-catalog-generated.js"
    docs_path = tmp_path / "mcp-tools.md"
    # ファイルは作らない

    monkeypatch.setattr(gen, "HELPER_PATH", helper_path)
    monkeypatch.setattr(gen, "JS_PATH", js_path)
    monkeypatch.setattr(gen, "DOCS_PATH", docs_path)

    rc = gen.check_all(tools)
    assert rc == 1
    captured = capsys.readouterr()
    assert "[drift] missing" in captured.err
    assert "Fix:" in captured.err


def test_check_all_pass_when_match(tmp_path, monkeypatch, capsys):
    """ファイル内容が build_* 出力と一致すれば check_all は 0 を返す。"""
    tools = gen.load_tools()
    helper_text = gen.build_helper(tools)
    js_text = gen.build_js(tools)
    docs_text = gen.build_docs(tools)

    helper_path = tmp_path / "mcp_helper.py"
    js_path = tmp_path / "tool-catalog-generated.js"
    docs_path = tmp_path / "mcp-tools.md"
    helper_path.write_text(helper_text, encoding="utf-8")
    js_path.write_text(js_text, encoding="utf-8")
    docs_path.write_text(docs_text, encoding="utf-8")

    monkeypatch.setattr(gen, "HELPER_PATH", helper_path)
    monkeypatch.setattr(gen, "JS_PATH", js_path)
    monkeypatch.setattr(gen, "DOCS_PATH", docs_path)

    rc = gen.check_all(tools)
    captured = capsys.readouterr()
    assert rc == 0, f"check_all must return 0 on byte-exact match; stderr={captured.err!r}"
    assert captured.err == ""


def test_check_all_detects_drift_mismatch(tmp_path, monkeypatch, capsys):
    """ファイル内容が build_* 出力と異なれば check_all は 1 を返し unified_diff を出力する。"""
    tools = gen.load_tools()
    helper_path = tmp_path / "mcp_helper.py"
    js_path = tmp_path / "tool-catalog-generated.js"
    docs_path = tmp_path / "mcp-tools.md"
    helper_path.write_text("# WRONG CONTENT\n", encoding="utf-8")
    js_path.write_text(gen.build_js(tools), encoding="utf-8")
    docs_path.write_text(gen.build_docs(tools), encoding="utf-8")

    monkeypatch.setattr(gen, "HELPER_PATH", helper_path)
    monkeypatch.setattr(gen, "JS_PATH", js_path)
    monkeypatch.setattr(gen, "DOCS_PATH", docs_path)

    rc = gen.check_all(tools)
    captured = capsys.readouterr()
    assert rc == 1
    assert "[drift] out of sync" in captured.err
    # unified_diff ヘッダが出ている
    assert "---" in captured.err and "+++" in captured.err
