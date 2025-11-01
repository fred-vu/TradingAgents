# Trade Audit Log Schema

TradingAgents emits audit events to `trade_audit.jsonl` in the configured log directory. Each line is a JSON object with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string (ISO-8601) | Auto-generated when the record is persisted. |
| `trade_id` | string | Unique identifier (UUID4 hex) for the trade recommendation event. |
| `symbol` | string | Ticker symbol evaluated by the agent team. |
| `trade_date` | string | Trading date (YYYY-mm-dd) supplied to the graph. |
| `recommendation` | string | Final BUY/SELL/HOLD signal recommended to the trader. |
| `confidence` | number/null | Optional confidence score (if available from downstream agents). |
| `analysts` | object | Map of analyst role → `{ "signal": str|null, "reasoning": str }`. |
| `debate_rounds` | integer | Number of investment debate turns completed. |
| `risk_rounds` | integer | Number of risk debate turns completed. |
| `risk_score` | number/null | Optional quantitative risk score if the pipeline provides one. |
| `trader_notes` | string | Trader agent’s execution plan or notes. |
| `final_decision` | string | Same as recommendation; duplicated for downstream compatibility. |
| `investment_judge_decision` | string | Research manager’s summary ruling. |
| `risk_judge_decision` | string | Risk manager’s summary ruling. |
| `debate_history` | string | Transcript of the investment debate. |
| `risk_history` | string | Transcript of the risk debate. |
| `execution_status` | string | Default `PENDING`; updated by downstream systems if execution occurs. |
| `errors` | array | Empty list by default; populate with error messages if execution encounters issues. |

## Location

- Default directory: `<project_root>/../audit_logs/`
- Override via config keys `audit_log_dir` / `audit_log_filename` or environment variables `TRADINGAGENTS_AUDIT_LOG_DIR`, `TRADINGAGENTS_LOG_DIR`.

## Consumption Tips

- Treat the file as append-only JSON Lines. Each row is a standalone JSON object.
- For analytics, stream into a data warehouse or parse using tools like `jq` or pandas.
- Audit log complements the full-state JSON snapshots in `eval_results/<ticker>/TradingAgentsStrategy_logs/`.
