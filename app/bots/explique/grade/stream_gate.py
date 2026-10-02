from collections.abc import Callable

from app.bots.explique.response_evaluator import EvaluatorContext, ResponseEvaluator


class StreamGate:
    """Middleman between a streaming response and the student, holding back what the evaluator could still reject."""

    def __init__(self, context: EvaluatorContext, stream_writer: Callable[[str], None]):
        self.context = context
        self.stream_writer = stream_writer
        self.generated = ""
        # Set once the generated response can no longer be rejected.
        self.is_open = False

    def feed(self, chunk: str) -> None:
        """Take the next streaming chunk, and write whatever cannot be rejected."""
        self.generated += chunk
        if self.is_open:
            self.stream_writer(chunk)
        elif not ResponseEvaluator.may_reject(self.generated, self.context):
            self.is_open = True
            self.stream_writer(self.generated)

    @property
    def streamed(self) -> str:
        """What has reached the student."""
        return self.generated if self.is_open else ""
