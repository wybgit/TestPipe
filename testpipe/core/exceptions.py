"""Framework exceptions."""


class TestPipeError(Exception):
    """Base framework exception."""


class ValidationError(TestPipeError):
    """Raised when a spec or config is invalid."""


class PipelineCompileError(TestPipeError):
    """Raised when a pipeline cannot be compiled."""


class StepExecutionError(TestPipeError):
    """Raised when a step fails during execution."""

    def __init__(self, step_name: str, message: str):
        self.step_name = step_name
        super().__init__(f"{step_name}: {message}")
