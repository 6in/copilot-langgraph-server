"""Probe: which event types does the Copilot SDK actually emit during send()?

Run inside the worker container:
    docker exec copilot-langgraph-worker-1 uv run python /app/scripts/probe_sdk_events.py
"""
from __future__ import annotations

import asyncio
from collections import Counter

from app.auth.manager import CopilotAuthManager
from copilot import CopilotClient, SubprocessConfig, PermissionHandler  # type: ignore[import-untyped]


async def main() -> None:
    mgr = CopilotAuthManager()
    token = mgr.load_token()
    if not token:
        raise SystemExit("No token found at ~/.copilot_sdk/token.enc — log in via the UI first.")

    client = CopilotClient(SubprocessConfig(github_token=token, use_logged_in_user=False))
    await client.start()
    try:
        session = await client.create_session(
            on_permission_request=PermissionHandler.approve_all,
            model="gpt-4.1",
            streaming=True,
        )

        events_seen: list[tuple[str, int]] = []  # (type, payload_length)
        counter: Counter[str] = Counter()

        def on_event(event):
            etype = getattr(event, "type", None)
            etype_str = str(etype)
            counter[etype_str] += 1
            # Capture payload size for delta-ish events
            data = getattr(event, "data", None)
            content = getattr(data, "content", None) or getattr(data, "delta_content", None) or ""
            events_seen.append((etype_str, len(content) if isinstance(content, str) else 0))

        session.on(on_event)

        prompt = "100文字程度で自己紹介してください。"
        print(f"[PROBE] sending prompt: {prompt!r}")
        await session.send_and_wait(prompt, timeout=120)

        print("\n[PROBE] === event counts ===")
        for etype, count in counter.most_common():
            print(f"  {etype}: {count}")

        print("\n[PROBE] === event sequence (first 30) ===")
        for i, (etype, size) in enumerate(events_seen[:30]):
            print(f"  {i:3d}. {etype} (payload_len={size})")
        if len(events_seen) > 30:
            print(f"  ... ({len(events_seen) - 30} more)")

        await session.disconnect()
    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
