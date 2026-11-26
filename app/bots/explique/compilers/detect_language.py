from app.bots.compilers.detect_language import LanguageDetectorCompiler
from app.bots.explique.compilers.base import ExpliqueCompiler, ExpliqueTask


class LanguageDetectorCompiler(ExpliqueCompiler, LanguageDetectorCompiler):
    """Detects the student's language from their latest turn, read through explique's message callbacks."""

    config = LanguageDetectorCompiler.config.model_copy(update={"task": ExpliqueTask.DETECT_LANGUAGE})
