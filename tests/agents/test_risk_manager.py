from types import SimpleNamespace
from pathlib import Path
import importlib.util


_RISK_MANAGER_PATH = Path(__file__).resolve().parents[2] / "tradingagents" / "agents" / "managers" / "risk_manager.py"
_spec = importlib.util.spec_from_file_location("risk_manager_module", _RISK_MANAGER_PATH)
_risk_manager = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader, "Unable to load risk_manager module specification"
_spec.loader.exec_module(_risk_manager)
create_risk_manager = _risk_manager.create_risk_manager


class DummyLLM:
    def __init__(self, response_content="Risk-adjusted decision"):
        self.response_content = response_content
        self.last_prompt = None

    def invoke(self, prompt):
        self.last_prompt = prompt
        return SimpleNamespace(content=self.response_content)


class DummyMemory:
    def __init__(self):
        self.last_input = None

    def get_memories(self, situation, n_matches=2):
        self.last_input = situation
        return [{"recommendation": "Tighten stops on weak fundamentals."}]


def _base_state(**overrides):
    base = {
        "company_of_interest": "NVDA",
        "market_report": "Market trends favour semiconductors.",
        "news_report": "Breaking: supply chain constraints easing.",
        "fundamentals_report": "Fundamentals: PE at 55, debt rising.",
        "sentiment_report": "Sentiment: bullish retail chatter.",
        "investment_plan": "Scale into position over three tranches.",
        "risk_debate_state": {
            "history": "Risky argues to double exposure; Safe urges caution.",
            "risky_history": "Risky: leverage the rally.",
            "safe_history": "Safe: cap downside with stops.",
            "neutral_history": "Neutral: wait for confirmation.",
            "latest_speaker": "Safe",
            "current_risky_response": "Risky: momentum is strong.",
            "current_safe_response": "Safe: volatility elevated.",
            "current_neutral_response": "Neutral: review macro data.",
            "count": 3,
        },
    }
    base.update(overrides)
    return base


def test_risk_manager_includes_fundamentals_in_memory_context():
    llm = DummyLLM()
    memory = DummyMemory()
    node = create_risk_manager(llm, memory)

    node(_base_state())

    assert "Fundamentals: PE at 55, debt rising." in memory.last_input
    # Ensure fundamentals are not substituted with news content.
    assert memory.last_input.count("Breaking: supply chain constraints easing.") == 1


def test_risk_manager_prompt_highlights_fundamental_evaluation():
    llm = DummyLLM()
    memory = DummyMemory()
    node = create_risk_manager(llm, memory)

    node(_base_state())

    assert "Evaluate Fundamentals Explicitly" in llm.last_prompt
    assert "Fundamentals: PE at 55, debt rising." in llm.last_prompt
    assert "Tighten stops on weak fundamentals." in llm.last_prompt


def test_risk_manager_handles_missing_fundamentals_gracefully():
    llm = DummyLLM(response_content="Hold until fundamentals confirm trend.")
    memory = DummyMemory()
    node = create_risk_manager(llm, memory)

    result = node(_base_state(fundamentals_report=""))

    assert memory.last_input.endswith("\n\n")
    assert result["final_trade_decision"] == "Hold until fundamentals confirm trend."
    assert result["risk_debate_state"]["judge_decision"] == "Hold until fundamentals confirm trend."
