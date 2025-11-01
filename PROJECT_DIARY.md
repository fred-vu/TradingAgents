# Project Diary

## 2025-11-01
- Phase 1 kickoff: addressed audit item “Risk manager lacks fundamentals input”.
- Corrected fundamentals wiring in `tradingagents/agents/managers/risk_manager.py` and expanded prompt guidance.
- Added regression tests (`tests/agents/test_risk_manager.py`) validating fundamentals propagation, prompt content, and graceful handling when data is missing.
- Documented state contract in `docs/STATE_SCHEMA.md`; created support stubs for future memory validation.
- Refactored LLM provider initialization with new `llm_factory`, configurable provider metadata, and merged overrides; added coverage in `tests/graph/test_llm_factory.py`.
- Replaced developer-specific paths in `default_config`, introduced deep-copy helpers, and ensured recursive/conditional settings respect runtime overrides.
- Hardened OpenAI data vendor parsing (`tradingagents/dataflows/openai.py`) with robust extraction logic; added regression tests in `tests/dataflows/test_openai_vendor.py` and config checks in `tests/config/test_default_config.py`.
