"""Framework bootstrap helpers."""


def bootstrap() -> None:
    """Import built-in registrations."""
    from testpipe.ops import builtin as _ops_builtin  # noqa: F401
    from testpipe.pipelines import builtin as _pipelines_builtin  # noqa: F401
    from testpipe.skills import builtin as _skills_builtin  # noqa: F401
    from testpipe.templates import builtin as _templates_builtin  # noqa: F401
