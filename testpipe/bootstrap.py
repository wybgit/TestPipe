"""Framework bootstrap helpers."""


def bootstrap() -> None:
    """Import built-in registrations."""
    from testpipe import ops as _ops  # noqa: F401
    from testpipe import pipelines as _pipelines  # noqa: F401
    from testpipe.skills import builtin as _skills_builtin  # noqa: F401
    from testpipe.templates import builtin as _templates_builtin  # noqa: F401
