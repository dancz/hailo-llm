import os
from .base import BaseRunner
from .mock_runner import MockRunner
# from .hailo_runner import HailoRunner # Will import when implemented

_runner_instance = None

def get_runner() -> BaseRunner:
    global _runner_instance
    if _runner_instance is None:
        # Check environment variable or config to decide runner
        # For now, default to Mock if not specified
        if os.environ.get("USE_HAILO_RUNNER") == "1":
             from .hailo_runner import HailoRunner
             _runner_instance = HailoRunner()
             _runner_instance.load_model("models")
        else:
            _runner_instance = MockRunner()
            _runner_instance.load_model("mock")
    return _runner_instance
