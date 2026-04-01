"""arq worker for async chat processing.

Run with: uv run arq app.jobs.worker.WorkerSettings

The worker runs as a separate process from FastAPI. It initialises
its own Redis client, JobStore, and LangGraph graph per startup.
"""
import os

from arq.connections import RedisSettings
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from redis.asyncio import Redis

from app.graph.builder import build_graph
from app.jobs.job_store import JobStore
from app.jobs.notifier import build_notifier
from app.providers.copilot import ChatCopilot


DB_PATH = os.getenv("CHAT_DB_PATH", "./data/chat.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


async def startup(ctx: dict) -> None:
    """arq on_startup: init Redis client and JobStore."""
    ctx["redis_client"] = Redis.from_url(REDIS_URL)
    ctx["job_store"] = JobStore(ctx["redis_client"])


async def shutdown(ctx: dict) -> None:
    """arq on_shutdown: close Redis connection."""
    await ctx["redis_client"].aclose()


async def process_chat(
    ctx: dict,
    *,
    job_id: str,
    thread_id: str,
    prompt: str,
    model: str = "claude-sonnet-4.5",
    github_token: str,
    reply_to: dict,
) -> dict:
    """arq job function: execute LangGraph and save result.

    Critical ordering: save_result() BEFORE notifier.done()
    so the SSE client can immediately fetch the result.

    Note: github_token is passed in job payload. Acceptable for
    personal tool on localhost. See RESEARCH.md Pitfall 4.
    """
    job_store: JobStore = ctx["job_store"]
    notifier = build_notifier(reply_to, job_store)

    llm = ChatCopilot(github_token=github_token, model=model)

    try:
        async with AsyncSqliteSaver.from_conn_string(DB_PATH) as checkpointer:
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


class WorkerSettings:
    """arq worker configuration.

    Start worker: uv run arq app.jobs.worker.WorkerSettings
    """

    functions = [process_chat]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    job_timeout = 300  # 5 minutes — matches send_and_wait timeout
