"""Framework bootstrap helpers."""


def bootstrap() -> None:
    """Import built-in registrations."""
    from testpipe import ops as _ops  # noqa: F401
    from testpipe import pipelines as _pipelines  # noqa: F401
