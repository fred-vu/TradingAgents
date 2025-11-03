## OpenRouter Integration Context

### Current Goals
- Provide a free-only evaluation stack for CLI usage while keeping a path to paid/high-performance models via configuration.
- Maintain predictable call cadence (<=16 requests/min by default) to avoid shared-tier throttling.
- Surface clear configuration levers so an external reviewer can suggest improvements or alternative providers.

### Model Aliases & Cost Table
| Alias Key | Upstream Model ID | Notes | Estimated Cost (USD / 1k tokens) |
|-----------|-------------------|-------|----------------------------------|
| `zAi-glm-4-5` | `z-ai/glm-4.5-air:free` | Primary free model (balanced reasoning, good latency) | prompt 0.00 / completion 0.00 |
| `minimax-free` | `minimax/minimax-m2:free` | Secondary free model; consistent reasoning | prompt 0.00 / completion 0.00 |

Paid / higher-tier aliases remain (`openai/gpt-5-mini`, `openai/gpt-4o-mini`, `mistralai/magistral-medium-2506:thinking`, `meta-llama/llama-3.3-70b-instruct`, `x-ai/grok-4-fast`), but are blocked in free-only runs unless explicitly re-enabled.

### Capability Tiers & Scoring
- `finance_safe`: `gpt-5-mini`, `gpt-4o-mini`, `magistral-medium`.
- `cost_saver`: `gpt-4o-mini`, `magistral-medium`.
- `research_heavy`: `llama3-70b`, `grok-4-fast`.
- `free_trial`: `zAi-glm-4-5`, `minimax-free` (GLM primary, Minimax secondary).

Candidate scoring uses:
- Priority weight (position-based) 0.4
- `reliability` 0.4 (GLM:0.7, Minimax:0.6)
- `cost_weight` 0.15 (all free tiers set 1.0)
- Tier bonus (finance_safe +0.05, cost_saver +0.03, research_heavy +0.02)

This yields default fallback order:
1. `z-ai/glm-4.5-air:free`
2. `minimax/minimax-m2:free`

### Selection Modes (`TRADINGAGENTS_OPENROUTER_SELECTION_MODE`)
- `balanced` *(default)*: mixes cost & reliability to select highest scoring candidate.
- `cost_balanced`: cost weight emphasized more heavily.
- `performance_first`: reliability + tier bonuses dominate; free models are deprioritized.
- `free_only`: restricts candidate pool to `free_trial` tier; still respects scoring and reliability ordering.

### Rate Limiting (`TRADINGAGENTS_OPENROUTER_MAX_CALLS`)
- Global limiter stored per provider key (default 16 calls/minute). Adjustable via environment variable.
- Enforced before **every** OpenRouter call (deep, quick, tool bindings). If bucket is full, the executor sleeps until the oldest timestamp slips out of the 60s window.

### CLI Defaults (`cli/utils.py`)
- Quick- & deep-thinking menus now list the same free models to keep local runs consistent.
- If a user selects GLM hoặc Minimax trong CLI, config dùng thẳng model upstream tương ứng (không cần sửa code).

### Tests & Regression Coverage
- `tests/graph/test_llm_factory.py` validates:
  - OpenRouter fallback stack contains core aliases + hai free alias.
  - Free-only mode instantiates GLM/Minimax (cho phép thay đổi model primary do scoring).
  - OpenAI / Ollama instantiation counts reflect 2 Chat clients (deep + quick).

### Operational Notes / Gaps for Audit
- Maintained only two free models to minimise rate-limit churn; revisit if additional reliable free tiers become available.
- Rate limiter là coarse (per-provider); auditor có thể đề xuất bucket riêng cho deep/quick hoặc pacing adapt.
- Chưa có telemetry về success/latency mỗi model; audit có thể yêu cầu ghi log để điều chỉnh `reliability` sau này.
- Paid models vẫn tồn tại trong config; đảm bảo block khi chạy đánh giá free-only để tránh phát sinh chi phí.
