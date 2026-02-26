import os
import sys
from pathlib import Path

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.mcp import MCPServerStdio
from crewai import LLM

from src.tools.news_tool import NewsScanTool
from src.tools.weather_tool import WeatherAlertTool

DEFAULT_AGENT_MAX_ITER = int(os.getenv("AGENT_MAX_ITER", "3"))


def _llm():
    """DeepSeek V3 via OpenRouter — completely free, high limits, great tool calling."""
    return LLM(
        model="openrouter/deepseek/deepseek-chat-v3-0324",
        temperature=0.2,
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
    )


_MCP_DIR = str(Path(__file__).parent / "mcp_servers")


@CrewBase
class SupplyChainCrew:

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ── Agents ────────────────────────────────────────────────────────
    @agent
    def global_sentinel(self) -> Agent:
        return Agent(
            config=self.agents_config["global_sentinel"],
            tools=[NewsScanTool(), WeatherAlertTool()],
            llm=_llm(),
            max_iter=DEFAULT_AGENT_MAX_ITER,
            verbose=True,
        )

    @agent
    def inventory_analyst(self) -> Agent:
        logistics_db = MCPServerStdio(
            command=sys.executable,
            args=[os.path.join(_MCP_DIR, "logistics_db_server.py")],
        )
        return Agent(
            config=self.agents_config["inventory_analyst"],
            mcps=[logistics_db],
            llm=_llm(),
            max_iter=DEFAULT_AGENT_MAX_ITER,
            verbose=True,
        )

    @agent
    def mitigation_strategist(self) -> Agent:
        maps_router = MCPServerStdio(
            command=sys.executable,
            args=[os.path.join(_MCP_DIR, "maps_server.py")],
        )
        return Agent(
            config=self.agents_config["mitigation_strategist"],
            mcps=[maps_router],
            llm=_llm(),
            max_iter=DEFAULT_AGENT_MAX_ITER,
            verbose=True,
        )

    # ── Tasks (sequential: detect → analyse → mitigate) ──────────────
    @task
    def detect_threats(self) -> Task:
        return Task(config=self.tasks_config["detect_threats"])

    @task
    def impact_analysis(self) -> Task:
        return Task(config=self.tasks_config["impact_analysis"])

    @task
    def mitigation_plan(self) -> Task:
        return Task(
            config=self.tasks_config["mitigation_plan"],
            output_file="output/crisis_report.md",
        )

    # ── Crew ──────────────────────────────────────────────────────────
    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
