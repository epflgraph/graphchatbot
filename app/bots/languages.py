from pathlib import Path

from app.compilation.templates import render_prompt

# ISO 639-2 for "undetermined": the detector's answer
# when a turn carries no supported language.
UNDETERMINED = "und"

# The languages a bot can be instructed to reply in, ISO code to English name:
# English, plus French, German, Swiss German and Italian. Codes are ISO 639-1
# except `gsw`, which is 639-3; Swiss German has no two-letter code.
LANGUAGES = {
    "en": "English",
    "fr": "French",
    "de": "German",
    "gsw": "Swiss Standard German",
    "it": "Italian",
}

# What the student sees when a model call fails.
NO_ANSWER_TEMPLATE = "no-answer.md"


def no_answer(search_path: tuple[Path, ...], lang_code: str | None) -> str:
    """Canned apology, in the language the turn was written in."""
    return render_prompt(search_path, NO_ANSWER_TEMPLATE, lang_code=lang_code)
