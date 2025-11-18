# 🚀 CrewAI Calendar Assistant — Multi‑Agent + Google Calendar + Ollama

![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.11-blue)
![CrewAI](https://img.shields.io/badge/CrewAI-MultiAgent-orange)
![Ollama](https://img.shields.io/badge/Ollama-LocalLLM-purple)
![GoogleCalendar](https://img.shields.io/badge/Google-CalendarAPI-lightgrey)

---

# 📌 Overview

This project is a **production‑grade multi‑agent workflow** built using:

- **CrewAI** – Agent orchestration  
- **Ollama** – Local LLM inference (Llama 3.1 8B)  
- **Google Calendar API** – Scheduling, availability, event retrieval  
- **Custom Planning Manager Agent** – Routes requests to the correct specialist agent  
- **Custom Tools** – Python functions exposed as agent tools  
- **Structured Outputs** – Pydantic models for Meeting crafting + date interpretation  

This repository demonstrates a **real‑world agent system**, capable of:

- Understanding user natural language  
- Interpreting dates  
- Checking availability  
- Scheduling meetings  
- Creating Google Calendar events  
- Running local LLM pipelines (offline, secure)  

---

# 🏗️ Architecture Diagram

```mermaid
flowchart TD
    User --> ManagerAgent

    ManagerAgent -->|Classifies Request| meeting_scheduler_assistant
    ManagerAgent --> availability_checker_assistant
    ManagerAgent --> event_checker_assistant
    ManagerAgent --> datetime_interpreter_specialist

    meeting_scheduler_assistant -->|Uses Tool| GoogleCalendarAPI
    availability_checker_assistant -->|Uses Tool| GoogleCalendarAPI
    event_checker_assistant -->|Uses Tool| GoogleCalendarAPI

    subgraph Tools
        MeetingSchedulerTool
        TimeAvailabilityTool
        EventCheckerTool
    end

    meeting_scheduler_assistant --> MeetingSchedulerTool
    availability_checker_assistant --> TimeAvailabilityTool
    event_checker_assistant --> EventCheckerTool

    GoogleCalendarAPI -.-> OAuth
```

---

# 🔁 Sequence Diagram — Full Multi‑Agent Flow

```mermaid
sequenceDiagram
    participant U as User
    participant M as Manager Agent
    participant S as Scheduler Agent
    participant A as Availability Agent
    participant E as Event Checker Agent
    participant G as Google Calendar API

    U->>M: "Schedule meeting with Joe at 9pm"
    M->>M: Classifies request
    M->>S: Delegates scheduling task

    S->>S: Parse + Craft JSON meeting object
    S->>G: createEvent(summary,start,end,attendees)
    G-->>S: Event created

    S-->>U: "Your meeting is scheduled"
```

---

# 🧠 CrewAI Flow Diagram

```mermaid
graph TD
    A[User Input] --> B[Manager Service Crew]
    B --> C{Choose Agent}

    C -->|Meeting| D[Meeting Scheduler Assistant]
    C -->|Availability| E[Availability Checker Assistant]
    C -->|Events| F[Event Checker Assistant]
    C -->|Date Parsing| G[Datetime Interpreter]

    D --> T1[Meeting Scheduler Task]
    E --> T2[Availability Task]
    F --> T3[Event Check Task]
    G --> T4[Date Interpreter Task]

    subgraph Tools
        TS1[MeetingSchedulerTool]
        TS2[TimeAvailabilityTool]
        TS3[EventCheckerTool]
    end

    D --> TS1
    E --> TS2
    F --> TS3
```

---

# 📂 Project Structure

```
crewai-lab/
├── pyproject.toml
├── .gitignore
├── src/
│   └── calendar_assistant_flow/
│       ├── main.py
│       ├── models.py
│       ├── crews/
│       │   ├── Assistant_crew/
│       │   │   ├── assistant_crew.py
│       │   │   ├── config/
│       │   │   │   ├── agents.yaml
│       │   │   │   └── tasks.yaml
│       │   ├── Manager_crew/
│       │   │   ├── manager_crew.py
│       │   │   ├── config/
│       │   │   │   ├── agents.yaml
│       │   │   │   └── tasks.yaml
│       ├── tools/
│           ├── custom_tool.py
│           └── __init__.py
└── README.md
```

---

# ⚙️ Installation

```bash
git clone https://github.com/santoshhub/agentic-ai-lab
cd agentic-ai-lab/crewai-lab
uv venv
uv pip install -r requirements.txt  # or pyproject.toml via uv sync
```

---

# 🔥 Running the Flow

```bash
crewai flow kickoff
```

---

# 🤖 Running Ollama (Required)

Install Ollama:

```bash
brew install ollama
```

Start server:

```bash
ollama serve
```

Download model:

```bash
ollama pull llama3.1:8b
```

Verify:

```bash
curl http://localhost:11434/api/tags
```

---

# 🔐 Google Calendar Setup

1. Visit Google Cloud Console  
2. Enable Calendar API  
3. Create OAuth client ID  
4. Download `credentials.json`  
5. Place it in project root (`crewai-lab/`)  
6. First run triggers OAuth login  
7. Token saved automatically to `token.pickle`

---

# 🧪 Example Flow Request

> "Please schedule a daily standup with joe@gmail.com today at 9pm and check my availability."

System produces structured JSON → schedules the meeting → confirms back.

---

# 🧩 Key Features

- Multi‑agent collaboration  
- Supervisor agent (routing logic)  
- Custom Google Calendar tools  
- Offline LLM reasoning with Ollama  
- Strong structured output enforcement  
- Pydantic typing for deterministic tasks  
- Clean CrewAI orchestration  
- Extendable architecture  

---

# 🛠️ Roadmap

- Add MCP server for exposing tools  
- Add Langfuse tracing  
- Add UI (Streamlit)  

---

# 📄 License

MIT © 2025 Santosh Shahane
