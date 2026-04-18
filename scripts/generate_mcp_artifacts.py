#!/usr/bin/env python3
"""MCP ツールカタログ用アーティファクト決定論ジェネレータ。

config/mcp_tools.yaml のみを入力にして以下 3 ターゲットを生成する:

- mcp_server/tools/mcp_helper.py       (sandbox から MCP を呼ぶ Python ラッパー)
- static/js/tool-catalog-generated.js  (iframe-rpc.js が import する JS カタログ)
- docs/mcp-tools.md                    (人間向けツール仕様ドキュメント)

実行例:
    python3 scripts/generate_mcp_artifacts.py --target helper   # stdout に Python を出力
    python3 scripts/generate_mcp_artifacts.py --target js       # stdout に JS を出力
    python3 scripts/generate_mcp_artifacts.py --target docs     # stdout に Markdown を出力
    python3 scripts/generate_mcp_artifacts.py --target all      # 3 ファイルをディスクへ書き出し
    python3 scripts/generate_mcp_artifacts.py --check           # drift 検知 (exit 1 if mismatch)

決定論性:
    同一 YAML 入力に対して常に同一バイト列を出力する。build_* の戻り値は末尾に
    単一の `\\n` を持つ (drift 検知の偽陽性回避)。
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT / "config" / "mcp_tools.yaml"
HELPER_PATH = ROOT / "mcp_server" / "tools" / "mcp_helper.py"
JS_PATH = ROOT / "static" / "js" / "tool-catalog-generated.js"
DOCS_PATH = ROOT / "docs" / "mcp-tools.md"

# --- DO NOT EDIT headers (target-specific comment syntax) --------------------

HELPER_HEADER = (
    "# DO NOT EDIT — auto-generated from config/mcp_tools.yaml by scripts/generate_mcp_artifacts.py\n"
    "# To regenerate: python3 scripts/generate_mcp_artifacts.py --target helper\n"
)
JS_HEADER = (
    "// DO NOT EDIT — auto-generated from config/mcp_tools.yaml by scripts/generate_mcp_artifacts.py\n"
    "// To regenerate: python3 scripts/generate_mcp_artifacts.py --target js\n"
)
DOCS_HEADER = (
    "<!-- DO NOT EDIT — auto-generated from config/mcp_tools.yaml by scripts/generate_mcp_artifacts.py -->\n"
    "<!-- To regenerate: python3 scripts/generate_mcp_artifacts.py --target docs -->\n"
)


# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------


def load_tools(yaml_path: Path | None = None) -> list[dict]:
    """config/mcp_tools.yaml を読み込んで tools 配列を返す。"""
    path = yaml_path or YAML_PATH
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["tools"]


# ---------------------------------------------------------------------------
# Python helper generation
# ---------------------------------------------------------------------------


def _format_arg(arg: dict) -> str:
    """python_wrapper.args の 1 エントリを `name: type` or `name: type = default` に整形する。"""
    name = arg["name"]
    type_ = arg["type"]
    if "default" in arg:
        return f"{name}: {type_} = {arg['default']}"
    return f"{name}: {type_}"


def _format_docstring(raw: str, indent: str = "    ") -> str:
    """YAML docstring (複数行 str) を Python 関数本体の docstring ブロックに整形する。

    Returns:
        triple-quote で囲まれた複数行 docstring ブロック (末尾改行なし)。
        例: '    \"\"\"line1\\n    line2\\n    \"\"\"'
    """
    # YAML の | リテラルブロックは末尾改行が残るのでストリップ
    body = raw.rstrip("\n")
    lines = body.split("\n")
    out: list[str] = [f'{indent}"""{lines[0].rstrip()}']
    for line in lines[1:]:
        if line.strip() == "":
            out.append("")
        else:
            out.append(f"{indent}{line}")
    out.append(f'{indent}"""')
    return "\n".join(out)


def _mcp_args_literal(mapping: dict) -> str:
    """mcp_args_mapping を Python dict リテラルに整形する。

    例: {sql: sql, pool: pool_name} → '{"sql": sql, "pool_name": pool}'
    Python 側引数名 (= mapping.value) を Python 識別子、
    MCP 側引数名 (= mapping.key の value) を dict キーにする。

    注: YAML スキーマは {python_arg: mcp_arg_name} を想定。
    db_query 例: pool (Python) → pool_name (MCP) なので YAML では `pool: pool_name`。
    """
    if not mapping:
        return "{}"
    parts: list[str] = []
    for py_arg, mcp_arg in mapping.items():
        parts.append(f'"{mcp_arg}": {py_arg}')
    return "{" + ", ".join(parts) + "}"


def _generate_wrapper_body(tool: dict) -> str:
    """python_wrapper.result_transform.mode に応じて関数本体コードを生成する。

    3 モード:
      - passthrough           : `return _call_tool("<name>")` または引数付き
      - extract_key           : dict → result.get("<key>", [result]) パターン
      - web_search_results    : dict → results[] を取り出し各 item の content に _clean_content を適用

    引数なし (args==[]) かつ passthrough のみ、引数辞書を省略する。
    """
    wrapper = tool["python_wrapper"]
    transform = wrapper.get("result_transform", {})
    mode = transform.get("mode", "passthrough")
    mcp_name = tool["name"]
    mapping = wrapper.get("mcp_args_mapping", {}) or {}
    args_literal = _mcp_args_literal(mapping)
    indent = "    "

    if mode == "passthrough":
        if not mapping:
            return f'{indent}return _call_tool("{mcp_name}")'
        return f'{indent}return _call_tool("{mcp_name}", {args_literal})'

    if mode == "extract_key":
        key = transform["key"]
        return "\n".join(
            [
                f'{indent}result = _call_tool("{mcp_name}", {args_literal})',
                f"{indent}if isinstance(result, dict):",
                f'{indent}    if "error" in result:',
                f'{indent}        return [{{"error": result["error"]}}]',
                f'{indent}    return result.get("{key}", [result])',
                f'{indent}return [{{"error": "unexpected response"}}]',
            ]
        )

    if mode == "web_search_results":
        return "\n".join(
            [
                f'{indent}result = _call_tool("{mcp_name}", {args_literal})',
                f"{indent}if isinstance(result, dict):",
                f'{indent}    if "error" in result:',
                f'{indent}        return [{{"error": result["error"]}}]',
                f'{indent}    raw_results = result.get("results", [result])',
                f"{indent}    for r in raw_results:",
                f'{indent}        if "content" in r:',
                f'{indent}            r["content"] = _clean_content(r["content"])',
                f"{indent}    return raw_results",
                f'{indent}return [{{"error": "unexpected response"}}]',
            ]
        )

    raise ValueError(f"Unknown result_transform.mode: {mode} (tool={mcp_name})")


def build_helper(tools: list[dict]) -> str:
    """mcp_helper.py 全文を生成する。

    Returns:
        str: 末尾に単一の `\\n` を持つ (drift 検知の偽陽性回避)。
    """
    parts: list[str] = []
    parts.append(HELPER_HEADER.rstrip("\n"))
    parts.append(
        '"""mcp_helper — サンドボックス Python コードから MCP ツールを呼び出すヘルパー。\n'
        "\n"
        "このファイルは config/mcp_tools.yaml の python_wrapper ブロックから自動生成されます。\n"
        "手書きヘルパー (_call_tool / _clean_content / _INTERNAL_URL / _TIMEOUT) は\n"
        "mcp_helper_utils.py に分離されています。新規ツール追加時は YAML を編集して\n"
        "`python3 scripts/generate_mcp_artifacts.py --target all` を実行してください。\n"
        '"""'
    )
    parts.append("from mcp_helper_utils import _call_tool, _clean_content  # noqa: F401")

    # 各 python_wrapper を持つツールを YAML 順に生成
    functions: list[str] = []
    for tool in tools:
        wrapper = tool.get("python_wrapper")
        if not wrapper:
            continue
        fn_name = wrapper["function_name"]
        args = wrapper.get("args") or []
        return_type = wrapper.get("return_type", "dict")
        formatted_args = ", ".join(_format_arg(a) for a in args)
        signature = f"def {fn_name}({formatted_args}) -> {return_type}:"
        docstring = _format_docstring(wrapper["docstring"])
        body = _generate_wrapper_body(tool)
        functions.append("\n".join([signature, docstring, body]))

    # ヘッダー + docstring + import の後に空行 2 行、関数間は空行 2 行
    header_block = "\n".join(parts)
    functions_block = "\n\n\n".join(functions)
    text = header_block + "\n\n\n" + functions_block
    return text.rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# JS catalog generation
# ---------------------------------------------------------------------------


def _js_description(tool: dict) -> str:
    """JSDoc テーブルおよび JS description 文字列 (privileged タグ付き) を返す。"""
    desc = tool["description"]
    if tool.get("privileged"):
        desc = f"{desc} [privileged]"
    return desc


def build_js(tools: list[dict]) -> str:
    """tool-catalog-generated.js 全文を生成する。

    Returns:
        str: 末尾に単一の `\\n` を持つ。
    """
    lines: list[str] = []
    lines.append(JS_HEADER.rstrip("\n"))
    lines.append("")

    # --- JSDoc table (sync-tool-list-to-js.py L26-81 と同じカラム計算) ---
    lines.append("/**")
    lines.append(" * Available MCP tools (auto-generated from config/mcp_tools.yaml).")
    lines.append(" * Use `call(toolName, params)` to invoke.")
    lines.append(" *")

    name_width = max(len(t["name"]) for t in tools)
    name_width = max(name_width, len("Tool"))

    desc_rows = [_js_description(t) for t in tools]
    desc_width = max(len(d) for d in desc_rows)
    desc_width = max(desc_width, len("Description"))

    lines.append(
        f" * | {'Tool':<{name_width}} | {'Description':<{desc_width}} |"
    )
    lines.append(
        f" * | {'-' * name_width} | {'-' * desc_width} |"
    )
    for tool, desc in zip(tools, desc_rows):
        lines.append(
            f" * | {tool['name']:<{name_width}} | {desc:<{desc_width}} |"
        )
    lines.append(" */")

    # --- JS array literal ---
    lines.append("export const AVAILABLE_TOOLS = [")
    entries: list[str] = []
    for tool in tools:
        parts: list[str] = []
        parts.append(f"name: {json.dumps(tool['name'])}")
        parts.append(
            f"description: {json.dumps(tool['description'], ensure_ascii=False)}"
        )
        if tool.get("privileged"):
            parts.append("privileged: true")
        entries.append("  { " + ", ".join(parts) + " }")
    lines.append(",\n".join(entries) + ",")
    lines.append("];")

    text = "\n".join(lines)
    return text.rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# Markdown docs generation
# ---------------------------------------------------------------------------


def build_docs(tools: list[dict]) -> str:
    """docs/mcp-tools.md 全文を生成する。

    Returns:
        str: 末尾に単一の `\\n` を持つ。
    """
    lines: list[str] = []
    lines.append(DOCS_HEADER.rstrip("\n"))
    lines.append("")
    lines.append("# MCP Tools Catalog")
    lines.append("")
    lines.append(
        "このドキュメントは `config/mcp_tools.yaml` から自動生成されます。"
        "ツールを追加・変更する場合は YAML を編集し、"
        "`python3 scripts/generate_mcp_artifacts.py --target all` を実行してください。"
    )
    lines.append("")
    lines.append("新規ツール追加手順は [docs/mcp-tool-add-manual.md](./mcp-tool-add-manual.md) を参照。")
    lines.append("")
    lines.append("## ツール一覧")
    lines.append("")
    lines.append("| Tool | Privileged | Sandbox Helper | Description |")
    lines.append("| ---- | ---------- | -------------- | ----------- |")
    for tool in tools:
        name = tool["name"]
        privileged = "yes" if tool.get("privileged") else "no"
        wrapper = tool.get("python_wrapper")
        if wrapper:
            helper = f"`mcp_helper.{wrapper['function_name']}()`"
        else:
            helper = "—"
        desc = tool["description"]
        lines.append(f"| `{name}` | {privileged} | {helper} | {desc} |")
    lines.append("")

    # --- 各ツール詳細セクション ---
    for tool in tools:
        name = tool["name"]
        lines.append(f"## `{name}`")
        lines.append("")
        lines.append(tool["description"])
        lines.append("")
        if tool.get("privileged"):
            lines.append(
                "**Privileged:** このツールは広範な権限を持ちます。"
                "SubAgent が `tools:` に宣言すると SubAgentRegistry が WARNING を出します。"
            )
            lines.append("")
        wrapper = tool.get("python_wrapper")
        if wrapper:
            fn_name = wrapper["function_name"]
            args = wrapper.get("args") or []
            return_type = wrapper.get("return_type", "dict")
            formatted_args = ", ".join(_format_arg(a) for a in args)
            signature = f"def {fn_name}({formatted_args}) -> {return_type}"
            lines.append(f"**Sandbox Helper:** `{signature}`")
            lines.append("")
            docstring_raw = wrapper["docstring"].rstrip("\n")
            lines.append("```")
            for doc_line in docstring_raw.split("\n"):
                lines.append(doc_line)
            lines.append("```")
            lines.append("")
        else:
            exposed = tool.get("sandbox_exposed", True)
            reason = "sandbox 非公開" if exposed is False else "python_wrapper 未定義"
            lines.append(f"**Sandbox Helper:** なし ({reason})")
            lines.append("")

    text = "\n".join(lines)
    return text.rstrip("\n") + "\n"


# ---------------------------------------------------------------------------
# write_all / check_all
# ---------------------------------------------------------------------------


def write_all(tools: list[dict]) -> list[Path]:
    """3 ファイルをディスクへ書き出す。書き出したパスのリストを返す。"""
    helper_text = build_helper(tools)
    js_text = build_js(tools)
    docs_text = build_docs(tools)

    HELPER_PATH.parent.mkdir(parents=True, exist_ok=True)
    JS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOCS_PATH.parent.mkdir(parents=True, exist_ok=True)

    HELPER_PATH.write_text(helper_text, encoding="utf-8")
    JS_PATH.write_text(js_text, encoding="utf-8")
    DOCS_PATH.write_text(docs_text, encoding="utf-8")
    return [HELPER_PATH, JS_PATH, DOCS_PATH]


def _rel_or_abs(path: Path) -> str:
    """path が ROOT 以下なら相対パスを、そうでなければ絶対パスを返す。

    monkeypatch で check_all のパスを tmp_path にすり替えるテストケースや、
    将来的に外部ディレクトリを検査対象にする拡張で ValueError を避けるための保険。
    """
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _check_one(path: Path, expected: str, label: str) -> list[str]:
    """単一ファイルの drift をチェックし、差分行のリストを返す (空なら一致)。"""
    if not path.exists():
        return [f"[drift] missing: {path}"]
    actual = path.read_text(encoding="utf-8")
    if actual == expected:
        return []
    diff = list(
        difflib.unified_diff(
            actual.splitlines(keepends=True),
            expected.splitlines(keepends=True),
            fromfile=f"{label} (on-disk)",
            tofile=f"{label} (expected)",
        )
    )
    return [f"[drift] out of sync: {path}"] + diff


def check_all(tools: list[dict]) -> int:
    """3 ファイルが build_* の結果と一致するかをバイト完全一致で検証する。

    Returns:
        0: 全ファイル一致 (drift なし)
        1: いずれかに drift あり (stderr に unified_diff + Fix 指示を出力)
    """
    helper_text = build_helper(tools)
    js_text = build_js(tools)
    docs_text = build_docs(tools)

    messages: list[str] = []
    messages += _check_one(HELPER_PATH, helper_text, "mcp_helper.py")
    messages += _check_one(JS_PATH, js_text, "tool-catalog-generated.js")
    messages += _check_one(DOCS_PATH, docs_text, "mcp-tools.md")

    if not messages:
        return 0

    for line in messages:
        sys.stderr.write(line if line.endswith("\n") else line + "\n")
    sys.stderr.write(
        "\nFix: python3 scripts/generate_mcp_artifacts.py --target all && git add "
        f"{_rel_or_abs(HELPER_PATH)} {_rel_or_abs(JS_PATH)} {_rel_or_abs(DOCS_PATH)}\n"
    )
    return 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deterministically generate MCP artifacts from config/mcp_tools.yaml."
    )
    parser.add_argument(
        "--target",
        choices=["helper", "js", "docs", "all"],
        default="all",
        help="生成対象 (helper/js/docs は stdout 出力, all はディスクへ書き出し)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="生成結果を on-disk ファイルと比較し、drift を検出したら exit 1",
    )
    args = parser.parse_args(argv)

    tools = load_tools()

    if args.check:
        return check_all(tools)

    if args.target == "helper":
        sys.stdout.write(build_helper(tools))
        return 0
    if args.target == "js":
        sys.stdout.write(build_js(tools))
        return 0
    if args.target == "docs":
        sys.stdout.write(build_docs(tools))
        return 0

    # target == "all" : write to disk
    paths = write_all(tools)
    for p in paths:
        sys.stderr.write(f"wrote {_rel_or_abs(p)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
