# EPFL Graph and CEDE Chatbots

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1C3C3C?logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)

This is the FastAPI backend for the EPFL Graph and CEDE chatbots, developed by the [Center for Digital Education (CEDE)](https://www.epfl.ch/education/educational-initiatives/cede/): a modular framework to build and serve educational tutors, the EPFL Graph chatbot and other administrative RAG assistants. All bots are built with [LangChain](https://python.langchain.com/) and [LangGraph](https://langchain-ai.github.io/langgraph/).

The system is designed around a modular, self-discovering **bot architecture**: each bot is a standalone agent with its own prompts, tools, and conversation graph. New bots are automatically detected at runtime—no manual registration required.

All agents use models from the inference service at EPFL's [Research Computing Platform](https://portal.rcp.epfl.ch), which guarantees that data is never sent to external providers.

---

## Overview

This repository exposes a **FastAPI** application with OpenAI-compatible streaming endpoints that serve a variety of task-specific AI tutors and assistants. Bots can be tailored for:

- **Administrative tasks** (e.g. answering questions about institutional docs via RAG)
- **Course tutoring** (e.g. pedagogical Q&A with classification into theory / practice / admin / unrelated)
- **Custom workflows** (build any LangGraph topology and plug it in)

---

## Project Architecture

```
app/
├── main.py              # FastAPI entry point
├── config.py            # INI + environment variable loading
├── bots/
│   ├── base.py          # Bot ABC, BotState, model configuration
│   ├── registry.py      # Auto-discovery of bot classes via filesystem scanning
│   ├── prompts.py       # Recursive Markdown prompt resolution
│   ├── main.py          # LLM completion / streaming helpers
│   ├── nodes/           # Reusable LangGraph nodes (classify, model, tools)
│   ├── admin/           # AdminBot + concrete admin bots
│   ├── course/          # CourseBot + pedagogical variants
│   └── graph_chat/      # GraphChatBot
├── interfaces/graphai.py # GraphAI RAG client
├── llms/utils.py        # Structured output helpers
└── routers/             # FastAPI public routers
```

### Key Design Decisions

- **Auto-discovery**: Bots are found by scanning `app/bots/` for classes defined in `*_bot.py` files
- **No central registry**: Drop a new bot directory in the right place and restart—the registry picks it up automatically
- **Prompts as Markdown**: Prompts are composed recursively from Markdown fragments, allowing easy inheritance and overrides
- **Stateless graphs**: LangGraph graphs are compiled once at startup (`@cached_property`) and reused per request
- **Streaming-first**: All endpoints support streaming message completion via `stream_mode="messages"`

---

## Getting Started

### Prerequisites

- **Python** >= 3.11
- A running RAG backend (GraphAI / Elasticsearch) if using RAG-enabled bots
- An [RCP API key](https://portal.rcp.epfl.ch)

### Installation

```bash
# Clone the repository
git clone https://github.com/epflgraph/graphchatbot.git
cd graphchatbot

# Create a virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### Configuration

Copy the example configuration file and fill in your credentials:

```bash
cp config.ini.example config.ini
```

Edit `config.ini` to set:
- RCP base url and API key
- GraphAI / Elasticsearch connection details
- Langfuse credentials for tracing

### Running Locally

```bash
# Standard
python -m app.main

# With auto-reload (development)
uvicorn app.main:app --reload --port 8000
```

The API documentation will be available at `http://localhost:8000/docs`.

---

## Adding a New Bot

Creating a new bot requires **zero** modifications to existing code.

1. **Create the bot directory**  
   Inside `app/bots/<category>/<botname>/`, create:
   - `<botname>_bot.py` — class definition
   - `<prompt_file>.md` — system prompt templates for the agent, or omit as needed to fall back to higher-level prompt files
   - `tool_description.md` — tool-calling hints

2. **Pick the right base class**

   | Base Class | Use Case |
   |------------|----------|
   | `AdminBot` | Single-tool RAG bot for institutional docs |
   | `CourseBot` | Course tutor with built-in message classification (theory / practice / admin / unrelated) |
   | `HintingCourseBot` | Course tutor that provides hints instead of direct answers |
   | `DirectCourseBot` | Course tutor that gives direct answers |
   | `Bot` (ABC) | Fully custom LangGraph topology |

   Each bot class **must** define:
   - `name: str` (unique identifier)
   - `groups: list[str]` (authorized user groups; use `[]` for public/unrestricted bots)
   - Any required configuration fields

3. **Restart the application** — the registry auto-discovers and instantiates the bot.

### Prompt Resolution

The built-in prompt system (`app/bots/prompts.py`) composites bot prompts from recursive Markdown fragments:

- `{fragment}` → inline another `.md` file (searched upwards from the bot directory)
- `{{placeholder}}` → dynamic value filled at runtime via `str.format(...)`

---

## Testing

### Inspect a Bot

```python
from app.bots.registry import init_bots, get_bot

init_bots()
bot = get_bot("MY-BOT-NAME")

print(bot.prompt())            # View resolved prompt
print(bot.build_tools())       # Inspect tool schemas
print(bot.graph)               # Verify graph compiles
```

### Run the Test Suite

```bash
make test      # run unittest discover over tests/ with coverage
make lint      # check linting and formatting (no writes)
make lint-fix  # auto-fix lint issues and reformat
```

---

## Development Guidelines

- **Async everywhere**: All node functions and tools must be `async`
- **Python 3.11+ types**: Use `list[str]`, `dict[str, ...]`, `str | None`
- **No hardcoded secrets**: Always pull from `config.ini` / `.env` via `config.get("section", {}).get("key")`
- **Logging**: Use `logging.getLogger(__name__)`; the logging format is configured in `app.logging_config`
