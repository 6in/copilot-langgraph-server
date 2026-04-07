"""DebateGraph task handler — runs turn-based multi-agent debate via DebateGraph.

Security:
    T-17-03: Gem fetch uses is_public OR github_login filter (same as OrchestratorHandler)
    T-17-04: max_turns capped at 20 at handler entry to prevent DoS
    T-17-05: pattern validated against allowed values at handler entry
    T-17-06: KeyError on agent resolution caught and stored as error result
"""
import json
import logging
import os

from langchain_core.messages import AIMessage, HumanMessage

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.jobs.handlers.base import TaskHandler
from app.jobs.notifier import build_notifier
from app.orchestrator.agent import SubAgentRegistry
from app.orchestrator.debate_graph import build_debate_graph
from app.providers.copilot import ChatCopilot

logger = logging.getLogger(__name__)

AGENT_DIR = os.getenv("AGENT_DIR", "./agents")
DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")

_ALLOWED_PATTERNS = frozenset({"debate", "panel", "chain"})


def _build_debate_turns(messages: list) -> list[dict]:
    """AIMessage リストを {name, content} の発言リストに変換する。"""
    return [
        {"name": m.name or "Agent", "content": m.content}
        for m in messages
        if isinstance(m, AIMessage)
    ]


class DebateHandler(TaskHandler):
    """Handles task_type="debate": runs DebateGraph with SubAgent participants."""

    async def handle(self, ctx: dict, job: dict) -> dict:
        job_id: str = job["job_id"]
        thread_id: str = job["thread_id"]
        prompt: str = job["prompt"]
        github_token: str = job["github_token"]
        reply_to: dict = job["reply_to"]

        participants: list[str] = job.get("participants") or []
        pattern: str = job.get("pattern", "debate")
        max_turns: int = min(job.get("max_turns", 3), 20)  # T-17-04: DoS防止
        current_turn: int = job.get("current_turn", 0)
        github_login: str = job.get("github_login", "unknown")
        gem_ids: list[str] = job.get("gem_ids") or []

        # T-17-05: pattern バリデーション
        if pattern not in _ALLOWED_PATTERNS:
            logger.warning("DebateHandler: invalid pattern=%s, defaulting to 'debate'", pattern)
            pattern = "debate"

        job_store = ctx["job_store"]
        notifier = build_notifier(reply_to, job_store)

        # バリデーション: participants + gem_ids の合計が 2 名未満
        # gem_ids はこの後マージされるため、合計数でチェックする
        if len(participants) + len(gem_ids) < 2:
            error_msg = f"Error: participants must have at least 2 agents total (agents + gems), got {len(participants) + len(gem_ids)}"
            await job_store.save_result(job_id, error_msg)
            await notifier.done()
            return {"job_id": job_id, "status": "done"}

        registry = SubAgentRegistry(AGENT_DIR, github_token)

        try:
            await notifier.progress("thinking")

            # gem_ids がある場合は GemSubAgent をマージ (OrchestratorHandler と同パターン, T-17-03)
            if gem_ids:
                try:
                    from app.orchestrator.gem_agent import GemSubAgent
                    import psycopg

                    async with await psycopg.AsyncConnection.connect(DB_URI) as conn:
                        async with conn.cursor() as cur:
                            placeholders = ", ".join(["%s"] * len(gem_ids))
                            await cur.execute(
                                f"""SELECT gem_id, name, system_prompt
                                    FROM gems
                                    WHERE gem_id IN ({placeholders})
                                      AND (is_public = true OR github_login = %s)""",
                                (*gem_ids, github_login),
                            )
                            gem_rows = await cur.fetchall()

                    for row in gem_rows:
                        gem_id_str, gem_name, system_prompt = row
                        gem_agent = GemSubAgent(
                            name=gem_name,
                            system_prompt=system_prompt or "",
                            github_token=github_token,
                        )
                        registry.agents[gem_name] = gem_agent
                        # Gem 名を participants に追加して討論グラフに参加させる
                        if gem_name not in participants:
                            participants.append(gem_name)
                except Exception as e:
                    logger.warning("DebateHandler: gem fetch failed: %s", e)
                    # Gem fetch 失敗後 participants が空なら討論不可 → エラー返却
                    if not participants:
                        error_msg = f"Error: GEM のロードに失敗しました。再試行してください。({e})"
                        await job_store.save_result(job_id, error_msg)
                        await notifier.done()
                        return {"job_id": job_id, "status": "done"}

            # T-17-06: participants でエージェントをフィルター、KeyError をキャッチ
            try:
                agents_map = {name: registry.agents[name] for name in participants}
            except KeyError as missing:
                error_msg = f"Error: agent not found: {missing}. Available: {list(registry.agents.keys())}"
                await job_store.save_result(job_id, error_msg)
                await notifier.done()
                return {"job_id": job_id, "status": "done"}

            # aggregator 用 LLM
            llm = ChatCopilot(github_token=github_token)

            async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
                await checkpointer.setup()
                graph = build_debate_graph(
                    participants,
                    pattern,
                    max_turns,
                    agents_map,
                    llm,
                    checkpointer,
                )

                # initial DebateState
                # Pitfall 2: current_turn > 0 (再エンキュー) の場合 messages は空にして
                # checkpointer が蓄積済みの messages を使う (二重蓄積防止)
                initial = {
                    "turn": current_turn,
                    "max_turns": max_turns,
                    "pattern": pattern,
                    "participants": participants,
                    "messages": [HumanMessage(content=prompt)] if current_turn == 0 else [],
                    "current_agent_idx": current_turn,
                    "awaiting_extension": False,
                }

                config = {"configurable": {"thread_id": thread_id}}

                # astream で各ターンをリアルタイム通知しつつ turns リストを直接蓄積する。
                # aget_state は PostgreSQL チェックポインタからの逆シリアライズで
                # AIMessage 型が失われる場合があるため使用しない。
                all_turns: list[dict] = []
                final_turn = current_turn
                async for state_chunk in graph.astream(initial, config=config):
                    # state_chunk は {node_name: state_delta} の形式 (stream_mode="updates" デフォルト)
                    for node_name, node_state in state_chunk.items():
                        if not isinstance(node_state, dict):
                            continue
                        new_messages = node_state.get("messages", [])
                        if not isinstance(new_messages, list):
                            continue
                        for msg in new_messages:
                            if isinstance(msg, AIMessage):
                                name = msg.name or node_name
                                all_turns.append({"name": name, "content": msg.content})
                                await notifier.send_turn(name, msg.content)
                        # dispatcher がターンカウンターを更新する
                        if "turn" in node_state:
                            final_turn = node_state["turn"]

            turns = all_turns
            summary_text = turns[-1]["content"] if turns else ""
            result_payload = json.dumps({
                "type": "debate_result",
                "debate_text": summary_text,
                "turns": turns,
                "final_turn": final_turn,
                "max_turns": max_turns,
                "is_complete": True,
            })
            await job_store.save_result(job_id, result_payload)
            await notifier.done()

        except Exception as e:
            logger.exception("DebateHandler failed for job %s", job_id)
            await job_store.save_result(job_id, f"Error: {e}")
            await notifier.done()

        finally:
            await registry.close()

        return {"job_id": job_id, "status": "done"}
