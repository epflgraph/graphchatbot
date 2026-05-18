---
marp: true
theme: default
class: lead
paginate: true
backgroundColor: #f0f4f8
backgroundImage: url('https://marp.app/assets/hero-background.svg')
style: |
  section {
    --h1-color: #0284c7;
    --h2-color: #0369a1;
    --h3-color: #0c4a6e;
    --color-foreground: #1e293b;
    font-family: 'Inter', -apple-system, sans-serif;
  }
  h1 {
    text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
  }
  .highlight {
    color: #e11d48;
    font-weight: bold;
  }
---

# ♻️ **Big refactor chatbot**

---

## ⚠️ **The Problem**

The chatbot had a single shared agent handling every bot:

- All bots shared **the same agent graph** — impossible to give each bot its own conversation structure
- Adding a new bot required **duplicating a lot of code**, with risk of the copies drifting apart over time
- Prompts had **heavy repetition** across bots, with no mechanism for sharing common parts
- Streaming used an older LangGraph API; the refactor adopts current best practices

---

## 🏛️ **Bot Class Hierarchy**

Each bot is now its own class, organised in an inheritance tree:

```
Bot (abstract base)
├── CourseBot              ← Course chatbots
│   ├── HintingCourseBot   ← Hinting style
│   │   └── MATH240Bot
│   └── DirectCourseBot    ← Direct answers
│       └── MATH106eBot
├── AdminBot               ← Admin chatbots
│   ├── LexBot
│   ├── SACBot
│   └── ServicedeskBot
├── GraphChatBot           ← EPFL Graph
└── ...                    ← Any other bot
```

Each level adds specificity. `MATH240Bot` defines only its name, search index, access groups, and tool input schema — **everything else is inherited**.

Changing shared behaviour at any level **propagates automatically**.

---

## ⚙️ **Graph Node Composition**

Each bot assembles its own conversation flow from reusable nodes:

- **`classify`** — classifies the user's message into a category (greeting, theory, practice, admin, unrelated) using a lightweight model call; sets whether tools should be forced
- **`model`** — calls the main LLM with the bot's prompt and conversation history; optionally binds tools
- **`tools`** — executes tool calls and loops back to `model`

A course bot's graph is: `classify → model ⇄ tools`.
An admin bot can use a different arrangement or skip classify entirely.
A debate partner chatbot can reuse some parts and/or override this structure completely.

**Nodes are shared building blocks** — bots personalise the wiring, not the node code.

---

## 🔧 **Tools**

**Old system:**
- All bots shared the same fixed tool set, resolved on every model invocation
- Complicated `tools_queue` approach: a list of tool names to be used in order

**New system:**
- Idea: Bots define their own tools separately (kind of plug-and-play, like for MCP).
- `tools_queue` replaced by a single `force_tools: bool`, set by `classify` and cleared after use
- Simplified inheritance of tools leveraging the bots architecture.
- Tool description is composed via `.md` files, exactly like prompts (hierarchically).

---

## 🧩 **Prompt Composition**

Each bot's prompt is built from `.md` files, resolved by walking up the folder tree.

- Shared guidelines live at the root and apply to every bot automatically
- Each level can define or override any piece (behavior, format, pedagogy)
- A bot only needs to provide what makes it **specific** — everything else is inherited
- `{placeholder}` syntax pulls in the nearest matching file up the tree

---

## 🧩 **Prompt Composition — Example**

```
bots/
├── general_considerations.md      ← "If the user asks inappropriate questions..."
└── course/
    ├── format.md                  ← "Format your answer using
    │                                 Markdown (e.g., math, links, ..."
    ├── prompt.md                  ← "You are a tutor for {course_name}...
    │                                 {coursebook}
    │                                 {pedagogical_considerations}
    │                                 {format}
    │                                 {general_considerations}"
    └── hinting/
        ├── pedagogical_considerations.md   ← Hinting style
        └── math240/
            ├── course_name.md     ← "Statistique (MATH-240)"
            └── coursebook.md      ← "Statistique
                                      MATH-240 / 5 crédits
                                      Teacher: Panaretos Victor
                                      Langue: Français
                                      Résumé
                                      Ce cours donne une introduction..."
```

---

## 🏗️ **Current State**

**Done:**
- All infrastuctural changes that allow the new bots architecture.
- 5 bots registered and serving on new endpoints (`/chat/completions_new`, `/models_new`)
- New endpoints live alongside old ones — no disruption to existing users

**Still in progress:**
1. Transfer the rest of bots, including GraphChat.
2. Swap old endpoints to point to the new bot system.
3. Deploy on test and check with Thijs.
4. Old code cleanup.
5. [later] Completely bypass EPFL groups, auth, etc. by delegating to OpenWebUI.
