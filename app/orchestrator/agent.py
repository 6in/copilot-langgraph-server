from __future__ import annotations
import frontmatter
from pathlib import Path
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.providers.copilot import ChatCopilot
from app.orchestrator.state import AgentState


class SubAgent:
    def __init__(self, name: str, description: str, model: str, system_prompt: str, github_token: str):
        self.name = name
        self.description = description
        self._llm = ChatCopilot(model=model, github_token=github_token)
        self._system_prompt = system_prompt

    @classmethod
    def from_dir(cls, agent_dir: Path, github_token: str) -> "SubAgent":
        post = frontmatter.load(agent_dir / "AGENT.md")
        meta = post.metadata
        return cls(
            name=meta["name"],
            description=meta["description"],
            model=meta.get("model", "claude-sonnet-4-6"),
            system_prompt=post.content,
            github_token=github_token,
        )

    async def run(self, state: AgentState) -> AgentState:
        messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=state["input"]),
        ]
        response = await self._llm.ainvoke(messages)
        return {
            "output": response.content,
            "messages": [AIMessage(content=response.content)],
        }

    async def close(self) -> None:
        await self._llm.close()


class SubAgentRegistry:
    def __init__(self, agent_dir: str, github_token: str):
        self.agents: dict[str, SubAgent] = {}
        self._github_token = github_token
        for path in Path(agent_dir).glob("**/AGENT.md"):
            agent = SubAgent.from_dir(path.parent, github_token)
            self.agents[agent.name] = agent
            print(f"[registry] loaded: {agent.name}")
        if not self.agents:
            print(f"[registry] WARNING: no agents found in {agent_dir}")

    def get(self, name: str) -> SubAgent:
        return self.agents[name]

    def all(self) -> list[SubAgent]:
        return list(self.agents.values())

    async def close(self) -> None:
        for agent in self.agents.values():
            await agent.close()
