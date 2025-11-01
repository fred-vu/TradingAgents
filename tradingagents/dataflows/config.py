from copy import deepcopy
from typing import Dict, Optional

import tradingagents.default_config as default_config

# Use default config but allow it to be overridden
_config: Optional[Dict] = None
DATA_DIR: Optional[str] = None


def initialize_config():
    """Initialize the configuration with default values."""
    global _config, DATA_DIR
    if _config is None:
        _config = default_config.copy_default_config()
        DATA_DIR = _config["data_dir"]


def set_config(config: Dict):
    """Update the configuration with custom values."""
    global _config, DATA_DIR
    if _config is None:
        _config = default_config.copy_default_config()

    overrides = dict(config)
    provider_overrides = overrides.pop("provider_config", None)

    _config.update(overrides)
    if provider_overrides:
        _config["provider_config"] = default_config.merge_provider_config(
            _config.get("provider_config", {}),
            provider_overrides,
        )

    DATA_DIR = _config["data_dir"]


def get_config() -> Dict:
    """Get the current configuration."""
    if _config is None:
        initialize_config()
    return deepcopy(_config)


# Initialize with default config
initialize_config()
