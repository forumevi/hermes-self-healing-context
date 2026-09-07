import traceback
from typing import Dict, Any, Callable

class SelfHealingInterceptor:
    """
    Intercepts Hermes Agent execution loops to catch unhandled runtime errors,
    unconfigured mock attributes, and sync/async boundary failures.
    """
    def __init__(self, memory_patcher):
        self.memory_patcher = memory_patcher

    def execute_with_protection(self, target_func: Callable, *args: Any, **kwargs: Any) -> Any:
        try:
            return target_func(*args, **kwargs)
        except TypeError as e:
            err_msg = str(e)
            if any(term in err_msg.lower() for term in ["mock", "unconfigured", "coroutine", "await"]):
                print(f"[Hermes-Self-Healing] Intercepted runtime exception: {err_msg}")
                healed_context = self.memory_patcher.fetch_and_patch_context(
                    error_type="TypeError",
                    error_message=err_msg,
                    traceback_str=traceback.format_exc()
                )
                raise RuntimeHealedException(err_msg, healed_context) from e
            raise e

class RuntimeHealedException(Exception):
    def __init__(self, message: str, context_patch: str):
        super().__init__(message)
        self.context_patch = context_patch
