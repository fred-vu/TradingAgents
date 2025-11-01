import importlib.util
from pathlib import Path


_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "tradingagents" / "default_config.py"
_spec = importlib.util.spec_from_file_location("tradingagents.default_config_test", _DEFAULT_CONFIG_PATH)
default_config = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader, "Unable to load default_config module specification"
_spec.loader.exec_module(default_config)


def test_copy_default_config_returns_isolated_provider_dict():
    cfg1 = default_config.copy_default_config()
    cfg2 = default_config.copy_default_config()

    cfg1["provider_config"]["openai"]["base_url"] = "https://example.com/v1"

    assert cfg2["provider_config"]["openai"]["base_url"] != "https://example.com/v1"
    assert default_config.DEFAULT_CONFIG["provider_config"]["openai"]["base_url"] != "https://example.com/v1"


def test_data_dir_defaults_inside_project():
    cfg = default_config.copy_default_config()
    data_dir = Path(cfg["data_dir"]).resolve()
    project_dir = Path(cfg["project_dir"]).resolve()

    assert data_dir.is_absolute()
    assert data_dir.is_relative_to(project_dir)
