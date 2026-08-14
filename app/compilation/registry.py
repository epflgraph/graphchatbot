import logging
from enum import StrEnum

from app.compilation.base import MessageCompiler, Task

logger = logging.getLogger(__name__)


class UndefinedCompilerError(KeyError):
    """No compiler is registered for a task/override pair."""

    def __init__(self, task: Task, override: StrEnum | None):
        super().__init__(
            f"No message compiler registered for task={task!s}, override={override!s}. "
            "Add one to the registry's compiler list."
        )


class CompilerRegistry:
    """Resolves `(task, override)` to a compiler.

    Built from an ordered list of compilers: one declaring no overrides answers
    every lookup for its task, and a later compiler registered under the same
    `(task, override)` replaces an earlier one. Nothing is validated here — a
    compiler's own config validates itself when built; a missing lookup only
    raises from `get`.
    """

    def __init__(self, *compilers: type[MessageCompiler]):
        self._compilers = {}
        for compiler in compilers:
            for override in compiler.config.overrides or (None,):
                self._compilers[(compiler.config.task, override)] = compiler

    def get(self, task: Task, override: StrEnum | None = None) -> type[MessageCompiler]:
        """The compiler for `task`, falling back to its override-less one."""
        for key in ((task, override), (task, None)):
            compiler = self._compilers.get(key)
            if compiler is not None:
                return compiler
        raise UndefinedCompilerError(task, override)

    def describe(self) -> str:
        """The registered mapping, for logging at startup."""
        return "\n".join(
            f"  {task!s}{f'[{override!s}]' if override else ''} -> {compiler.__name__}"
            for (task, override), compiler in self._compilers.items()
        )
