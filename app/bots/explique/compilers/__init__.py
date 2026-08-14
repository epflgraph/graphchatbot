from app.bots.explique.compilers.classify import ClassifyCompiler
from app.bots.explique.compilers.evaluate import EvaluateCompiler
from app.bots.explique.compilers.plan_challenge import PlanChallengeCompiler
from app.bots.explique.compilers.practice import PracticeCompiler
from app.bots.explique.compilers.respond import (
    ContentUnreadableResponseCompiler,
    EndSessionResponseCompiler,
    NewTopicResponseCompiler,
    PracticeUnavailableResponseCompiler,
    SkipResponseCompiler,
    SocialResponseCompiler,
    TutoringResponseCompiler,
)
from app.bots.explique.compilers.retrieve import RetrieveCompiler
from app.bots.explique.compilers.summarize import SummarizeCompiler
from app.bots.explique.compilers.transcribe_image import ImageTranscriptionCompiler
from app.compilation.registry import CompilerRegistry

COMPILERS = CompilerRegistry(
    ImageTranscriptionCompiler,
    ClassifyCompiler,
    RetrieveCompiler,
    EvaluateCompiler,
    PlanChallengeCompiler,
    PracticeCompiler,
    SummarizeCompiler,
    SocialResponseCompiler,
    SkipResponseCompiler,
    NewTopicResponseCompiler,
    EndSessionResponseCompiler,
    PracticeUnavailableResponseCompiler,
    TutoringResponseCompiler,
    ContentUnreadableResponseCompiler,
)
