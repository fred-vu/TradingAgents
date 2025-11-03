# Project Diary

## 2025-11-01
- Phase 1 kickoff: addressed audit item “Risk manager lacks fundamentals input”.
- Corrected fundamentals wiring in `tradingagents/agents/managers/risk_manager.py` and expanded prompt guidance.
- Added regression tests (`tests/agents/test_risk_manager.py`) validating fundamentals propagation, prompt content, and graceful handling when data is missing.
- Documented state contract in `docs/STATE_SCHEMA.md`; created support stubs for future memory validation.
- Refactored LLM provider initialization with new `llm_factory`, configurable provider metadata, and merged overrides; added coverage in `tests/graph/test_llm_factory.py`.
- Replaced developer-specific paths in `default_config`, introduced deep-copy helpers, and ensured recursive/conditional settings respect runtime overrides.
- Hardened OpenAI data vendor parsing (`tradingagents/dataflows/openai.py`) with robust extraction logic; added regression tests in `tests/dataflows/test_openai_vendor.py` and config checks in `tests/config/test_default_config.py`.
- Phase 2 kickoff: introduced persistent memory storage, structured logging, and audit logging per production readiness plan.
- Added `tradingagents/logging_utils.py` with configurable log directories, audit stream, and LangSmith hooks; validated via `tests/logging/test_logging_utils.py`.
- Updated `FinancialSituationMemory` to leverage persistent Chroma directories and added regression coverage in `tests/agents/test_memory_persistence.py`.
- Replaced vendor routing prints with structured logging and documented audit schema (`docs/AUDIT_LOG_SCHEMA.md`).
- Implemented dedicated `AuditLogger` with retention policy, richer schema, and integration into `TradingAgentsGraph`; added tests in `tests/utils/test_audit_logger.py` and expanded documentation.
- Manual end-to-end verification of audit JSONL during CLI runs remains to be scheduled; smoke test via `AuditLogger` helper confirmed file output.
- Patched `FinancialSituationMemory` to use `chromadb.PersistentClient`, restoring CLI compatibility with latest Chroma releases while retaining backward compatibility shims.
- Manual end-to-end verification of audit JSONL during CLI runs remains to be scheduled; smoke test via `AuditLogger` helper confirmed file output.
- Phase 3 kickoff: implemented SQLite-backed response cache with configurable TTLs, vendor priority ordering, and cost logging. Added regression coverage in `tests/dataflows/test_cache_layer.py` and `tests/dataflows/test_route_caching.py` (skips when vendor deps missing).
- Extended vendor redundancy: added circuit breaker logic, optional dependency handling for yfinance/Google, and regression tests ensuring fallbacks skip tripped vendors while logging cost metrics.
- Integrated live Finnhub and NewsAPI vendors with optional API key detection, expanding fundamentals/news coverage while keeping local cache as fallback.
- Completed LLM Phase 3 work: OpenRouter alias mapping with cost estimates, logging improvements, and regression coverage to ensure cheaper models can be selected dynamically.

## 2025-11-03
- Refined OpenRouter free-only stack for CLI tests: removed Maverick/Gemini aliases, added GLM 4.5 Air, Minimax M2, DeepSeek v3, and Mistral Small free variants.
- Added provider-level rate limiter (default 16 TPM, configurable via `TRADINGAGENTS_OPENROUTER_MAX_CALLS`) to prevent free-tier throttling during runs.
- Updated `cli/utils.py` selections so both shallow/deep pickers list the new free models; ensures CLI choices map to actual aliases.
- Introduced `Openrouter-Context.md` summarising alias mappings, scoring, and limiter behaviour for upcoming external audit.
- Updated `.env.example` to document selection mode/limit env vars for operators enabling free-only mode.
