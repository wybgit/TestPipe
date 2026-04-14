"""Framework bootstrap helpers."""


def bootstrap() -> None:
    """Import built-in registrations."""
    from testpipe.ops import artifact as _ops_artifact  # noqa: F401
    from testpipe.ops import asserts as _ops_asserts  # noqa: F401
    from testpipe.ops import atc as _ops_atc  # noqa: F401
    from testpipe.ops import builtin as _ops_builtin  # noqa: F401
    from testpipe.ops import device as _ops_device  # noqa: F401
    from testpipe.ops import resource as _ops_resource  # noqa: F401
    from testpipe.ops import transfer as _ops_transfer  # noqa: F401
    from testpipe.pipelines import atc as _pipelines_atc  # noqa: F401
    from testpipe.pipelines import builtin as _pipelines_builtin  # noqa: F401
    from testpipe.skills import builtin as _skills_builtin  # noqa: F401
    from testpipe.templates import builtin as _templates_builtin  # noqa: F401
