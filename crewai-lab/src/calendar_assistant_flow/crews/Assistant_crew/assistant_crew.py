from pathlib import Path
from typing import List, Optional
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from crewai import Agent, Task, LLM
from crewai.project import CrewBase, agent, task

# Paths
ASSISTANT_DIR = Path(__file__).resolve().parent
ASSISTANT_CONFIG = ASSISTANT_DIR / "config"

# Prevent accidental OpenAI/OpenRouter usage
for k in ["OPENAI_API_KEY", "OPENROUTER_API_KEY", "OPENROUTER_API_BASE"]:
    os.environ.pop(k, None)

load_dotenv()

# LLM config
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.1:8b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# Tools
from calendar_assistant_flow.tools.custom_tool import (
    MeetingSchedulerTool,
    TimeAvailabilityTool,
    EventCheckerTool,
)


class MeetingResult(BaseModel):
    status: str
    id: str
    summary: str
    start: str
    end: str
    htmlLink: Optional[str] = None


# ---------- Inline output models (match tasks.yaml exactly) ----------
class MeetingCrafter(BaseModel):
    summary: str = Field(..., description="Meeting title")
    location: str = Field(default="", description="Meeting location")
    description: str = Field(default="", description="Meeting description")
    start: str = Field(..., description="Start time in YYYY-MM-DDTHH:MM:SS")
    end: str = Field(..., description="End time in YYYY-MM-DDTHH:MM:SS")
    attendees: List[str] = Field(default_factory=list, description="Attendee emails")


class DateInterpreter(BaseModel):
    original_query: str
    start: str
    end: str
    timezone: str


@CrewBase
class CalendarAssistant:
    """Calendar Assistant agents + tasks"""

    # IMPORTANT: these must point to valid YAML files
    agents_config = str(ASSISTANT_CONFIG / "agents.yaml")
    tasks_config = str(ASSISTANT_CONFIG / "tasks.yaml")

    # General-purpose Ollama LLM
    llm = LLM(
        provider="ollama",
        model=f"ollama/{LLM_MODEL}",
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",
        temperature=LLM_TEMPERATURE,
    )

    # LLM with tool-calls explicitly disabled to avoid LiteLLM Ollama tool templating bugs
    llm_no_tools = LLM(
        provider="ollama",
        model=f"ollama/{LLM_MODEL}",
        base_url=OLLAMA_BASE_URL,
        api_key="ollama",
        temperature=0.0,
        tool_choice="none",
    )

    # ----------------- Agents -----------------
    @agent
    def meeting_scheduler_assistant(self) -> Agent:
        # JSON crafting only (no tools)
        return Agent(
            config=self.agents_config["meeting_scheduler_assistant"],
            verbose=True,
            llm=self.llm,
            tools=[],
            max_iter=1,
            allow_delegation=False,
        )

    # @agent
    # def meeting_creator_agent(self) -> Agent:
    #     return Agent(
    #         config=self.agents_config["meeting_creator_agent"],
    #         verbose=True,
    #         llm=self.llm_no_tools,
    #         tools=[MeetingSchedulerTool()],
    #         max_iter=1,
    #         allow_delegation=False,
    #         stop_on_tool_output=True,
    #         respond_if_tool_output=True,
    #         auto_terminate=True,
    #         return_direct=True,  # ✅ add this line
    #     )

    @agent
    def meeting_creator_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["meeting_creator_agent"],
            verbose=True,
            llm=self.llm,  # <-- use regular llm
            tools=[MeetingSchedulerTool()],
            max_iter=2,  # <-- allow one extra step to finalize
            allow_delegation=False,
            return_direct=True  # <-- crucial so tool output is the final answer
        )

    @agent
    def availability_checker_assistant(self) -> Agent:
        return Agent(
            config=self.agents_config["availability_checker_assistant"],
            verbose=True,
            llm=self.llm,
            tools=[TimeAvailabilityTool()],
        )

    @agent
    def event_checker_assistant(self) -> Agent:
        return Agent(
            config=self.agents_config["event_checker_assistant"],
            verbose=True,
            llm=self.llm,
            tools=[EventCheckerTool()],
        )

    # ----------------- Tasks -----------------
    @task
    def meeting_crafter_task(self) -> Task:
        return Task(
            config=self.tasks_config["meeting_crafter_task"],
            output_pydantic=MeetingCrafter,
            return_direct=True,
        )

    @task
    def meeting_scheduler_task(self) -> Task:
        return Task(
            config=self.tasks_config["meeting_scheduler_task"],
            output_pydantic=MeetingResult,  # ensure JSON shape
            return_direct=True,
        )

    @task
    def dateinterpreter_task(self) -> Task:
        return Task(
            config=self.tasks_config["dateinterpreter_task"],
            output_pydantic=DateInterpreter,
            return_direct=True,
        )

    @task
    def availability_checker_task(self) -> Task:
        return Task(
            config=self.tasks_config["availability_checker_task"],
            return_direct=True,
        )

    @task
    def event_checker_task(self) -> Task:
        return Task(
            config=self.tasks_config["event_checker_task"],
            return_direct=True,
        )
