from .plugin import HermesSelfHealingPlugin

def register(ctx):
    """
    Hermes Agent plugin registration entry point.
    """
    plugin = HermesSelfHealingPlugin()
    
    ctx.register_hook("on_session_start", plugin.on_session_start)
    ctx.register_hook("on_session_end", plugin.on_session_end)
    ctx.register_hook("post_tool_call", plugin.post_tool_call)
    ctx.register_hook("pre_llm_call", plugin.pre_llm_call)
