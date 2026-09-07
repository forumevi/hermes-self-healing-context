import pytest
from core.runtime_interceptor import SelfHealingInterceptor, RuntimeHealedException
from core.fts5_memory_patcher import MemoryPatcher

def test_interceptor_catches_unconfigured_mock():
    patcher = MemoryPatcher(db_path=":memory:")
    interceptor = SelfHealingInterceptor(memory_patcher=patcher)

    def broken_mock_function():
        raise TypeError("unconfigured mock attribute '_skill_nudge_interval' accessed")

    with pytest.raises(RuntimeHealedException) as exc_info:
        interceptor.execute_with_protection(broken_mock_function)

    assert "HERMES DYNAMIC SELF-HEALING CONTEXT INJECTED" in exc_info.value.context_patch
    assert "Verify mock fixture initialization" in exc_info.value.context_patch
