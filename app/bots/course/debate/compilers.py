from enum import StrEnum

from app.bots.compilers.base import BotTask
from app.bots.compilers.respond import ResponseCompiler
from app.compilation.base import MessageCompilerConfig, ModelChoice


class DebateStage(StrEnum):
    """How far the debate has progressed. `classify` picks one per turn,
    and each stage gets its own prompt and its own model node."""

    NO_CASE_STUDY = "no-case-study"
    NO_POSITION = "no-position"
    EARLY = "early-stage-debate"
    MID = "mid-stage-debate"
    LATE = "late-stage-debate"
    ENDED = "debate-ended"


def stage_config(stage: DebateStage) -> MessageCompilerConfig:
    return MessageCompilerConfig(
        task=BotTask.RESPOND,
        model_choice=ModelChoice.MAIN,
        overrides=(stage,),
        system_template=f"prompt-{stage}.md",
    )


class NoCaseStudyCompiler(ResponseCompiler):
    """The student has not said which case study they want to discuss."""

    config = stage_config(DebateStage.NO_CASE_STUDY)


class NoPositionCompiler(ResponseCompiler):
    """A case study is chosen, but the student has taken no position on it yet."""

    config = stage_config(DebateStage.NO_POSITION)


class EarlyStageCompiler(ResponseCompiler):
    """Most ideas have yet to be exchanged."""

    config = stage_config(DebateStage.EARLY)


class MidStageCompiler(ResponseCompiler):
    """Some ideas are developed, with more left to discuss."""

    config = stage_config(DebateStage.MID)


class LateStageCompiler(ResponseCompiler):
    """Most ideas are discussed, with little left to explore."""

    config = stage_config(DebateStage.LATE)


class DebateEndedCompiler(ResponseCompiler):
    """The solution has already been revealed in this conversation."""

    config = stage_config(DebateStage.ENDED)


# Which compiler handles each stage, from the `overrides` each one declares.
_COMPILER_BY_STAGE = {
    stage: compiler
    for compiler in (
        NoCaseStudyCompiler,
        NoPositionCompiler,
        EarlyStageCompiler,
        MidStageCompiler,
        LateStageCompiler,
        DebateEndedCompiler,
    )
    for stage in compiler.config.overrides
}


class UnassignedStageError(KeyError):
    """No compiler is assigned to this debate stage."""

    def __init__(self, stage: DebateStage):
        known = [str(stage) for stage in _COMPILER_BY_STAGE]
        super().__init__(f"No compiler for stage {stage!s}. Assigned stages: {known!r}")


def compiler_for(stage: DebateStage) -> type[ResponseCompiler]:
    """The compiler that answers one stage of the debate."""

    compiler = _COMPILER_BY_STAGE.get(stage)
    if compiler is None:
        raise UnassignedStageError(stage)
    return compiler
