"""Phase 20 MCP ツール呼び出しインタラクティブテスト。

全 4 スタブツールを呼び出して応答を確認する。

実行方法:
  # worker コンテナ内から（推奨）
  docker compose exec worker uv run python scripts/test_mcp_tools.py

  # ホスト側から（mcp-server のホストポートが公開されている場合 / デバッグ用）
  MCP_SERVER_URL=http://localhost:8001 uv run python scripts/test_mcp_tools.py

オプション:
  --tool <name>   特定のツールのみ実行 (ping / web_search_stub / db_query_stub / claude_code_stub)
  --url <url>     MCP サーバー URL を上書き (デフォルト: 環境変数 MCP_SERVER_URL または http://mcp-server:8001)
  --json          結果を JSON 形式で出力
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import textwrap

from langchain_mcp_adapters.client import MultiServerMCPClient

DEFAULT_MCP_URL = os.environ.get("MCP_SERVER_URL", "http://mcp-server:8001") + "/mcp"

# 各ツールのテスト入力
TOOL_INPUTS: dict[str, dict] = {
    "ping": {},
    "web_search_stub": {"query": "LangGraph MCP integration"},
    "db_query_stub": {"sql": "SELECT * FROM users LIMIT 5"},
    "claude_code_stub": {"command": "ls -la"},
}


async def run_tests(
    tool_filter: str | None,
    mcp_url: str,
    as_json: bool,
) -> int:
    results: list[dict] = []
    failed = 0

    print(f"接続先: {mcp_url}", file=sys.stderr)
    client = MultiServerMCPClient(
        {
            "copilot-tools": {
                "transport": "streamable_http",
                "url": mcp_url,
            }
        }
    )

    tools = await client.get_tools()
    tool_map = {t.name: t for t in tools}
    print(f"取得済みツール: {sorted(tool_map.keys())}\n", file=sys.stderr)

    targets = (
        {tool_filter: tool_map[tool_filter]}
        if tool_filter
        else {k: tool_map[k] for k in TOOL_INPUTS if k in tool_map}
    )

    if tool_filter and tool_filter not in tool_map:
        print(f"エラー: ツール '{tool_filter}' が見つかりません。利用可能: {sorted(tool_map.keys())}")
        return 1

    for name, tool in targets.items():
        inputs = TOOL_INPUTS.get(name, {})
        status = "PASS"
        output = None
        error = None
        try:
            output = await tool.ainvoke(inputs)
        except Exception as exc:
            status = "FAIL"
            error = str(exc)
            failed += 1

        entry = {
            "tool": name,
            "inputs": inputs,
            "status": status,
            "output": output,
            "error": error,
        }
        results.append(entry)

        if not as_json:
            _print_result(entry)

    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    else:
        total = len(results)
        passed = total - failed
        print(f"\n{'=' * 50}")
        print(f"結果: {passed}/{total} 成功" + (f"  ({failed} 失敗)" if failed else ""))

    return 1 if failed else 0


def _print_result(entry: dict) -> None:
    icon = "✓" if entry["status"] == "PASS" else "✗"
    print(f"{icon} {entry['tool']}({_fmt_inputs(entry['inputs'])})")
    if entry["error"]:
        print(f"  エラー: {entry['error']}")
    else:
        output_str = str(entry["output"])
        if len(output_str) > 200:
            output_str = output_str[:200] + "..."
        print(f"  → {output_str}")
    print()


def _fmt_inputs(inputs: dict) -> str:
    if not inputs:
        return ""
    return ", ".join(f"{k}={v!r}" for k, v in inputs.items())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 20 MCP ツール呼び出しテスト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            例:
              # 全ツールテスト（worker コンテナ内）
              docker compose exec worker uv run python scripts/test_mcp_tools.py

              # ping のみ
              docker compose exec worker uv run python scripts/test_mcp_tools.py --tool ping

              # ホスト側から（デバッグ用）
              MCP_SERVER_URL=http://localhost:8001 uv run python scripts/test_mcp_tools.py
        """),
    )
    parser.add_argument("--tool", choices=list(TOOL_INPUTS.keys()), help="特定のツールのみ実行")
    parser.add_argument("--url", default=DEFAULT_MCP_URL, help=f"MCP URL (デフォルト: {DEFAULT_MCP_URL})")
    parser.add_argument("--json", action="store_true", dest="as_json", help="JSON 形式で出力")
    args = parser.parse_args()

    sys.exit(asyncio.run(run_tests(args.tool, args.url, args.as_json)))


if __name__ == "__main__":
    main()
