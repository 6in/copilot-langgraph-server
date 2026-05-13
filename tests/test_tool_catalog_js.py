"""Phase 30 Plan 04: JS カタログ分離後の回帰テスト。

Node を CI に要求しないため Python の正規表現で軽量に検証する。
決定論的な文字列一致は build_js の出力と実ファイル内容を比較して担保する。
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "static" / "js" / "tool-catalog-generated.js"
IFRAME_RPC_PATH = REPO_ROOT / "static" / "js" / "iframe-rpc.js"


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_mcp_artifacts",
        REPO_ROOT / "scripts" / "generate_mcp_artifacts.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_catalog_file_exists():
    assert CATALOG_PATH.exists(), f"missing: {CATALOG_PATH}"


def test_catalog_header_is_do_not_edit():
    text = CATALOG_PATH.read_text(encoding="utf-8")
    assert text.startswith("// DO NOT EDIT"), f"先頭: {text[:100]}"


def test_catalog_exports_available_tools():
    text = CATALOG_PATH.read_text(encoding="utf-8")
    assert text.count("export const AVAILABLE_TOOLS = [") == 1


def test_catalog_contains_eight_tools():
    text = CATALOG_PATH.read_text(encoding="utf-8")
    # 8 つの `name: "...` エントリ（JSON object リテラル内）
    # YAML 順: ping, web_search, db_query, claude_code, execute_python,
    #          get_current_datetime, attachments_list, attachments_extract
    count = len(re.findall(r'\{\s*name:\s*"', text))
    assert count == 8, f"expected 8 tool entries, got {count}"
    assert 'name: "attachments_list"' in text
    assert 'name: "attachments_extract"' in text


def test_catalog_privileged_tools_flagged():
    text = CATALOG_PATH.read_text(encoding="utf-8")
    # claude_code と execute_python の両方に privileged: true
    assert 'name: "claude_code"' in text
    assert 'name: "execute_python"' in text
    # privileged: true が 2 回出現
    assert text.count("privileged: true") == 2


def test_iframe_rpc_no_marker_block():
    text = IFRAME_RPC_PATH.read_text(encoding="utf-8")
    assert "BEGIN TOOL_CATALOG" not in text
    assert "END TOOL_CATALOG" not in text


def test_iframe_rpc_reexports_catalog():
    text = IFRAME_RPC_PATH.read_text(encoding="utf-8")
    assert "from './tool-catalog-generated.js'" in text
    assert "AVAILABLE_TOOLS" in text


def test_iframe_rpc_keeps_handwritten_rpc():
    text = IFRAME_RPC_PATH.read_text(encoding="utf-8")
    # 手書き RPC 関数が回帰していないこと
    assert "export function ai(" in text
    assert "export function query(" in text
    assert "export function call(" in text
    # message listener と pending Map も残っている
    assert "const pending = new Map();" in text
    assert "window.addEventListener('message'" in text


def test_legacy_sync_script_removed():
    legacy = REPO_ROOT / "scripts" / "sync-tool-list-to-js.py"
    assert not legacy.exists(), "scripts/sync-tool-list-to-js.py must be deleted in Plan 04"


def test_catalog_matches_generator_output():
    """drift 検知: build_js(tools) の出力と実ファイル内容が完全一致する。"""
    gen = _load_generator()
    expected = gen.build_js(gen.load_tools())
    actual = CATALOG_PATH.read_text(encoding="utf-8")
    assert actual == expected, "tool-catalog-generated.js is out of sync with generator output"
