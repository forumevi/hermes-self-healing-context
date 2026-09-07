from core.runtime_interceptor import SelfHealingInterceptor
from core.fts5_memory_patcher import MemoryPatcher

class HermesSelfHealingPlugin:
    """
    Main Gateway Plugin entrypoint for Nous Research Hermes Agent.
    """
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.patcher = MemoryPatcher(db_path=self.config.get("db_path"))
        self.interceptor = SelfHealingInterceptor(memory_patcher=self.patcher)

    def on_conversation_loop_start(self, context: dict):
        print("[Hermes-Self-Healing] Engine active. Monitoring execution loop...")

    def wrap_execution(self, func, *args, **kwargs):
        return self.interceptor.execute_with_protection(func, *args, **kwargs)
