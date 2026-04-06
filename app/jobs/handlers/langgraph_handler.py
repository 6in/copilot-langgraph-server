"""LangGraph chat task handler — extracted from the original process_chat function."""
import json
import os
import re

import psycopg
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.graph.builder import build_graph
from app.jobs.handlers.base import TaskHandler
from app.jobs.notifier import build_notifier
from app.providers.copilot import ChatCopilot

DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")


def extract_html(text: str) -> str:
    """AI 出力からHTMLコードブロックを抽出する。```html で囲まれた部分を返す。"""
    m = re.search(r"```html\n(.*?)```", text, re.DOTALL)
    return m.group(1).strip() if m else text


async def _get_gem_info(thread_id: str, db_uri: str) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    """thread_id から gem_id, gem_type, gem_name, system_prompt, knowledge を取得する。"""
    try:
        async with await psycopg.AsyncConnection.connect(db_uri) as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """SELECT g.gem_id, g.type, g.name, g.system_prompt, g.knowledge
                       FROM threads t
                       LEFT JOIN gems g ON t.gem_id = g.gem_id
                       WHERE t.thread_id = %s""",
                    (thread_id,),
                )
                row = await cur.fetchone()
                if row and row[0] is not None:
                    return str(row[0]), row[1], row[2], row[3], row[4] or ""
    except Exception:
        pass
    return None, None, None, None, None


class LangGraphHandler(TaskHandler):
    """Handles task_type="langgraph": runs the LangGraph StateGraph and saves the AI reply."""

    async def handle(self, ctx: dict, job: dict) -> dict:
        job_id: str = job["job_id"]
        thread_id: str = job["thread_id"]
        prompt: str = job["prompt"]
        model: str = job.get("model", "claude-sonnet-4.5")
        github_token: str = job["github_token"]
        reply_to: dict = job["reply_to"]

        job_store = ctx["job_store"]
        notifier = build_notifier(reply_to, job_store)
        llm = ChatCopilot(github_token=github_token, model=model)

        try:
            async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
                graph = build_graph(llm, checkpointer)
                github_login = job.get("github_login", "unknown")
                config = {"configurable": {"thread_id": thread_id, "github_login": github_login}}

                await notifier.progress("thinking")

                # Gem 情報を取得し、SystemMessage を注入する（Canvas Gem 対応）
                gem_id, gem_type, gem_name, system_prompt, knowledge = await _get_gem_info(thread_id, DB_URI)

                # knowledge が空でなければ system_prompt に結合（Todo 7）
                if system_prompt and knowledge:
                    system_prompt = system_prompt + "\n\n## 知識\n" + knowledge
                elif knowledge and not system_prompt:
                    system_prompt = "## 知識\n" + knowledge

                # メッセージリストを構築（SystemMessage があれば先頭に追加）
                messages_input: list = []
                if system_prompt:
                    messages_input.append(SystemMessage(content=system_prompt))
                messages_input.append(HumanMessage(content=prompt))

                result = await graph.ainvoke(
                    {"messages": messages_input},
                    config=config,
                )
                final_text = result["messages"][-1].content

                # Canvas Gem の場合: HTML 抽出 + canvas_apps upsert + JSON result
                if gem_type == "canvas":
                    html = extract_html(final_text)
                    app_id_str: str | None = None
                    try:
                        async with await psycopg.AsyncConnection.connect(DB_URI) as conn:
                            async with conn.cursor() as cur:
                                await cur.execute(
                                    """INSERT INTO canvas_apps (thread_id, github_login, name, html, source)
                                       VALUES (%s, %s, %s, %s, 'canvas')
                                       ON CONFLICT (thread_id, github_login)
                                       DO UPDATE SET html = EXCLUDED.html, name = EXCLUDED.name
                                       RETURNING app_id""",
                                    (thread_id, github_login, gem_name or "Canvas App", html),
                                )
                                row = await cur.fetchone()
                                if row:
                                    app_id_str = str(row[0])
                            await conn.commit()
                    except Exception:
                        pass  # upsert 失敗は致命的ではない — テキストとして返す

                    if app_id_str:
                        result_payload = json.dumps({"type": "canvas", "app_id": app_id_str, "html": html})
                    else:
                        result_payload = final_text
                else:
                    result_payload = final_text

                # 1. Save result FIRST
                await job_store.save_result(job_id, result_payload)
                # 2. Then signal done
                await notifier.done()

        except Exception as e:
            await job_store.save_result(job_id, f"Error: {e}")
            await notifier.done()
        finally:
            await llm.close()

        return {"job_id": job_id, "status": "done"}
