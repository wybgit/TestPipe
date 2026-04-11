"""Framework bootstrap helpers."""


def bootstrap() -> None:
    """Import built-in registrations."""
    from testpipe.ops import builtin as _ops_builtin  # noqa: F401
    from testpipe.pipelines import builtin as _pipelines_builtin  # noqa: F401

