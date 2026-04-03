"""LangGraph chat task handler — extracted from the original process_chat function."""
import os

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.graph.builder import build_graph
from app.jobs.handlers.base import TaskHandler
from app.jobs.notifier import build_notifier
from app.providers.copilot import ChatCopilot

DB_URI = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable")


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
                config = {"configurable": {"thread_id": thread_id}}

                await notifier.progress("thinking")

                result = await graph.ainvoke(
                    {"messages": [HumanMessage(content=prompt)]},
                    config=config,
                )
                final_text = result["messages"][-1].content

                # 1. Save result FIRST
                await job_store.save_result(job_id, final_text)
                # 2. Then signal done
                await notifier.done()

        except Exception as e:
            await job_store.save_result(job_id, f"Error: {e}")
            await notifier.done()
        finally:
            await llm.close()

        return {"job_id": job_id, "status": "done"}
