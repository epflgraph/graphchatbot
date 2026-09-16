from app.bots.compilers.respond import ResponseCompiler


class GroundedResponseCompiler(ResponseCompiler):
    """The reply, grounded in the turns that retrieved its sources.

    The conversation is kept whole: the `search_course_material` calls and
    their results remain real turns in it, so the reply is written right
    after the material it cites.
    """

    config = ResponseCompiler.config.model_copy(update={"system_template": "respond-sys.md"})
