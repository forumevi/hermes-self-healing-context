# Hermes Dynamic Self-Healing Context Engine (`hermes-self-healing-context`)

An advanced infrastructure plugin for the **Nous Research Hermes Agent** ecosystem. 

This engine hooks directly into the Hermes execution loop to intercept unhandled runtime errors (such as unconfigured mock attributes and sync/async loop mismatches). It dynamically queries Hermes's long-term **SQLite FTS5 memory** to patch the context window with structural resolution guidelines in real-time.

---

## Key Features

* **Runtime Exception Interception**: Catches edge-case `TypeError` and mock fixture crashes before they break the agentic state.
* **FTS5 Dynamic Context Injection**: Queries local memory stores (`~/.hermes/memory.db`) to extract historical fix patterns.
* **Zero-Downtime Recovery**: Enriches the prompt context with precise structural mitigation steps during failure states.

---

## Architecture

```text
hermes-self-healing-context/
├── plugin.json                 # Hermes Plugin Manifest
├── plugin.py                   # Main Gateway Hook Entrypoint
├── core/
│   ├── runtime_interceptor.py  # Execution Loop Exception Guard
│   └── fts5_memory_patcher.py  # SQLite FTS5 Context Retrieval Engine
└── tests/
    └── test_self_healing.py    # Unit & Integration Tests

## Installation
Clone into your local Hermes plugins directory:
mkdir -p ~/.hermes/plugins
git clone [https://github.com/forumevi/hermes-self-healing-context.git](https://github.com/forumevi/hermes-self-healing-context.git) ~/.hermes/plugins/hermes-self-healing-context

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/forumevi/hermes-self-healing-context/issues).
# Hermes Self-Healing Context Plugin

**Version:** 2.0.0  
**Status:** Production Ready  
**License:** MIT

Advanced self-healing engine for Hermes Agent that intercepts runtime errors, queries FTS5 memory for historical fixes, and dynamically patches the context window for zero-downtime recovery.

## Features

- **Runtime Exception Interception:** Catches TypeError, ConnectionError, and other exceptions before they crash the agent
- **FTS5 Memory Patching:** Queries local SQLite FTS5 database for historical fix patterns
- **Auto-Retry:** Automatically retries transient errors with exponential backoff
- **Pattern Learning:** Learns from successful/unsuccessful patches to improve future recommendations
- **Confidence Scoring:** Provides reliability scores for each fix recommendation
- **Performance Metrics:** Tracks latency, hit rate, and error patterns
- **Security:** SQL injection prevention and input sanitization
- **Graceful Shutdown:** Proper resource cleanup and connection management

## Installation

```bash
git clone https://github.com/forumevi/hermes-self-healing-context.git ~/.hermes/plugins/hermes-self-healing-context
