"""Configuration loading for the local stdio server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping

from .errors import OpenObserveMcpError

AuthMode = Literal["basic", "bearer"]
APP_DIR_NAME = "openobserve-mcp"
DEFAULT_CONFIG_FILENAME = "config.env"
DEFAULT_CONFIG_TEMPLATE = """# OpenObserve MCP configuration
OO_BASE_URL=https://openobserve.example.com
# Optional if the credentials have access to exactly one organization.
# OO_ORG_ID=default
OO_AUTH_MODE=basic
OO_USERNAME=your_username
OO_PASSWORD=your_password
# OO_TOKEN=your_bearer_token
OO_TIMEOUT_SECONDS=20
OO_VERIFY_SSL=true
"""


class ConfigError(OpenObserveMcpError):
    """Raised when local configuration is invalid."""


@dataclass(frozen=True, slots=True)
class OpenObserveConfig:
    """Runtime configuration for the OpenObserve MCP server."""

    base_url: str
    org_id: str | None
    auth_mode: AuthMode
    username: str | None
    password: str | None
    token: str | None
    timeout_seconds: float
    verify_ssl: bool

    @classmethod
    def load(
        cls,
        *,
        env: Mapping[str, str] | None = None,
        dotenv_path: str | Path | None = None,
    ) -> "OpenObserveConfig":
        if env is None:
            env = os.environ
        resolved_dotenv = resolve_dotenv_path(env=env, dotenv_path=dotenv_path)
        merged: dict[str, str] = {}
        if resolved_dotenv is not None:
            merged.update(_load_dotenv(resolved_dotenv))
        merged.update(env)

        base_url = _required(merged, "OO_BASE_URL").rstrip("/")
        org_id = _optional(merged, "OO_ORG_ID")
        auth_mode = _auth_mode(_required(merged, "OO_AUTH_MODE"))
        timeout_seconds = _positive_float(merged.get("OO_TIMEOUT_SECONDS", "20"), "OO_TIMEOUT_SECONDS")
        verify_ssl = _bool_value(merged.get("OO_VERIFY_SSL", "true"), "OO_VERIFY_SSL")

        username = _optional(merged, "OO_USERNAME")
        password = _optional(merged, "OO_PASSWORD")
        token = _optional(merged, "OO_TOKEN")

        if auth_mode == "basic":
            if not username or not password:
                raise ConfigError("Basic auth requires OO_USERNAME and OO_PASSWORD.")
        if auth_mode == "bearer" and not token:
            raise ConfigError("Bearer auth requires OO_TOKEN.")

        return cls(
            base_url=base_url,
            org_id=org_id,
            auth_mode=auth_mode,
            username=username,
            password=password,
            token=token,
            timeout_seconds=timeout_seconds,
            verify_ssl=verify_ssl,
        )


def default_config_path(*, env: Mapping[str, str] | None = None) -> Path:
    """Return the default per-user config path."""
    if env is None:
        env = os.environ

    xdg_config_home = _optional(env, "XDG_CONFIG_HOME")
    if xdg_config_home:
        base_dir = Path(xdg_config_home).expanduser()
    else:
        home = _optional(env, "HOME")
        base_dir = (Path(home).expanduser() if home else Path.home()) / ".config"
    return base_dir / APP_DIR_NAME / DEFAULT_CONFIG_FILENAME


def resolve_dotenv_path(
    *,
    env: Mapping[str, str] | None = None,
    dotenv_path: str | Path | None = None,
) -> Path | None:
    """Resolve the config file path.

    Precedence:
    1. Explicit ``dotenv_path`` argument
    2. ``OO_CONFIG_FILE`` environment variable
    3. Per-user XDG config file
    4. Legacy ``.env.local`` in the current working directory
    """
    if env is None:
        env = os.environ

    if dotenv_path is not None:
        return _existing_path(dotenv_path, label="Config file")

    configured_path = _optional(env, "OO_CONFIG_FILE")
    if configured_path:
        return _existing_path(configured_path, label="OO_CONFIG_FILE")

    user_path = default_config_path(env=env)
    if user_path.exists():
        return user_path

    legacy_path = Path(".env.local")
    if legacy_path.exists():
        return legacy_path

    return None


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, separator, value = line.partition("=")
        if not separator:
            raise ConfigError(f"Invalid dotenv line {line_number} in {path}.")

        key = key.strip()
        value = _strip_quotes(value.strip())
        if not key:
            raise ConfigError(f"Invalid dotenv key on line {line_number} in {path}.")
        values[key] = value
    return values


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _required(env: Mapping[str, str], name: str) -> str:
    value = _optional(env, name)
    if not value:
        raise ConfigError(f"Missing required configuration value: {name}.")
    return value


def _optional(env: Mapping[str, str], name: str) -> str | None:
    value = env.get(name)
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _existing_path(value: str | Path, *, label: str) -> Path:
    path = Path(value).expanduser()
    if path.exists():
        return path
    raise ConfigError(f"{label} points to a missing file: {path}.")


def _auth_mode(value: str) -> AuthMode:
    normalized = value.strip().lower()
    if normalized in {"basic", "bearer"}:
        return normalized
    raise ConfigError("OO_AUTH_MODE must be either 'basic' or 'bearer'.")


def _positive_float(value: str, name: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number.") from exc
    if number <= 0:
        raise ConfigError(f"{name} must be greater than zero.")
    return number


def _bool_value(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{name} must be a boolean-like value.")
