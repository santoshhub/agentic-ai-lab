# manager_crew.py
import os
import requests
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task

# --- Paths ---
MANAGER_DIR = Path(__file__).resolve().parent
MANAGER_CONFIG = MANAGER_DIR / "config"

# --- .env ---
load_dotenv()

# --- Ollama config ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))


def assert_ollama_ready():
    """Fail fast if Ollama is offline or model not installed."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=8)
        r.raise_for_status()
        models = {m.get("name") for m in r.json().get("models", [])}
        if LLM_MODEL not in models:
            raise RuntimeError(
                f"Ollama model '{LLM_MODEL}' not found. Install with: ollama pull {LLM_MODEL}"
            )
    except Exception as e:
        raise RuntimeError(
            f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. Start it with 'ollama serve'."
        ) from e


class RouterDecision(BaseModel):
    agent: Literal[
        "meeting_scheduler_assistant",
        "availability_checker_assistant",
        "event_checker_assistant",
    ] = Field(..., description="Chosen agent to handle the request")
    reason: str = Field(..., description="Short reason for routing")


@CrewBase
class ManagerServiceCrew:
    """Manager / router crew."""

    agents_config = str(MANAGER_CONFIG / "agents.yaml")
    tasks_config = str(MANAGER_CONFIG / "tasks.yaml")

    llm = LLM(
        provider="ollama",
        model=f"ollama/{LLM_MODEL}",
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",   # placeholder
        temperature=0.0,
    )

    @agent
    def project_manager(self) -> Agent:
        return Agent(
            config=self.agents_config["project_manager"],
            verbose=True,
            llm=self.llm,
            allow_delegation=False,
            max_iter=1,
        )

    @task
    def project_manager_task(self) -> Task:
        return Task(
            config=self.tasks_config["project_manager_task"],
            output_pydantic=RouterDecision,
            return_direct=True,
            max_iter=1,
        )

    @crew
    def crew(self) -> Crew:
        assert_ollama_ready()
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
