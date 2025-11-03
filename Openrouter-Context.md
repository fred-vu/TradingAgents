## OpenRouter Integration Context

### Current Goals
- Provide a free-only evaluation stack for CLI usage while keeping a path to paid/high-performance models via configuration.
- Maintain predictable call cadence (<=16 requests/min by default) to avoid shared-tier throttling.
- Surface clear configuration levers so an external reviewer can suggest improvements or alternative providers.

### Model Aliases & Cost Table
| Alias Key | Upstream Model ID | Notes | Estimated Cost (USD / 1k tokens) |
|-----------|-------------------|-------|----------------------------------|
| `zAi-glm-4-5` | `z-ai/glm-4.5-air:free` | Primary free model (balanced reasoning, good latency) | prompt 0.00 / completion 0.00 |
| `minimax-free` | `minimax/minimax-m2:free` | Backup free model; comparable reasoning, slightly slower | prompt 0.00 / completion 0.00 |
| `deepseek-r1` | `deepseek/deepseek-chat-v3-0324:free` | Multi-lingual, tends to be available when others throttle | prompt 0.00 / completion 0.00 |
| `mistral-small` | `mistralai/mistral-small-3.2-24b-instruct:free` | Creative/structured fallback, more moderation events | prompt 0.00 / completion 0.00 |

Paid / higher-tier aliases remain (`openai/gpt-5-mini`, `openai/gpt-4o-mini`, `mistralai/magistral-medium-2506:thinking`, `meta-llama/llama-3.3-70b-instruct`, `x-ai/grok-4-fast`), but are blocked in free-only runs unless explicitly re-enabled.

### Capability Tiers & Scoring
- `finance_safe`: `gpt-5-mini`, `gpt-4o-mini`, `magistral-medium`.
- `cost_saver`: `gpt-4o-mini`, `magistral-medium`.
- `research_heavy`: `llama3-70b`, `grok-4-fast`.
- `free_trial`: `zAi-glm-4-5`, `minimax-free`, `deepseek-r1`, `mistral-small` (ordered intentionally so GLM is first).

Candidate scoring uses:
- Priority weight (position-based) 0.4
- `reliability` 0.4 (raised GLM:0.8, Minimax:0.6, DeepSeek:0.5, Mistral:0.45)
- `cost_weight` 0.15 (all free tiers set 1.0)
- Tier bonus (finance_safe +0.05, cost_saver +0.03, research_heavy +0.02)

This yields default fallback order:
1. `z-ai/glm-4.5-air:free`
2. `minimax/minimax-m2:free`
3. `deepseek/deepseek-chat-v3-0324:free`
4. `mistralai/mistral-small-3.2-24b-instruct:free`

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
- If a user selects Minimax or DeepSeek in the CLI, the config uses the literal upstream model ID (no need to adjust code).

### Tests & Regression Coverage
- `tests/graph/test_llm_factory.py` validates:
  - OpenRouter fallback stack contains core + four free aliases.
  - Free-only mode instantiates all free models (and tolerates different primary selections based on score).
  - OpenAI / Ollama instantiation counts reflect 2 Chat clients (deep + quick).

### Operational Notes / Gaps for Audit
- DeepSeek free tier occasionally returns `429` or lacks tool support; we rely on scoring + fallback to recover. Consider adding automatic block if a model repeatedly fails for tools.
- Rate limiter is coarse (per-provider) and does not differentiate deep vs quick contexts; a reviewer may suggest separate buckets or adaptive pacing.
- No persistence layer yet for recording per-model success/failure rates. Audit may recommend telemetry (counts, latencies) to refine scoring in production.
- Paid models remain in config; ensure they are blocked when running free-only evaluations to avoid accidental spend.

