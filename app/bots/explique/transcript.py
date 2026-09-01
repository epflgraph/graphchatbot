from langchain_core.messages import BaseMessage

from app.bots.explique.quiz_page import Quiz
from app.llms.utils import flatten_content


def summarize_quiz(message: BaseMessage) -> BaseMessage:
    """Replace a rendered practice quiz with a summary of the questions it
    asked, leaving every other turn untouched."""
    if message.type != "ai":
        return message

    # Flatten first: content may be multi-part, and quiz markup needs one
    # string to match against.
    questions = Quiz.find_questions(flatten_content(message.content))
    if questions is None:
        return message

    # Copy rather than mutate: `messages` is graph state shared with the nodes
    # running in parallel on this turn.
    return message.model_copy(update={"content": questions.to_summary()})
