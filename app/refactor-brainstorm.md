# GraphChatbot Refactor — Brainstorm Notes

## Goals
- Reduce boilerplate: adding a new course bot should take ~30 lines, not ~380
- Single source of truth: a prompt/logic fix should not require editing 10+ files
- Self-contained bots: adding a bot means adding one directory, not scattering files
- Composable architecture: reuse nodes and presets, override only what's needed
- Align with LangGraph best practices

---

## Terminology
- **Bot** replaces "integration"
- Example: "add a new bot for CS-101", `class MATH240(CourseBot)`

---

## Bot Definition
Class-based. A bot declares only what's unique to it:
- `name` — identifier (shown in model dropdown)
- `index` — Elasticsearch/RAG index for document retrieval
- `groups` — EPFL groups with access
- `context` — domain-specific context (course description, URL, syllabus, etc.)
- `style` — behavioral flag, e.g. `"hinting"` vs `"direct"` (maps to pedagogical prompt variants)
- `tools` — which tools the bot has access to

Everything else (graph, nodes, prompt templates, classify logic) comes from the preset.

---

## Architecture: 3 Levels of Composability

```
Level 1 — Primitive nodes (pure functions)
    classify, model, tools, respond, ...

Level 2 — Presets (compose nodes into a standard graph)
    CourseBot, SimpleRAGBot, GraphChatBot, ...

Level 3 — Bots (subclass a preset, provide config)
    MATH240, ENV342, GraphChat, CMi, ...
```

Custom bots that need non-standard behavior subclass `Bot` directly and compose their own graph from Level 1 nodes.

### Base class hierarchy
```
Bot  (base class)
├── CourseBot       ← course tutors
├── SimpleRAGBot    ← domain-specific RAG (CMi, plasma, sac, servicedesk)
├── GraphChatBot    ← EPFL knowledge graph variants
└── ...custom bots...
```

### Nodes
- Pure functions — take state (+ bot config via closure/partial) as input
- Decoupled from the bot class, independently testable
- Bot class owns config and declares its graph; presets wire nodes together

---

## State
- Default `BaseState` extends LangGraph's `MessagesState`
- Fields like `category` and `tools_queue` only present when the graph uses them
- Each preset can define its own state or extend the default

---

## File Structure: By-Bot
Discovery via filesystem scan at startup: any subdirectory of `app/bots/` containing a `bot.py` is registered as a bot. No manual registry, no `__subclasses__()` magic.

```
app/
├── bots/
│   ├── base.py              ← Bot base class
│   ├── nodes/               ← primitive node functions
│   │   ├── classify.py
│   │   ├── model.py
│   │   ├── tools.py
│   │   └── respond.py
│   ├── presets/             ← CourseBot, SimpleRAGBot, GraphChatBot
│   │   ├── course.py
│   │   ├── simple_rag.py
│   │   └── graph_chat.py
│   ├── math240/
│   │   ├── bot.py
│   │   └── tools.py
│   ├── math106e/
│   │   ├── bot.py
│   │   └── tools.py
│   ├── graph_chat/
│   │   ├── bot.py
│   │   └── tools.py
│   └── ...
```

---

## Tools
- All tools move into the by-bot structure
- Bot-specific tools live in `bots/<botname>/tools.py`
- Shared/preset tools live in `bots/presets/` alongside the preset
- Parameterized tools (e.g. `search_course_material`) are shared factory functions that presets bind to the bot's index automatically — bots don't redeclare them
- No MCP server — not enough reuse outside this app to justify the overhead

---

## Prompts
- Preset owns the prompt template structure
- Bot provides the variable parts (context, style) that get injected
- Bots can override a method (e.g. `extra_instructions()`) to inject additional sections without rewriting the whole template
- Shared fragments (pedagogical styles, warnings) stay in a common module

---

## LangGraph Alignment
- Replace `astream_events()` + manual node filtering with `stream_mode="messages"`
- Stateless (no checkpointers) — correct for OpenAI `/chat/completions` compatibility
- No interrupts needed for now
- Per-bot compiled graphs, instantiated at startup (or lazily), reused across requests

---

## Not Changing
- HTTP API remains OpenAI-compatible (`/chat/completions`, request/response schema)

---

## Schemas
- Replace manual `app/schemas/` types with the ones from the `openai` SDK directly (`openai.types.chat`)
- Already a dependency, types are Pydantic v2, compatible with FastAPI
- Stays in sync with OpenAI spec automatically on SDK version bumps
- May still need a thin wrapper for app-specific fields (e.g. auth)

## Still To Decide
- Internal node function signatures (how bot config is injected into pure node functions)
- Whether `style` is an enum or open string
- How graph_chat variants collapse (model-only difference — likely just a class attribute override)
