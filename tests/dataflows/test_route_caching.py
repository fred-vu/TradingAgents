import importlib
import pytest


@pytest.fixture(autouse=True)
def reset_cache():
    cache_module = importlib.import_module("tradingagents.dataflows.cache")
    cache_module.reset_cache_for_tests()
    interface_module = importlib.import_module("tradingagents.dataflows.interface")
    interface_module.reset_vendor_state_for_tests()
    yield
    cache_module.reset_cache_for_tests()
    interface_module.reset_vendor_state_for_tests()


def test_route_to_vendor_cache_hits(tmp_path, monkeypatch):
    try:
        interface_module = importlib.import_module("tradingagents.dataflows.interface")
    except ModuleNotFoundError as exc:
        pytest.skip(f"Missing dependency for interface module: {exc}")
    config_module = importlib.import_module("tradingagents.dataflows.config")

    call_count = {"alpha_vantage": 0}

    def fake_vendor(symbol, start, end):
        call_count["alpha_vantage"] += 1
        return f"PAYLOAD-{symbol}-{call_count['alpha_vantage']}"

    monkeypatch.setitem(
        interface_module.VENDOR_METHODS["get_stock_data"],
        "alpha_vantage",
        fake_vendor,
    )

    original_config = config_module.get_config()
    try:
        config_module.set_config(
            {
                "cache_db_path": str(tmp_path / "cache" / "cache.db"),
                "cache_ttl": {"get_stock_data": 3600},
                "tool_vendors": {"get_stock_data": "alpha_vantage"},
                "vendor_costs": {},
            }
        )

        first = interface_module.route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-01-31")
        second = interface_module.route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-01-31")

        assert first == second
        assert call_count["alpha_vantage"] == 1
    finally:
        config_module.set_config(original_config)


def test_circuit_breaker_skips_failed_vendor(tmp_path, monkeypatch):
    interface_module = importlib.import_module("tradingagents.dataflows.interface")
    config_module = importlib.import_module("tradingagents.dataflows.config")

    failure_counts = {"alpha_vantage": 0}

    def failing_vendor(*args, **kwargs):
        failure_counts["alpha_vantage"] += 1
        raise RuntimeError("alpha_vantage failure")

    def succeeding_vendor(*args, **kwargs):
        return "SUCCESS"

    monkeypatch.setitem(
        interface_module.VENDOR_METHODS["get_stock_data"],
        "alpha_vantage",
        failing_vendor,
    )
    monkeypatch.setitem(
        interface_module.VENDOR_METHODS["get_stock_data"],
        "yfinance",
        succeeding_vendor,
    )
    original_availability = interface_module.VENDOR_AVAILABILITY.get("yfinance")
    interface_module.VENDOR_AVAILABILITY["yfinance"] = True

    original_config = config_module.get_config()
    try:
        config_module.set_config(
            {
                "cache_db_path": str(tmp_path / "cache" / "cache.db"),
                "cache_ttl": {"get_stock_data": 0},
                "tool_vendors": {"get_stock_data": "alpha_vantage,yfinance"},
                "vendor_priority_order": "alpha_vantage,yfinance",
                "vendor_circuit_breaker_threshold": 2,
                "vendor_circuit_breaker_cooldown": 60,
                "vendor_costs": {},
            }
        )

        # First call: alpha fails, fallback to yfinance
        assert interface_module.route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-01-31") == "SUCCESS"
        # Second call: alpha fails again, circuit breaker trip threshold reached
        assert interface_module.route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-01-31") == "SUCCESS"
        # Third call: alpha should be skipped due to circuit breaker (no additional failure increments)
        assert interface_module.route_to_vendor("get_stock_data", "AAPL", "2024-01-01", "2024-01-31") == "SUCCESS"

        assert failure_counts["alpha_vantage"] == 2
    finally:
        config_module.set_config(original_config)
        interface_module.VENDOR_AVAILABILITY["yfinance"] = original_availability
