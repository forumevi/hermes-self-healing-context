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
