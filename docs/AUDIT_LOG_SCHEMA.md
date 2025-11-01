# Trade Audit Log Schema

TradingAgents emits audit events to `trade_audit.jsonl` in the configured log directory. Each line is a JSON object with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string (ISO-8601) | Automatically added by the logging system when the record is written. |
| `ticker` | string | Ticker symbol evaluated by the agent team. |
| `trade_date` | string | Trading date (YYYY-mm-dd) supplied to the graph. |
| `final_trade_decision` | string | Risk manager’s final BUY/SELL/HOLD verdict. |
| `trader_plan` | string | Trader’s proposed execution plan. |
| `risk_judge_decision` | string | Narrative from the risk judge summarising risk posture. |
| `investment_judge_decision` | string | Research manager’s recommendation backing the trade. |

## Location

- Default path: `<project_root>/logs/trade_audit.jsonl`
- Override via config key `audit_log_filename` or environment variable `TRADINGAGENTS_LOG_DIR`.

## Consumption Tips

- Treat the file as append-only JSON Lines. Each row is a standalone JSON object.
- For analytics, stream into a data warehouse or parse using tools like `jq` or pandas.
- Audit log complements the full-state JSON snapshots in `eval_results/<ticker>/TradingAgentsStrategy_logs/`.
