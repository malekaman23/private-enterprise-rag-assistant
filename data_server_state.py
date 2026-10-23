"""Runtime enable/disable state for the mounted company data source."""

import json
from pathlib import Path

import config


STATE_FILE = Path(config.DATA_DIR) / "company_data_server.json"


def is_enabled() -> bool:
    if not config.COMPANY_DATA_ROOT:
        return False
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8")).get("enabled", True)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return True


def set_enabled(enabled: bool) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"enabled": bool(enabled)}), encoding="utf-8")
