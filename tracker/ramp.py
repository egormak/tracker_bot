import logging
import requests
from pydantic import BaseModel, Field
from tracker import const

logger = logging.getLogger(__name__)


class RampConfig(BaseModel):
    cap_minutes: int = 25
    enabled_roles: list[str] = Field(default_factory=list)
    enabled_tasks: list[str] = Field(default_factory=list)
    excluded_tasks: list[str] = Field(default_factory=list)
    default_rest_fallback: int = 15


class RampStatus(BaseModel):
    current_step: int = 1
    cap_minutes: int = 25
    is_capped: bool = False
    today_focus_minutes: int = 0
    date: str = ""
    config: RampConfig = Field(default_factory=RampConfig)


def get_ramp_status() -> dict:
    """Fetch current ramp status from tracker-server."""
    try:
        response = requests.get(const.RAMP_STATUS_URI)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict) and "current_step" in data["data"]:
                return data["data"]
            return data if isinstance(data, dict) else {}
        logger.error(f"Failed to get ramp status: status {response.status_code}")
        return {}
    except Exception as e:
        logger.error(f"Error fetching ramp status: {e}")
        return {}


def reset_ramp() -> dict:
    """Reset ramp step to 1 via tracker-server."""
    try:
        response = requests.post(const.RAMP_RESET_URI)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict) and "current_step" in data["data"]:
                return data["data"]
            return data if isinstance(data, dict) else {}
        logger.error(f"Failed to reset ramp: status {response.status_code}")
        return {}
    except Exception as e:
        logger.error(f"Error resetting ramp: {e}")
        return {}


def get_ramp_status_model() -> RampStatus:
    """Fetch and parse ramp status into Pydantic model."""
    data = get_ramp_status()
    try:
        return RampStatus.model_validate(data)
    except Exception:
        return RampStatus()
