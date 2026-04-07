"""GemSubAgent — SubAgent implementation backed by a user-created Gem.

Used by OrchestratorHandler and DebateHandler to inject Gem-defined
system prompts into the multi-agent graph at runtime.
"""

from app.orchestrator.agent import SubAgent

DEFAULT_MODEL = "claude-sonnet-4-6"


class GemSubAgent(SubAgent):
    """A SubAgent whose identity and behaviour come from a Gem record in the DB.

    Unlike file-based SubAgents (loaded from AGENT.md), GemSubAgent is
    constructed at job-intake time using data fetched from PostgreSQL.
    The description is derived from the Gem name so the orchestrator router
    can route user messages to this Gem when it's a better fit.
    """

    def __init__(self, name: str, system_prompt: str, github_token: str, model: str = DEFAULT_MODEL):
        super().__init__(
            name=name,
            description=f"Gem: {name}。ユーザーが招待したカスタムアシスタント。",
            model=model,
            system_prompt=system_prompt,
            github_token=github_token,
        )
