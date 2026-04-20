#!/usr/bin/env python3
"""Phase 31 Spike: capture ASSISTANT_USAGE / ASSISTANT_REASONING from Copilot SDK.

Purpose
-------
`.planning/phases/31-agent-mcp-observability/31-RESEARCH.md` §5 で VERIFIED になった
Copilot SDK 0.2.0 の ``ASSISTANT_USAGE`` / ``ASSISTANT_REASONING`` / ``ASSISTANT_REASONING_DELTA``
イベントが、実運用に近い ``ChatCopilot.ainvoke`` 経由の呼び出しで実際に発火するかを
複数モデルで確認するための、使い捨てではない常設の調査スクリプト。

Phase 31 Plan 04 が SubAgent span に載せる attribute 名 (input_tokens /
output_tokens / cache_read_tokens / cache_write_tokens / reasoning_chars /
reasoning_prefix のうち取れるもの) を確定する根拠として、結果を
``docs/phase-31-reasoning-token-spike.md`` に記録する。

Usage (docker compose 経由で worker コンテナ内から実行):

    docker compose exec -T worker uv run python /app/scripts/spike_copilot_reasoning.py \
        --model claude-haiku-4-5-20251001 --prompt "東京の今日の天気を短く教えて"

Multi-model loop (plan 記載):

    for MODEL in claude-haiku-4-5-20251001 claude-sonnet-4-6 gpt-4.1; do
        docker compose exec -T worker uv run python /app/scripts/spike_copilot_reasoning.py \
            --model "$MODEL" --prompt "東京の今日の天気を短く教えて"
    done

Output
------
最終行に 1 行 JSON を stdout に emit する:

    {"event":"spike-usage","model":"<model>","usage":{...},"reasoning_count":N,...}

Template reference
------------------
``scripts/probe_sdk_events.py`` の shebang + ``main() -> int`` + ``sys.exit(main())`` 形式を踏襲。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Any

from app.auth.manager import CopilotAuthManager
from app.providers.copilot import ChatCopilot

# SDK-level enum: session event types (see RESEARCH §5.1)
from copilot.generated.session_events import SessionEventType  # type: ignore[import-untyped]

from langchain_core.messages import HumanMessage

logger = logging.getLogger("spike-copilot-reasoning")


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Phase 31 spike: capture Copilot SDK ASSISTANT_USAGE / "
            "ASSISTANT_REASONING events for a single model+prompt invocation."
        )
    )
    p.add_argument(
        "--model",
        default="claude-haiku-4-5-20251001",
        help="Copilot model identifier (default: claude-haiku-4-5-20251001)",
    )
    p.add_argument(
        "--prompt",
        default="東京の今日の天気を短く教えて",
        help="User prompt to send (default: weather-in-Tokyo short probe)",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="session.send_and_wait timeout in seconds (default: 120)",
    )
    return p


async def _run_spike(model: str, prompt: str, timeout: float) -> dict[str, Any]:
    """Invoke ChatCopilot and capture usage / reasoning events via session.on().

    Returns a dict suitable for ``json.dumps``.
    """
    mgr = CopilotAuthManager()
    token = mgr.load_token()
    if not token:
        raise SystemExit(
            "No token found at ~/.copilot_sdk/token.enc — "
            "log in via the Web UI (http://localhost:5173/orochi/) first."
        )

    llm = ChatCopilot(github_token=token, model=model, send_timeout=timeout)

    captured_usage: dict[str, Any] = {}
    captured_reasoning: list[str] = []
    captured_reasoning_deltas: list[str] = []
    # Bonus: the raw event-type counter lets us notice any *other* event we
    # did not expect (e.g. ASSISTANT_REASONING_DONE in future SDK versions).
    event_counts: dict[str, int] = {}

    def on_event(event: Any) -> None:
        etype = getattr(event, "type", None)
        data = getattr(event, "data", None)
        etype_str = str(etype)
        event_counts[etype_str] = event_counts.get(etype_str, 0) + 1

        if etype == SessionEventType.ASSISTANT_USAGE:
            # getattr with None default — all of these fields are `float | None`
            # per SDK dataclass. We record them as-is for the report.
            for field in (
                "input_tokens",
                "output_tokens",
                "cache_read_tokens",
                "cache_write_tokens",
                "conversation_tokens",
                "system_tokens",
                "tool_definitions_tokens",
            ):
                val = getattr(data, field, None)
                # Last-write-wins is fine: per-turn SDK emits at most one
                # ASSISTANT_USAGE event (RESEARCH §5.1).
                captured_usage[field] = val
        elif etype == SessionEventType.ASSISTANT_REASONING:
            rt = getattr(data, "reasoning_text", None)
            rid = getattr(data, "reasoning_id", None)
            ropaque = getattr(data, "reasoning_opaque", None)
            # We keep text only (for the "reasoning_chars" metric).
            if rt:
                captured_reasoning.append(rt)
            # If reasoning_text is absent but reasoning_opaque is present,
            # record the opaque placeholder so the report can distinguish
            # "reasoning existed but body was hidden" from "no reasoning".
            if not rt and ropaque:
                captured_reasoning.append(f"<opaque:{len(str(ropaque))}chars>")
            # rid collected for cross-reference debugging, not aggregated
            if rid:
                logger.debug("spike-reasoning-id model=%s id=%s", model, rid)
        elif etype == SessionEventType.ASSISTANT_REASONING_DELTA:
            delta = getattr(data, "reasoning_text", None) or getattr(data, "delta_content", None)
            if delta:
                captured_reasoning_deltas.append(delta)

    # Monkey-patch create_session so we can register the event handler BEFORE
    # send_and_wait fires. ChatCopilot._agenerate calls create_session itself
    # (we cannot pass session.on() through its public API), so we wrap the
    # underlying client method.
    await llm._ensure_client()  # noqa: SLF001 — spike-only
    orig_create_session = llm._client.create_session  # noqa: SLF001

    async def wrapped_create_session(*args: Any, **kwargs: Any) -> Any:
        session = await orig_create_session(*args, **kwargs)
        session.on(on_event)
        return session

    llm._client.create_session = wrapped_create_session  # noqa: SLF001 — spike-only

    try:
        result = await llm.ainvoke([HumanMessage(content=prompt)])
        # result is an AIMessage; we capture its content length only
        content_len = len(result.content) if isinstance(result.content, str) else 0
        return {
            "event": "spike-usage",
            "model": model,
            "prompt_chars": len(prompt),
            "response_chars": content_len,
            "usage": captured_usage,
            "reasoning_count": len(captured_reasoning),
            "reasoning_total_chars": sum(len(t) for t in captured_reasoning),
            "reasoning_delta_count": len(captured_reasoning_deltas),
            "reasoning_delta_total_chars": sum(len(t) for t in captured_reasoning_deltas),
            # First 200 chars preview — D-13 prefix rule (PII footprint minimised
            # by using a generic weather prompt per T-31-01 mitigation)
            "reasoning_prefix": (
                captured_reasoning[0][:200] if captured_reasoning else None
            ),
            "event_counts": event_counts,
        }
    finally:
        try:
            await llm.close()
        except Exception:  # pragma: no cover — best-effort cleanup
            logger.exception("spike: failed to close ChatCopilot cleanly")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = _build_argparser().parse_args()
    try:
        record = asyncio.run(_run_spike(args.model, args.prompt, args.timeout))
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover — surface on stderr for debug
        logger.exception("spike failed: %s", exc)
        return 1

    # 1-line JSON on stdout for easy grep/jq piping:
    #   docker compose logs worker 2>&1 | grep '"event":"spike-usage"'
    print(json.dumps(record, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
