#!/usr/bin/env python3
"""
config/mcp_tools.yaml を読み込み、static/js/iframe-rpc.js の
TOOL_CATALOG ブロックを自動更新するスクリプト。
"""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT / "config" / "mcp_tools.yaml"
JS_PATH = ROOT / "static" / "js" / "iframe-rpc.js"

BEGIN_MARKER = "// --- BEGIN TOOL_CATALOG ---"
END_MARKER = "// --- END TOOL_CATALOG ---"


def load_tools() -> list[dict]:
    with open(YAML_PATH) as f:
        data = yaml.safe_load(f)
    return data["tools"]


def build_block(tools: list[dict]) -> str:
    # --- JSDoc table ---
    lines = [
        BEGIN_MARKER,
        "/**",
        " * Available MCP tools (auto-generated from config/mcp_tools.yaml).",
        " * Use `call(toolName, params)` to invoke.",
        " *",
    ]

    # Calculate column widths
    name_width = max(len(t["name"]) for t in tools)
    name_width = max(name_width, len("Tool"))

    desc_rows: list[str] = []
    for t in tools:
        desc = t["description"]
        if t.get("privileged"):
            desc += " [privileged]"
        desc_rows.append(desc)

    desc_width = max(len(d) for d in desc_rows)
    desc_width = max(desc_width, len("Description"))

    lines.append(
        f" * | {'Tool':<{name_width}} | {'Description':<{desc_width}} |"
    )
    lines.append(
        f" * | {'-' * name_width} | {'-' * desc_width} |"
    )
    for t, desc in zip(tools, desc_rows):
        lines.append(
            f" * | {t['name']:<{name_width}} | {desc:<{desc_width}} |"
        )

    lines.append(" */")

    # --- JS array ---
    entries: list[str] = []
    for t in tools:
        obj: dict = {"name": t["name"], "description": t["description"]}
        if t.get("privileged"):
            obj["privileged"] = True
        # Build object literal manually for readable output
        parts = [f"name: {json.dumps(obj['name'])}"]
        parts.append(f"description: {json.dumps(obj['description'], ensure_ascii=False)}")
        if obj.get("privileged"):
            parts.append("privileged: true")
        entries.append("  { " + ", ".join(parts) + " }")

    lines.append("export const AVAILABLE_TOOLS = [")
    lines.append(",\n".join(entries) + ",")
    lines.append("];")
    lines.append(END_MARKER)

    return "\n".join(lines)


def main() -> None:
    tools = load_tools()
    block = build_block(tools)

    content = JS_PATH.read_text()

    begin_idx = content.find(BEGIN_MARKER)
    end_idx = content.find(END_MARKER)

    if begin_idx == -1 or end_idx == -1:
        raise SystemExit(
            f"Markers not found in {JS_PATH}.\n"
            f"Add '{BEGIN_MARKER}' and '{END_MARKER}' manually first."
        )

    end_idx += len(END_MARKER)
    new_content = content[:begin_idx] + block + content[end_idx:]

    JS_PATH.write_text(new_content)
    print(f"Updated {JS_PATH} with {len(tools)} tools.")


if __name__ == "__main__":
    main()
