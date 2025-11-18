import warnings
import json
from typing import List

from tzlocal import get_localzone
from datetime import datetime
from pydantic import BaseModel

from crewai import Crew, Process
from crewai.flow.flow import Flow, listen, start

from calendar_assistant_flow.crews.Manager_crew.manager_crew import ManagerServiceCrew
from calendar_assistant_flow.crews.Assistant_crew.assistant_crew import CalendarAssistant

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

calendar_assistant = CalendarAssistant()

class CalendarState(BaseModel):
    id: str = "1"
    question: str = (
        "Can you help me check my availability and schedule a meeting with "
        "joe@gmail.com by 9pm today for daily standup."
    )
    chosen_assistant: List[str] = []
    response: List[str] = []
    current_date: str = ""

class CalendarAssistantFlow(Flow[CalendarState]):
    initial_state = CalendarState

    @start()
    def execute_manager(self):
        print("Kickoff the Manager Crew")
        local_tz = get_localzone()
        current_date = str(datetime.now(local_tz).date())

        router_output = (
            ManagerServiceCrew()
            .crew()
            .kickoff(inputs={"question": self.state.question})
        )
        # CrewOutput may be a string or have .raw; normalize to dict
        try:
            raw = router_output if isinstance(router_output, str) else router_output.raw  # type: ignore
        except Exception:
            raw = str(router_output)

        data = json.loads(raw) if isinstance(raw, str) else raw
        agent_name = data["agent"]
        print(f"[router] agent={agent_name} reason={data.get('reason','')}")
        chosen_assistant = [agent_name]

        self.state.chosen_assistant = chosen_assistant
        self.state.current_date = current_date
        print("Selected_assistant:", chosen_assistant)
        return chosen_assistant

    @listen(execute_manager)
    def assistant_crew(self):
        chosen_assistant = [str(x).strip() for x in self.state.chosen_assistant]
        print("Chosen assistants:", chosen_assistant)

        # Map agent constructors
        agent_map = {
            "meeting_scheduler_assistant": calendar_assistant.meeting_scheduler_assistant,
            "availability_checker_assistant": calendar_assistant.availability_checker_assistant,
            "event_checker_assistant": calendar_assistant.event_checker_assistant,
        }

        # Map tasks in sequence per assistant
        task_map = {
            "meeting_scheduler_assistant": [
                calendar_assistant.meeting_crafter_task,
                calendar_assistant.meeting_scheduler_task,
            ],
            "availability_checker_assistant": [
                calendar_assistant.dateinterpreter_task,
                calendar_assistant.availability_checker_task,
            ],
            "event_checker_assistant": [
                calendar_assistant.dateinterpreter_task,
                calendar_assistant.event_checker_task,
            ],
        }

        feedbacks: List[str] = []
        for name in chosen_assistant:
            fn = agent_map.get(name)
            if not fn:
                print(f"No agent ctor for: {name}")
                continue

            agent = fn()
            tasks = [t() for t in task_map.get(name, [])]
            if not tasks:
                print(f"No tasks for: {name}")
                continue

            c = Crew(agents=[agent], tasks=tasks, process=Process.sequential, verbose=True)
            out = c.kickoff(inputs={"question": self.state.question, "current_date": self.state.current_date})
            feedbacks.append(f"{name}: {out}")

        self.state.response = feedbacks

    @listen(assistant_crew)
    def generate_client_response(self):
        return self.state.response

def kickoff():
    flow = CalendarAssistantFlow()
    flow.kickoff()

if __name__ == "__main__":
    kickoff()
