#!/usr/bin/env python3
"""docker logs stdout の OTEL span-like JSONL を検索・閲覧する CLI (Phase 31 D-16..D-18)。

stdlib のみで動作する (argparse / json / sys / re / datetime)。
docker compose logs からパイプで流し込んで使う想定:

    docker compose logs api 2>&1 | python3 scripts/trace_query.py
    docker compose logs api 2>&1 | python3 scripts/trace_query.py --trace-id <UUID> --format tree
    docker compose logs --follow api | python3 scripts/trace_query.py --user 0hya6in -f

Design:
- stdin JSONL pass 1 で docker prefix (`api-1  | `) を剥がし、非 JSON 行は silent skip。
- span 判定は {trace_id, span_id, operation_name} の 3 key 存在で行う (Landmine 11.5)。
- streaming 出力 (pretty/tsv/ndjson) は 1 span ごとに emit、tree は全読み込み後 DFS 描画。
- `--since 1h` / `5m` / `30s` / `1d` の相対形式と ISO-8601 UTC の両方をサポート。
- exit code は pipeline を止めないよう原則 0 (入力なし・パース失敗とも 0)。

See:
- .planning/phases/31-agent-mcp-observability/31-RESEARCH.md §6-7
- .planning/phases/31-agent-mcp-observability/31-PATTERNS.md `scripts/trace_query.py`
- app/observability/trace.py  (SpanDict schema, 10 top-level fields)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Iterator, TextIO

# -----------------------------------------------------------------------------
# Span parse helpers
# -----------------------------------------------------------------------------

_SINCE_RE = re.compile(r"^(\d+)([smhd])$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}

_REQUIRED_SPAN_KEYS = frozenset({"trace_id", "span_id", "operation_name"})


def parse_since(value: str) -> datetime:
    """`--since` / `--until` の値を tz-aware UTC datetime に変換する。

    受け付ける形式:
      - 相対: `30s` / `5m` / `1h` / `7d`
      - ISO-8601 UTC: `2026-04-18T12:00:00Z` (Z/+00:00/+09:00 等の tz 指定付き)
        tz 指定なしの ISO 8601 も UTC とみなして tzaware 化する。
    """
    m = _SINCE_RE.match(value.strip())
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        return datetime.now(timezone.utc) - timedelta(seconds=_UNIT_SECONDS[unit] * n)
    iso = value.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def strip_docker_prefix(line: str) -> str:
    """docker compose logs の `api-1  | <log>` prefix を剥がす。

    本体が既に JSON のみの場合は pass-through。
    `" | "` を含まない場合も pass-through (他 logging driver との後方互換)。
    """
    sep = " | "
    if sep in line:
        return line.split(sep, 1)[1]
    return line


def is_span(obj: Any) -> bool:
    """SpanDict schema の最低限 3 キーを満たすか判定 (Landmine 11.5)。"""
    return isinstance(obj, dict) and _REQUIRED_SPAN_KEYS.issubset(obj.keys())


def parse_line(line: str) -> dict | None:
    """1 行を docker prefix strip + JSON decode + span 判定まで行う。

    失敗系 (非 JSON / JSON だが span でない) はすべて None を返す。例外は握り潰す。
    """
    stripped = strip_docker_prefix(line).strip()
    if not stripped.startswith("{"):
        return None
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not is_span(obj):
        return None
    return obj


# -----------------------------------------------------------------------------
# Filter
# -----------------------------------------------------------------------------


def _span_start_dt(span: dict) -> datetime | None:
    s = span.get("start_time")
    if not isinstance(s, str):
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def matches(span: dict, args: argparse.Namespace) -> bool:
    """CLI filter フラグを AND で判定。attribute 経由のフィルタは空 dict でも安全。"""
    attrs = span.get("attributes") or {}
    if args.trace_id and span.get("trace_id") != args.trace_id:
        return False
    if args.user and attrs.get("user_id") != args.user:
        return False
    if args.app and attrs.get("app_id") != args.app:
        return False
    if args.agent and attrs.get("agent_name") != args.agent:
        return False
    if args.tool and attrs.get("tool_name") != args.tool:
        return False
    if args.status and span.get("status_code") != args.status:
        return False
    if args.operation and span.get("operation_name") != args.operation:
        return False
    if args.privileged and not attrs.get("privileged"):
        return False
    if args.min_duration_ms is not None:
        if int(span.get("duration_ms") or 0) < args.min_duration_ms:
            return False
    if args.since is not None:
        dt = _span_start_dt(span)
        if dt is None or dt < args.since:
            return False
    if args.until is not None:
        dt = _span_start_dt(span)
        if dt is None or dt > args.until:
            return False
    return True


# -----------------------------------------------------------------------------
# Output formatters
# -----------------------------------------------------------------------------


def emit_ndjson(span: dict, out: TextIO) -> None:
    """生の span を 1 行 JSON として pass-through (jq 等にチェーン可)。"""
    out.write(json.dumps(span, ensure_ascii=False, default=str))
    out.write("\n")


def _pretty_line(span: dict) -> str:
    op = span.get("operation_name", "?")
    status = span.get("status_code", "?")
    duration = span.get("duration_ms", 0)
    attrs = span.get("attributes") or {}
    trace_id = span.get("trace_id", "")
    short_trace = trace_id.split("-")[0] if trace_id else ""
    parts = [
        f"[{status:<5}]",
        f"{op:<10}",
        f"duration={duration}ms",
        f"trace={short_trace}",
    ]
    for key in ("user_id", "app_id", "agent_name", "tool_name", "model_name"):
        v = attrs.get(key)
        if v is not None and v != "":
            parts.append(f"{key.split('_')[0]}={v}")
    if attrs.get("privileged"):
        parts.append("privileged=true")
    msg = span.get("status_message")
    if msg:
        parts.append(f"msg={str(msg)[:80]}")
    return " ".join(parts)


def emit_pretty(span: dict, out: TextIO) -> None:
    """1 span 1 行の人間可読形式。縦整列 + duration / status を出す。"""
    out.write(_pretty_line(span))
    out.write("\n")


_TSV_COLUMNS = (
    "start_time",
    "trace_id",
    "span_id",
    "parent_span_id",
    "operation_name",
    "status_code",
    "duration_ms",
    "user_id",
    "app_id",
    "agent_name",
    "tool_name",
    "privileged",
    "status_message",
)


def emit_tsv(span: dict, out: TextIO, header_written: list[bool]) -> None:
    """スプレッドシート貼り付け用 TSV。初回だけヘッダを出力する。"""
    if not header_written[0]:
        out.write("\t".join(_TSV_COLUMNS) + "\n")
        header_written[0] = True
    attrs = span.get("attributes") or {}
    row: list[str] = []
    for col in _TSV_COLUMNS:
        if col in ("user_id", "app_id", "agent_name", "tool_name", "privileged"):
            v = attrs.get(col)
        else:
            v = span.get(col)
        if v is None:
            row.append("")
        else:
            # tab / newline を空白に置換して 1 行性を保つ
            s = str(v).replace("\t", " ").replace("\n", " ").replace("\r", " ")
            row.append(s)
    out.write("\t".join(row) + "\n")


def emit_tree(spans: list[dict], trace_id: str | None, out: TextIO) -> None:
    """--trace-id 指定時に親子関係を ASCII tree で表示する。

    未指定の場合は trace_id ごとにグループ化して順次表示する (運用で複数 trace を
    一気に眺めたいときの利便のため)。
    """
    by_trace: dict[str, list[dict]] = {}
    for s in spans:
        by_trace.setdefault(s.get("trace_id", ""), []).append(s)

    if trace_id is not None:
        ids = [trace_id]
    else:
        ids = list(by_trace.keys())

    for idx, tid in enumerate(ids):
        group = by_trace.get(tid, [])
        if idx > 0:
            out.write("\n")
        out.write(f"trace_id: {tid}\n")
        _render_tree(group, out)


def _render_tree(spans: list[dict], out: TextIO) -> None:
    """DFS で tree を描画する (stdlib のみ)。"""
    # children: parent_span_id -> [span, ...]
    # root: group 内に parent が存在しない span (parent_span_id is None or unknown)
    id_set = {s.get("span_id") for s in spans if s.get("span_id")}
    children: dict[str | None, list[dict]] = {}
    roots: list[dict] = []
    for s in spans:
        parent = s.get("parent_span_id")
        if parent is None or parent not in id_set:
            roots.append(s)
        else:
            children.setdefault(parent, []).append(s)

    # 時系列 (start_time) でソートして決定論的に表示
    def _sort_key(sp: dict) -> str:
        return str(sp.get("start_time") or "")

    roots.sort(key=_sort_key)
    for c in children.values():
        c.sort(key=_sort_key)

    def _walk(node: dict, prefix: str, is_last: bool) -> None:
        connector = "└── " if is_last else "├── "
        out.write(prefix + connector + _pretty_line(node) + "\n")
        kids = children.get(node.get("span_id"), [])
        for i, kid in enumerate(kids):
            last = i == len(kids) - 1
            next_prefix = prefix + ("    " if is_last else "│   ")
            _walk(kid, next_prefix, last)

    for i, root in enumerate(roots):
        last = i == len(roots) - 1
        _walk(root, "", last)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="trace_query.py",
        description=(
            "docker logs stdout の OTEL span-like JSONL を検索・閲覧する CLI "
            "(Phase 31 D-16..D-18)。stdin から JSONL を読む。"
        ),
        epilog=(
            "例:\n"
            "  docker compose logs api 2>&1 | python3 scripts/trace_query.py\n"
            "  docker compose logs api 2>&1 | python3 scripts/trace_query.py \\\n"
            "      --trace-id 550e8400-e29b-41d4-a716-446655440000 --format tree\n"
            "  docker compose logs --follow api | python3 scripts/trace_query.py \\\n"
            "      --user 0hya6in --tool web_search -f\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    f = p.add_argument_group("filter (AND)")
    f.add_argument("--trace-id", help="trace_id 一致 (UUID4 推奨)")
    f.add_argument("--user", help="attributes.user_id 一致 (github_login)")
    f.add_argument("--app", help="attributes.app_id 一致 (chat|superchat|canvas|gem|debate)")
    f.add_argument("--agent", help="attributes.agent_name 一致")
    f.add_argument("--tool", help="attributes.tool_name 一致")
    f.add_argument("--status", choices=["OK", "ERROR", "UNSET"], help="status_code 一致")
    f.add_argument(
        "--operation",
        choices=["request", "routing", "sub_agent", "tool_call"],
        help="operation_name 一致",
    )
    f.add_argument(
        "--since",
        type=parse_since,
        metavar="TS",
        help="ISO-8601 or relative (1h/5m/30s/1d)",
    )
    f.add_argument(
        "--until",
        type=parse_since,
        metavar="TS",
        help="ISO-8601 or relative (1h/5m/30s/1d)",
    )
    f.add_argument(
        "--privileged",
        action="store_true",
        help="attributes.privileged == true の span のみ",
    )
    f.add_argument(
        "--min-duration-ms",
        type=int,
        metavar="N",
        help="duration_ms >= N の span のみ",
    )

    o = p.add_argument_group("output")
    o.add_argument(
        "--format",
        choices=["pretty", "tree", "tsv", "ndjson"],
        default="pretty",
        help="出力形式 (default: pretty)",
    )
    o.add_argument(
        "-f",
        "--follow",
        action="store_true",
        help="stdin が EOF にならない限り待ち続ける (docker compose logs -f 対応)",
    )
    o.add_argument(
        "--max",
        type=int,
        metavar="N",
        default=None,
        help="最大 N span で終了 (default: 全件)",
    )
    return p


def _iter_stdin(stream: TextIO, follow: bool) -> Iterator[str]:
    """stdin から 1 行ずつ yield する。follow mode でも差は生まない (python の file-iter
    は EOF まで読む)。将来 tailf-like に変える際のフック点として関数化している。"""
    # `follow` は現状 argparse 可読性のためのフラグ。Python の sys.stdin は
    # tty / pipe どちらでも EOF まで読むので、通常の for 文で十分。
    del follow
    for line in stream:
        yield line


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    out: TextIO = sys.stdout
    header_written = [False]  # TSV 用
    spans: list[dict] = []

    for line in _iter_stdin(sys.stdin, args.follow):
        span = parse_line(line)
        if span is None:
            continue
        if not matches(span, args):
            continue

        if args.format == "tree":
            spans.append(span)
        else:
            if args.format == "ndjson":
                emit_ndjson(span, out)
            elif args.format == "pretty":
                emit_pretty(span, out)
            elif args.format == "tsv":
                emit_tsv(span, out, header_written)
            spans.append(span)  # max 判定用

        if args.max is not None and len(spans) >= args.max:
            break

    if args.format == "tree":
        emit_tree(spans, args.trace_id, out)

    try:
        out.flush()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
