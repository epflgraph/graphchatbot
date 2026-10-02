# Changelog

## [2.3.0] - 2026-10-02

Version 2.3.0 ships the graded flavour of explique, and gathers what the 2.2.x tags added: new course bots, incident reporting and sturdier shared layers.

`app/bots/explique/` now holds two flavours on one abstract `ExpliqueBot`. `train/` is the flavour that shipped in 2.1.0. `grade/` is its exam-like counterpart: the student picks a topic from a menu, the topic locks, and each explanation is graded against topic points derived once per topic. A covered topic is recorded by adding the student to that topic's Moodle group, through the new client in `app/interfaces/moodle.py`, and a polling task started with the app keeps each graded course's Moodle topic groups in step with its quizzes tagged `[TOPIC:...]`. One graded bot ships, `Explique`.

The request path gains what the graded flavour needs, for every bot. `/chat/completions` reads who is asking from the headers Open WebUI forwards and hands it to the graph as `BotState.requester`. A node can write status events and text to the stream itself, so a reply can show what the bot is doing before its text arrives, and streamed responses send `X-Accel-Buffering: no` so a proxy does not hold them back.

Eight course bots were added — BIO-695, CH-314, EE-310, MATH-101e, MATH-111a, MATH-310, MICRO-303 and MICRO-452. Course bots now keep retrieved documents in tool messages instead of injecting them into the system prompt, deduplicate retrieved chunks, and filter them by the course's language.

Failures are reported and bounded further. Unhandled exceptions and ERROR-level logs go to Sentry when a DSN is configured. A structured-output reply that fails to parse can be retried within the call's timeout, a tool loop batches its calls and answers on its exhausted round, and every stream closes with a `finish_reason` chunk. Each photo in a conversation is transcribed on its own, and the failure apology is a template looked up per bot.

**Upgrading.** The training course bots `explique-cs112g`, `explique-cs202` and `explique-cs233` are removed, so they drop out of `/models`. The `Explique` bot needs a `[moodle]` section with a web-service token in `config.ini`, without which it offers no topics, and Open WebUI must have `ENABLE_FORWARD_USER_INFO_HEADERS` on so the app knows who is asking. `config.ini.example` also gains optional `[sentry]` and `[moodle_polling]` sections. The languages a bot can be told to reply in are narrowed to English, French, German, Swiss Standard German and Italian.

## [2.1.0] - 2026-08-25

Version 2.1.0 ships explique, a family of tutors that teach by having the student explain, and a broad refactor of the layers every bot shares: message compilation, graph nodes, configuration and logging.

`app/bots/explique/` adds bots built on the premise that a student who explains a concept learns more than one who is told it. The tutor asks for an explanation, evaluates it against the course material using a structured model of the student's understanding, and responds by probing, hinting, explaining, motivating or challenging — never by putting the retrieved text in front of the student. A LangGraph pipeline classifies the student's intent, retrieves material on demand, and picks the response from explicit tutor-action rules; ending a session recaps it, citing the material it drew on. Three courses ship with it — CS-112(g), CS-202 and CS-233 — along with photo-upload transcription, a rendered practice-quiz page, and language detection so each session runs in the language the student writes in.

Prompts are now assembled by `app/compilation/` from Jinja templates and YAML example banks rather than concatenated at the call site, and every bot family — `admin`, `course`, `graph_chat` and `explique` — shares the same graph nodes, compilers and artifact base. Configuration is validated against a frozen Pydantic model at startup rather than read as a loose dictionary.

The public routes are additionally served under `/v1` and their completion envelopes now validate against the OpenAI schema, so stock OpenAI clients work against the same handlers. Client-supplied system messages are dropped at the request boundary, so a bot's role can no longer be overridden from outside.

Failures are bounded and reported: every model call, tool loop and retry has an explicit ceiling, a turn that fails answers the client with an error instead of closing the stream in silence, and logging is consistent throughout — warnings are routed through logging rather than stderr, the last `print()` calls in `app/` are gone, and oversized values are truncated so a record stays bounded.

One long-standing bug is fixed in `graph_chat`, where the exercise-set cache was keyed by query alone — a French request following an English one for the same query was served the English set.

**Upgrading.** Configuration is now strict: `[rcp]`, `[elasticsearch]`, `[graphsearch]` and `[graphai]` are required, and an unrecognised section or key raises at startup instead of being ignored. Check an existing `config.ini` against `config.ini.example`, which also gains an optional `[cache]` section for the root of the on-disk caches.

## [2.0.0] - 2026-07-09

Version 2.0.0 ships the refactored `app/bots/` architecture.

The legacy `app/integrations/` system has been replaced by a modular, self-discovering bot framework. Each bot is now a standalone class under `app/bots/`, built from reusable LangGraph nodes and composable Markdown prompts. New bots are detected automatically at runtime by scanning for `*_bot.py` files, with no manual registration required.

Project metadata and descriptions have been updated to reflect this broader scope: a FastAPI backend for the EPFL Graph and CEDE chatbots, serving educational tutors, the EPFL Graph chatbot, and administrative RAG assistants.
