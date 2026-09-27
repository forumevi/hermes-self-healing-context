# Hermes Self-Healing Context

An advanced Hermes Agent plugin designed to intercept runtime errors during tool execution and dynamically patch the context window. By leveraging a local SQLite FTS5 memory database, it enables zero-downtime recovery and proactive error handling.

##  Features

- **Runtime Error Interception**: Seamlessly hooks into the `post_tool_call` lifecycle to detect and classify tool execution failures without crashing the agent.
- **Dynamic Context Patching**: Automatically injects targeted system notes into the next LLM call via `pre_llm_call`, guiding the agent to recover gracefully from transient errors.
- **FTS5-Powered Memory**: Utilizes a local SQLite FTS5 database to store, index, and retrieve historical error patterns and successful fix strategies.
- **Proactive Pattern Learning**: Continuously updates its local knowledge base with generic fallbacks and observed error states to improve future recovery attempts.
- **Zero Configuration Required**: Runs out-of-the-box by respecting the `HERMES_HOME` environment variable, requiring no manual database setup.

## 🏗️ Architecture

The plugin is built with a modular, decoupled architecture to ensure stability and ease of maintenance:

| Component | Responsibility |
| --- | --- |
| `plugin.py` | Main entry point. Implements the Hermes Agent standard plugin interface and manages hook registrations. |
| `core/runtime_interceptor.py` | The brain of the operation. Classifies errors, manages the patch generation pipeline, and coordinates with the memory patcher. |
| `core/fts5_memory_patcher.py` | Handles all SQLite FTS5 interactions. Manages lazy database initialization, querying for historical patches, and learning from new outcomes. |
| `core/metrics.py` | Collects performance data (latency, hit rate, error counts) per session for observability. |

##  Installation

1. **Clone the repository** into your Hermes plugins directory:
   ```bash
   cd ~/.hermes/plugins
   git clone https://github.com/forumevi/hermes-self-healing-context.git
