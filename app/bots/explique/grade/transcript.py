from pathlib import Path

from langchain_core.messages import BaseMessage

from app.bots.explique.grade.prompts import ATTACHMENT_DROPPED_TEMPLATE, JAILBREAK_TEMPLATE
from app.bots.explique.grade.topics import Topic
from app.bots.languages import LANGUAGES
from app.compilation.templates import render_prompt
from app.llms.utils import flatten_content, wrap_content

# How Open WebUI encapsulates an attached file: its text in a source tag, inside a context
# block prepended to the student's turn, whose closing tag is the last thing before the
# student's own words. The source tag comes from Open WebUI's code, the closing one
# from its default retrieval template.
ATTACHMENT_SOURCE_TAG = '<source id="'
ATTACHMENT_END_TAG = "</context>"


def without_attachments(messages: list[BaseMessage], replacement: str) -> list[BaseMessage]:
    """The conversation with every attached file's text replaced by `replacement`.
    The student's own words and photos stay."""
    return [replace_attachments(message, replacement) if message.type == "human" else message for message in messages]


def replace_attachments(message: BaseMessage, replacement: str) -> BaseMessage:
    """`message` with `replacement` instead of the attached file's content; intact when it carries none."""
    parts = wrap_content(message.content)
    texts = [text_after_attachment(part["text"]) if part.get("type") == "text" else None for part in parts]
    if all(text is None for text in texts):
        return message

    replaced = []
    for part, text in zip(parts, texts):
        if text is None:
            replaced.append(part)
        elif text and replacement:
            replaced.append({**part, "text": f"{text}\n\n{replacement}"})
        else:
            replaced.append({**part, "text": text or replacement})
    content = replaced[0]["text"] if isinstance(message.content, str) else replaced
    return message.model_copy(update={"content": content})


def text_after_attachment(text: str) -> str | None:
    """What follows the attached file's wrapper in `text`; None when there is no wrapper."""
    if ATTACHMENT_SOURCE_TAG not in text:
        return None
    _, tag, after = text.rpartition(ATTACHMENT_END_TAG)
    return after.strip() if tag else ""


def graded_turns(search_path: tuple[Path, ...], topic: Topic, messages: list[BaseMessage]) -> list[BaseMessage]:
    """The conversation as the graders read it: an attached file's text is replaced by a
    placeholder, and a jailbreak attempt is left out, and so is the reply, so the instruction
    it carried is never scored."""
    placeholder = render_prompt(search_path, ATTACHMENT_DROPPED_TEMPLATE).strip()
    messages = without_attachments(messages, placeholder)
    templates = tuple(
        render_prompt(search_path, JAILBREAK_TEMPLATE, topic=topic, lang_code=lang_code) for lang_code in LANGUAGES
    )
    no_grade_turns = [
        message.type == "ai" and flatten_content(message.content).startswith(templates) for message in messages
    ]
    return [
        message
        for position, message in enumerate(messages)
        if not no_grade_turns[position] and not (position + 1 < len(messages) and no_grade_turns[position + 1])
    ]
