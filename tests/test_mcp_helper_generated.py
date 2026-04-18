"""Phase 30: 自動生成された mcp_helper.py の挙動回帰テスト。

Plan 03 で mcp_helper.py は scripts/generate_mcp_artifacts.py --target helper によって
生成されたコードに置き換わった。本テストは「Phase 30 前の手書き版と同一の挙動」を保証する。

_call_tool をモック化し、各 public 関数 (search / query_db / get_datetime / ping) が
期待通りの引数で _call_tool を呼び、期待通りの戻り値を返すことを検証する。

patch 対象は `mcp_helper` モジュール（import 済みシンボルを差し替えるため）。
`mcp_helper_utils` 側を patch しても mcp_helper 側の bindings は変わらない。
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# mcp_helper は mcp_server/tools ディレクトリに存在する（sandbox と同じ import 方式）
TOOLS_DIR = Path(__file__).resolve().parent.parent / "mcp_server" / "tools"
sys.path.insert(0, str(TOOLS_DIR))

import mcp_helper           # noqa: E402
import mcp_helper_utils     # noqa: E402  （import 可能性確認のみに使用）


def test_mcp_helper_has_do_not_edit_header():
    """生成されたファイルの先頭が DO NOT EDIT ヘッダーであることを確認する。"""
    text = Path(TOOLS_DIR / "mcp_helper.py").read_text(encoding="utf-8")
    assert text.startswith("# DO NOT EDIT"), f"先頭: {text[:100]}"


def test_mcp_helper_imports_from_utils():
    """自動生成ファイルが mcp_helper_utils から _call_tool と _clean_content を import する。"""
    text = Path(TOOLS_DIR / "mcp_helper.py").read_text(encoding="utf-8")
    assert "from mcp_helper_utils import _call_tool, _clean_content" in text


def test_mcp_helper_has_four_public_functions():
    """search / query_db / get_datetime / ping の 4 関数が存在する。claude_code / execute_python は存在しない。"""
    assert callable(mcp_helper.search)
    assert callable(mcp_helper.query_db)
    assert callable(mcp_helper.get_datetime)
    assert callable(mcp_helper.ping)
    assert not hasattr(mcp_helper, "claude_code")
    assert not hasattr(mcp_helper, "execute_python")


def test_ping_calls_call_tool_with_no_args():
    """ping() は _call_tool("ping") を呼ぶ（引数なし passthrough）。"""
    with patch.object(mcp_helper, "_call_tool", return_value={"status": "ok"}) as m:
        result = mcp_helper.ping()
    m.assert_called_once_with("ping")
    assert result == {"status": "ok"}


def test_get_datetime_calls_call_tool_with_no_args():
    """get_datetime() は _call_tool("get_current_datetime") を呼ぶ（引数なし passthrough）。"""
    with patch.object(mcp_helper, "_call_tool", return_value={"date": "2026-04-18"}) as m:
        result = mcp_helper.get_datetime()
    m.assert_called_once_with("get_current_datetime")
    assert result == {"date": "2026-04-18"}


def test_query_db_maps_pool_to_pool_name():
    """query_db(sql, pool) は _call_tool("db_query", {"sql":..., "pool_name":...}) を呼ぶ。"""
    fake_rows = [{"id": 1}, {"id": 2}]
    with patch.object(mcp_helper, "_call_tool", return_value={"rows": fake_rows}) as m:
        result = mcp_helper.query_db("SELECT 1", pool="analytics")
    m.assert_called_once_with("db_query", {"sql": "SELECT 1", "pool_name": "analytics"})
    assert result == fake_rows


def test_query_db_default_pool():
    """query_db の pool デフォルト値が 'default' であることを確認する。"""
    with patch.object(mcp_helper, "_call_tool", return_value={"rows": []}) as m:
        mcp_helper.query_db("SELECT 1")
    m.assert_called_once_with("db_query", {"sql": "SELECT 1", "pool_name": "default"})


def test_query_db_error_passthrough():
    """query_db は _call_tool が error を返した場合 [{error: ...}] を返す。"""
    with patch.object(mcp_helper, "_call_tool", return_value={"error": "boom"}):
        result = mcp_helper.query_db("SELECT 1")
    assert result == [{"error": "boom"}]


def test_search_calls_call_tool_and_cleans_content():
    """search(query) は web_search を呼び、結果の content に _clean_content を適用する。

    _clean_content は `from mcp_helper_utils import ...` 経由で mcp_helper モジュール側に
    バインドされているため、patch.object(mcp_helper, "_clean_content", ...) で差し替える。
    """
    fake_result = {
        "results": [
            {"title": "T", "url": "U", "content": "abc\ncookie notice\ndef"},
        ],
    }
    with patch.object(mcp_helper, "_call_tool", return_value=fake_result) as m:
        results = mcp_helper.search("python 3.12")
    m.assert_called_once_with("web_search", {"query": "python 3.12"})
    assert isinstance(results, list)
    assert results[0]["title"] == "T"
    # cookie notice は skip_patterns に含まれるため除去される（実 _clean_content を通過）
    assert "cookie" not in results[0]["content"].lower()


def test_search_error_passthrough():
    """search は error 時に [{error: ...}] を返す。"""
    with patch.object(mcp_helper, "_call_tool", return_value={"error": "network"}):
        results = mcp_helper.search("foo")
    assert results == [{"error": "network"}]


def test_generator_check_mode_has_no_drift():
    """Plan 03 完了後、scripts/generate_mcp_artifacts.py の build_helper 出力が
    mcp_helper.py とバイト完全一致する（drift なし）。

    Plan 03 は helper のみ上書き — js と docs はまだ差分がある可能性があるため、
    本テストでは helper 単体の一致だけを直接検証する。
    """
    import importlib.util
    repo_root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "generate_mcp_artifacts", repo_root / "scripts" / "generate_mcp_artifacts.py"
    )
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    expected = gen.build_helper(gen.load_tools())
    actual = (TOOLS_DIR / "mcp_helper.py").read_text(encoding="utf-8")
    assert actual == expected, "mcp_helper.py is out of sync with generator output"
