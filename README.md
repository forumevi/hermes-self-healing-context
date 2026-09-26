# Hermes Self-Healing Context Plugin

**Version:** 2.0.0  
**Status:** Production Ready  
**License:** MIT  
**Author:** forumevi

---

## Overview

Advanced self-healing engine for Hermes Agent that intercepts runtime errors, queries FTS5 memory for historical fixes, and dynamically patches the context window for zero-downtime recovery.

When Hermes Agent encounters an unhandled exception (TypeError, ConnectionError, mock fixture crashes, etc.), this plugin:
1. **Intercepts** the error before it crashes the agent state
2. **Queries** local SQLite FTS5 memory (`~/.hermes/memory.db`) for historical fix patterns
3. **Injects** structural mitigation steps into the context window in real-time
4. **Learns** from successful/unsuccessful patches to improve future recommendations

**No external dependencies** — uses only Python stdlib (`sqlite3`, `ast`, `traceback`).

---

## Features

### Core Capabilities
- **Runtime Exception Interception** — Catches TypeError, ConnectionError, and other exceptions before they break the agentic state
- **FTS5 Dynamic Context Injection** — Queries local memory stores for historical fix patterns
- **Zero-Downtime Recovery** — Enriches the prompt context with precise structural mitigation steps during failure states
- **Auto-Retry for Transient Errors** — Exponential backoff for ConnectionError, TimeoutError, RateLimitError

### Advanced Features
- **Error Pattern Learning** — Learns from successful/unsuccessful patches to improve future recommendations
- **Confidence Scoring** — Provides reliability scores (0-100%) for each fix recommendation
- **Performance Metrics** — Tracks latency, hit rate, and error patterns per session
- **SQL Injection Prevention** — Input sanitization for FTS5 MATCH queries
- **Connection Pooling** — Reuses SQLite connections with graceful shutdown

---

## Installation

### Option 1: Git Clone (Recommended)
Option 2: Pip Install (Future)
bash

1 pip install hermes-self-healing-context
Verification
After installation, restart Hermes Agent. You should see: 
[Hermes-Self-Healing] Plugin initialized with advanced features:
  - Error pattern learning: ENABLED
  - Auto-retry for transient errors: ENABLED
  - Performance metrics tracking: ENABLED
  - Confidence scoring: ENABLED

    Usage
The plugin automatically activates when Hermes Agent starts. No configuration required.
How It Works
Error Occurs: Hermes Agent encounters an unhandled exception during tool execution
Interception: SelfHealingInterceptor catches the error and classifies it (transient vs permanent)
Memory Query: MemoryPatcher queries FTS5 database for similar historical errors
Context Patch: If a fix pattern is found, it's injected into the next LLM call's context
Learning: The outcome (success/failure) is recorded for future recommendations
Example Scenario
User: "Search for recent papers on quantum computing"
Agent: [Calls search tool]
Error: ConnectionError: Network unreachable

[Hermes-Self-Healing] Generated context patch for: ConnectionError
[Hermes-Self-Healing] Injected patches into context

Agent: [Retries with proxy configuration from historical fix]
Success: Found 15 papers on quantum computing

Configuration (Optional)
Default configuration works out of the box. Advanced users can customize via plugin.json or environment variables:
{
  "db_path": "~/.hermes/memory.db",
  "enable_learning": true,
  "auto_retry": true,
  "max_retries": 2,
  "max_cache_size": 1000,
  "cache_ttl": 300
}
Configuration Options
Option
Type
Default
Description
db_path
string
~/.hermes/memory.db
Path to SQLite FTS5 database
enable_learning
bool
true
Learn from patch outcomes
auto_retry
bool
true
Retry transient errors automatically
max_retries
int
2
Maximum retry attempts for transient errors
max_cache_size
int
1000
Maximum cached query results
cache_ttl
int
300
Cache time-to-live in seconds
Architecture

12345678910111213
Component Responsibilities
Component
Responsibility
plugin.py
Implements Hermes Agent's standard plugin interface (on_session_start, post_tool_call, pre_llm_call, etc.)
runtime_interceptor.py
Classifies errors (transient vs permanent), manages auto-retry with exponential backoff
fts5_memory_patcher.py
Queries SQLite FTS5 for similar errors, generates context patches with confidence scores
error_analyzer.py
Tracks error frequency, detects recurring patterns, provides proactive recommendations
metrics.py
Collects performance data (latency, hit rate, error counts) per session
Testing
Run All Tests
bash

12
Expected Output

12345
Test Coverage
✅ Plugin initialization and configuration
✅ Session lifecycle hooks (start/end)
✅ Exception interception (happy path + error path)
✅ FTS5 INSERT/SELECT operations
✅ Auto-retry for transient errors
✅ Cache hit/miss scenarios
✅ Graceful shutdown (connection cleanup)
✅ SQL injection prevention
✅ Error pattern analysis
✅ Performance metrics tracking
Plugin Catalog Submission
This plugin is submitted to the Nous Research Hermes Agent Plugin Catalog.
Name: hermes-self-healing-context
Category: stability
Tags: memory, self-healing, runtime, context-engine, fts5, auto-retry, pattern-learning, metrics
Compatibility: Linux, macOS, Windows | Hermes Agent >= 0.1.0
Contributing
Contributions, issues, and feature requests are welcome!
Development Setup
bash

123
Pull Request Process
Fork the repository
Create a feature branch (git checkout -b feature/amazing-feature)
Commit your changes (git commit -m 'Add amazing feature')
Push to the branch (git push origin feature/amazing-feature)
Open a Pull Request
Code Style
Follow PEP 8
Add type hints to all function signatures
Include docstrings for all public methods
Write tests for new features
Ensure all tests pass before submitting PR
Changelog
v2.0.0 (2026-09-27)
Added: Error pattern learning with confidence scoring
Added: Auto-retry for transient errors with exponential backoff
Added: Performance metrics tracking (latency, hit rate)
Added: SQL injection prevention and input sanitization
Added: Connection pooling and graceful shutdown
Improved: FTS5 content table pattern for proper INSERT support
Improved: Defensive error handling (supports multiple result formats)
Improved: Comprehensive test suite (25+ tests)
v1.0.0 (2026-09-07)
Initial release
Runtime exception interception
FTS5 dynamic context injection
Zero-downtime recovery
License
MIT License
Copyright (c) 2026 forumevi
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
Acknowledgements
Nous Research — For building Hermes Agent and the plugin ecosystem
Hermes Agent Community — For feedback and testing
SQLite FTS5 — For powerful full-text search capabilities
Contact
GitHub: @forumevi
Discord: Nous Research Discord (#plugins-skills-and-skins)
Issues: Report a bug

1234567891011121314151617




```bash
mkdir -p ~/.hermes/plugins
git clone https://github.com/forumevi/hermes-self-healing-context.git ~/.hermes/plugins/hermes-self-healing-context
