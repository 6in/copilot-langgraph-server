from __future__ import annotations
"""scripts/trace_query.py CLI unit tests (Phase 31 D-16..D-18).

Docker logs stdout に emit された OTEL span-like JSONL を stdin から読み、
filter / format / tree 表示を行う CLI の挙動を検証する。

- stdlib のみを対象 (trace_query.py は外部依存ゼロ)
- sys.stdin / sys.stdout / sys.argv を差し替えて main() を直接呼ぶ
- logger や docker が絡まないため、pytest-asyncio 無しの同期テストで十分
"""

import importlib
import io
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest  # noqa: F401

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _run_cli(jsonl: str, args: list[str]) -> tuple[int, str]:
    """scripts/trace_query.py::main() を stdin/stdout/argv 差し替えで呼び出す。

    importlib.reload を挟むことで、テスト毎にモジュールの ContextVar 的な
    state (もしあれば) を初期化する。
    """
    import trace_query  # type: ignore  # noqa: F401

    importlib.reload(trace_query)
    old_stdin, old_stdout, old_argv = sys.stdin, sys.stdout, sys.argv
    sys.stdin = io.StringIO(jsonl)
    sys.stdout = io.StringIO()
    sys.argv = ["trace_query.py"] + args
    try:
        rc = trace_query.main()
        return (rc or 0), sys.stdout.getvalue()
    finally:
        sys.stdin, sys.stdout, sys.argv = old_stdin, old_stdout, old_argv


def _span_json(
    trace_id: str = "t-1",
    span_id: str | None = None,
    parent: str | None = None,
    op: str = "tool_call",
    user: str = "alice",
    app: str = "chat",
    agent: str = "ag",
    tool: str = "web_search",
    status: str = "OK",
    duration: int = 100,
    privileged: bool = False,
    start: str = "2026-04-18T12:00:00.000000Z",
    end: str = "2026-04-18T12:00:01.000000Z",
) -> str:
    """SpanDict の 10 top-level fields を満たす JSON 1 行を生成。"""
    attrs: dict = {
        "user_id": user,
        "app_id": app,
        "agent_name": agent,
        "tool_name": tool,
        "privileged": privileged,
    }
    return json.dumps({
        "trace_id": trace_id,
        "span_id": span_id or "a" * 16,
        "parent_span_id": parent,
        "operation_name": op,
        "start_time": start,
        "end_time": end,
        "duration_ms": duration,
        "status_code": status,
        "status_message": None,
        "attributes": attrs,
    })


# ---------------------------------------------------------------------------
# filter tests
# ---------------------------------------------------------------------------


def test_filter_by_trace_id():
    jsonl = "\n".join([
        _span_json(trace_id="A", span_id="1" * 16),
        _span_json(trace_id="A", span_id="2" * 16),
        _span_json(trace_id="B", span_id="3" * 16),
    ])
    rc, out = _run_cli(jsonl, ["--trace-id", "A", "--format", "ndjson"])
    assert rc == 0
    assert out.count('"trace_id": "A"') == 2
    assert '"trace_id": "B"' not in out


def test_filter_by_user():
    jsonl = "\n".join([_span_json(user="alice"), _span_json(user="bob")])
    rc, out = _run_cli(jsonl, ["--user", "alice", "--format", "ndjson"])
    assert rc == 0
    assert '"user_id": "alice"' in out
    assert '"user_id": "bob"' not in out


def test_filter_by_status():
    jsonl = "\n".join([
        _span_json(status="OK"),
        _span_json(status="ERROR"),
        _span_json(status="OK"),
    ])
    rc, out = _run_cli(jsonl, ["--status", "ERROR", "--format", "ndjson"])
    assert rc == 0
    assert out.count('"status_code": "ERROR"') == 1


def test_filter_by_operation():
    jsonl = "\n".join([
        _span_json(op="request"),
        _span_json(op="tool_call"),
        _span_json(op="sub_agent"),
    ])
    rc, out = _run_cli(jsonl, ["--operation", "tool_call", "--format", "ndjson"])
    assert rc == 0
    assert '"operation_name": "tool_call"' in out
    assert '"operation_name": "request"' not in out


def test_filter_by_tool_and_agent():
    jsonl = "\n".join([
        _span_json(tool="web_search", agent="researcher"),
        _span_json(tool="db_query", agent="analyst"),
    ])
    rc, out = _run_cli(
        jsonl, ["--tool", "web_search", "--agent", "researcher", "--format", "ndjson"]
    )
    assert rc == 0
    assert out.count("\n") == 1
    assert '"tool_name": "web_search"' in out
    assert '"tool_name": "db_query"' not in out


# ---------------------------------------------------------------------------
# robust parse tests
# ---------------------------------------------------------------------------


def test_strip_docker_prefix():
    raw = _span_json(trace_id="X")
    jsonl = f"api-1  | {raw}\n{raw}\n"
    rc, out = _run_cli(jsonl, ["--trace-id", "X", "--format", "ndjson"])
    assert rc == 0
    assert out.count('"trace_id": "X"') == 2


def test_skip_non_json_lines():
    raw = _span_json(trace_id="X")
    jsonl = (
        "INFO:     127.0.0.1:54321 - GET /health HTTP/1.1 200 OK\n"
        "api-1  | INFO:     Uvicorn running on http://0.0.0.0:8000\n"
        "some totally free text\n"
        + raw
        + "\n"
    )
    rc, out = _run_cli(jsonl, ["--format", "ndjson"])
    assert rc == 0
    assert '"trace_id": "X"' in out


def test_skip_non_span_json():
    # trace_id を持たない JSON 行はスキップされるべき (uvicorn の構造化 access log など)
    non_span = json.dumps({"message": "Started", "level": "INFO"})
    span = _span_json(trace_id="Y")
    jsonl = non_span + "\n" + span + "\n"
    rc, out = _run_cli(jsonl, ["--format", "ndjson"])
    assert rc == 0
    assert '"trace_id": "Y"' in out
    assert '"message": "Started"' not in out


# ---------------------------------------------------------------------------
# format tests
# ---------------------------------------------------------------------------


def test_tree_format_hierarchy():
    jsonl = "\n".join([
        _span_json(trace_id="T", span_id="r" * 16, parent=None, op="request"),
        _span_json(trace_id="T", span_id="o" * 16, parent="r" * 16, op="routing"),
        _span_json(trace_id="T", span_id="s" * 16, parent="r" * 16, op="sub_agent"),
        _span_json(trace_id="T", span_id="t" * 16, parent="s" * 16, op="tool_call"),
    ])
    rc, out = _run_cli(jsonl, ["--format", "tree", "--trace-id", "T"])
    assert rc == 0
    assert "trace_id" in out and "T" in out
    # operation_name 4 種がどれも含まれる
    assert "request" in out
    assert "routing" in out
    assert "sub_agent" in out
    assert "tool_call" in out
    # ASCII tree connector
    assert "├──" in out or "└──" in out


def test_ndjson_passthrough():
    jsonl = _span_json(trace_id="X") + "\n"
    rc, out = _run_cli(jsonl, ["--format", "ndjson"])
    assert rc == 0
    parsed = [json.loads(line) for line in out.strip().splitlines() if line]
    assert len(parsed) == 1
    assert parsed[0]["trace_id"] == "X"


def test_pretty_format_contains_summary():
    jsonl = _span_json(trace_id="P", op="tool_call", tool="web_search", duration=42)
    rc, out = _run_cli(jsonl, ["--format", "pretty"])
    assert rc == 0
    # pretty は 1 span 1 行の人間可読形式: operation_name / duration_ms / status などが見える
    assert "tool_call" in out
    assert "42" in out
    assert "OK" in out


def test_tsv_format_columns():
    jsonl = _span_json(trace_id="TSV", op="tool_call", tool="db_query", duration=123)
    rc, out = _run_cli(jsonl, ["--format", "tsv"])
    assert rc == 0
    # tab 区切りで少なくとも 4 列 (start_time / trace_id / operation / duration 相当) が出る
    assert "\t" in out
    assert "TSV" in out
    assert "tool_call" in out


# ---------------------------------------------------------------------------
# advanced filter tests
# ---------------------------------------------------------------------------


def test_min_duration_filter():
    jsonl = "\n".join([_span_json(duration=50), _span_json(duration=500)])
    rc, out = _run_cli(
        jsonl, ["--min-duration-ms", "100", "--format", "ndjson"]
    )
    assert rc == 0
    assert '"duration_ms": 500' in out
    # 50 は完全に消えていること (部分一致を避けるため `"duration_ms": 50,` 形で確認)
    assert '"duration_ms": 50,' not in out


def test_privileged_flag():
    jsonl = "\n".join([
        _span_json(privileged=True, span_id="p" * 16),
        _span_json(privileged=False, span_id="n" * 16),
    ])
    rc, out = _run_cli(jsonl, ["--privileged", "--format", "ndjson"])
    assert rc == 0
    assert '"privileged": true' in out
    # false は残らない
    assert '"privileged": false' not in out


def test_max_limits_output():
    jsonl = "\n".join([_span_json(span_id=f"{i}" * 16) for i in range(5)])
    rc, out = _run_cli(jsonl, ["--max", "2", "--format", "ndjson"])
    assert rc == 0
    assert out.count("\n") == 2


# ---------------------------------------------------------------------------
# since / until helper tests (parse_since)
# ---------------------------------------------------------------------------


def test_parse_since_relative():
    import trace_query  # type: ignore

    importlib.reload(trace_query)
    now = datetime.now(timezone.utc)
    result = trace_query.parse_since("1h")
    delta = now - result
    assert timedelta(minutes=59) < delta < timedelta(minutes=61)


def test_parse_since_seconds_minutes_days():
    import trace_query  # type: ignore

    importlib.reload(trace_query)
    now = datetime.now(timezone.utc)
    sec = trace_query.parse_since("30s")
    minutes = trace_query.parse_since("5m")
    day = trace_query.parse_since("1d")
    assert timedelta(seconds=29) < (now - sec) < timedelta(seconds=31)
    assert timedelta(minutes=4, seconds=50) < (now - minutes) < timedelta(
        minutes=5, seconds=10
    )
    assert timedelta(hours=23, minutes=59) < (now - day) < timedelta(
        hours=24, minutes=1
    )


def test_parse_since_iso_datetime():
    import trace_query  # type: ignore

    importlib.reload(trace_query)
    result = trace_query.parse_since("2026-04-18T12:00:00Z")
    # 受け入れて tzaware datetime を返せること (tzinfo が UTC)
    assert result.tzinfo is not None
    assert result.year == 2026
    assert result.month == 4
    assert result.day == 18


def test_filter_by_since():
    # 2 span を用意、1 件は古い、1 件は新しい
    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(hours=2)).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )
    new_ts = (now - timedelta(minutes=10)).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )
    jsonl = "\n".join([
        _span_json(trace_id="OLD", start=old_ts, end=old_ts),
        _span_json(trace_id="NEW", start=new_ts, end=new_ts),
    ])
    rc, out = _run_cli(jsonl, ["--since", "1h", "--format", "ndjson"])
    assert rc == 0
    assert '"trace_id": "NEW"' in out
    assert '"trace_id": "OLD"' not in out
