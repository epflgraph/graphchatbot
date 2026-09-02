from app.bots.course.compilers.respond import GroundedResponseCompiler


class DirectResponseCompiler(GroundedResponseCompiler):
    """Direct answer compiler for the direct course-bot family.

    The family-specific prompt lives at `direct/prompts/respond-sys.md` and is
    resolved through the bot's normal prompt search path.
    """
