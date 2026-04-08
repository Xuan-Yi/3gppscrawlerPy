"""
Loads configuration from config.toml at the project root.
All constants retain the same names so the rest of the codebase needs no changes.
"""
import tomllib
from pathlib import Path

_cfg_path = Path(__file__).parent.parent / "config.toml"
try:
    with _cfg_path.open("rb") as _f:
        _cfg = tomllib.load(_f)
except FileNotFoundError:
    raise FileNotFoundError(
        f"Configuration file not found: {_cfg_path}\n"
        "Create config.toml in the project root before running."
    ) from None
except tomllib.TOMLDecodeError as e:
    raise ValueError(f"Invalid TOML in {_cfg_path}: {e}") from e

# Network
BASE_URL                = _cfg["network"]["base_url"]
HEADERS                 = {"User-Agent": _cfg["network"]["user_agent"]}
TIMEOUT_PAGE            = _cfg["network"]["timeout_page"]
TIMEOUT_DOWNLOAD        = _cfg["network"]["timeout_download"]
RETRY_ATTEMPTS          = _cfg["network"]["retry_attempts"]
RETRY_BACKOFF           = _cfg["network"]["retry_backoff"]
MAX_CONCURRENT_REQUESTS = _cfg["network"]["max_concurrent"]

# Storage
LOCAL_FOLDER            = _cfg["storage"]["local_folder"]

# Processing
MAX_WORKERS             = _cfg["processing"]["max_workers"]
MAX_WORD_INSTANCES      = _cfg["processing"]["max_word_instances"]

# TRs
DEFAULT_TR_LIST         = _cfg["trs"]["default_list"]
