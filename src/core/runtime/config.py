"""Runtime configuration: ConfigurationProfile and YAML loading utilities.

Implements the data model defined in specs/004-openclaw-alignment/data-model.md.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class ConfigError(Exception):
    """Raised when configuration validation or loading fails.

    Attributes:
        field: The config field that caused the error, if applicable.
    """

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


# ---------------------------------------------------------------------------
# Nested config models
# ---------------------------------------------------------------------------

class LLMConfig(BaseModel):
    """LLM provider settings."""

    provider: str
    model: str
    api_key_ref: str = Field(
        description="Environment variable name that holds the API key (NOT the key itself).",
    )
    base_url: Optional[str] = None
    timeout: int = 60


class LoopConfig(BaseModel):
    """Agent loop budget parameters."""

    max_iterations: int = 10
    max_wall_seconds: int = 300
    max_history_messages: int = 20


class PluginsConfig(BaseModel):
    """Plugin discovery and ordering."""

    search_paths: List[str] = Field(default_factory=list)
    enabled_ids: List[str] = Field(default_factory=list)
    priority_overrides: Dict[str, int] = Field(default_factory=dict)


class MCPServerConfig(BaseModel):
    """Single MCP server entry."""

    name: str
    transport: str = "stdio"
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    tools_list_ttl_seconds: int = 300


class MCPConfig(BaseModel):
    """Model Context Protocol settings."""

    servers: List[MCPServerConfig] = Field(default_factory=list)


class DaemonRetryConfig(BaseModel):
    """Exponential back-off parameters for the daemon."""

    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    multiplier: float = 2.0


class DaemonConfig(BaseModel):
    """Daemon lifecycle settings."""

    probe_interval_seconds: int = 60
    shutdown_grace_seconds: int = 10
    retry: DaemonRetryConfig = Field(default_factory=DaemonRetryConfig)


class SecurityConfig(BaseModel):
    """Security and inbound-policy settings."""

    inbound_default_policy: str = "deny"
    sensitive_plugin_ids: List[str] = Field(default_factory=list)
    pairing_store_path: Optional[str] = None


class LoggingConfig(BaseModel):
    """Logging rotation settings."""

    level: str = "INFO"
    path: Optional[str] = None
    max_bytes: int = 10_485_760  # 10 MB
    backup_count: int = 3


class LimitsConfig(BaseModel):
    """Runtime resource limits."""

    memory_mb_warn: Optional[int] = None


class WorkspaceConfig(BaseModel):
    """Bounded local filesystem access (OpenClaw-style workspace tools).

    Relative paths in ``allowed_roots`` resolve against the directory that contains
    the loaded config file (same rule as ``plugins.search_paths``).
    """

    enabled: bool = True
    allowed_roots: List[str] = Field(default_factory=list)
    max_read_bytes: int = 262_144
    max_write_bytes: int = 262_144


class TelegramConfig(BaseModel):
    """Telegram Bot channel (specs/005-telegram-im)."""

    enabled: bool = False
    bot_token_ref: str = Field(
        default="TELEGRAM_BOT_TOKEN",
        description="Environment variable name holding the Bot API token.",
    )


# ---------------------------------------------------------------------------
# Top-level profile
# ---------------------------------------------------------------------------

class ConfigurationProfile(BaseModel):
    """Top-level runtime configuration (specs/004-openclaw-alignment)."""

    schema_version: str
    llm: LLMConfig
    loop: LoopConfig = Field(default_factory=LoopConfig)
    plugins: PluginsConfig = Field(default_factory=PluginsConfig)
    mcp: Optional[MCPConfig] = None
    daemon: Optional[DaemonConfig] = None
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: Optional[LoggingConfig] = None
    limits: Optional[LimitsConfig] = None
    workspace: Optional[WorkspaceConfig] = None
    telegram: Optional[TelegramConfig] = None


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_profile(path: str) -> ConfigurationProfile:
    """Read a YAML file and return a validated :class:`ConfigurationProfile`.

    Raises:
        ConfigError: If the file cannot be read or validation fails.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Cannot read config file: {exc}", field=None) from exc

    try:
        data: Any = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML: {exc}", field=None) from exc

    if not isinstance(data, dict):
        raise ConfigError("Config file must contain a YAML mapping at top level", field=None)

    try:
        return ConfigurationProfile.model_validate(data)
    except Exception as exc:
        raise ConfigError(f"Config validation failed: {exc}", field=None) from exc


def load_profile_with_env_override(path: str) -> ConfigurationProfile:
    """Load a YAML profile then overlay LLM fields from environment variables.

    ``llm.api_key_ref`` in YAML is the **name** of the env var that holds the secret
    (e.g. ``LLM_API_KEY``). Do **not** overwrite it with the key value when
    ``LLM_API_KEY`` is set — that would make ``doctor`` look up ``os.getenv("sk-...")``.

    Recognised env vars:
    - ``LLM_API_KEY_REF`` → override ``llm.api_key_ref`` (still an env var name)
    - ``LLM_MODEL_ID`` → ``llm.model``
    - ``LLM_BASE_URL`` → ``llm.base_url``
    """
    profile = load_profile(path)
    data = profile.model_dump()

    if (key_ref := os.getenv("LLM_API_KEY_REF")):
        data["llm"]["api_key_ref"] = key_ref.strip()
    if (model_id := os.getenv("LLM_MODEL_ID")) is not None:
        data["llm"]["model"] = model_id
    if (base_url := os.getenv("LLM_BASE_URL")) is not None:
        data["llm"]["base_url"] = base_url

    try:
        return ConfigurationProfile.model_validate(data)
    except Exception as exc:
        raise ConfigError(
            f"Config validation failed after env override: {exc}", field=None,
        ) from exc


def load_and_validate_profile(path: str) -> ConfigurationProfile:
    """Load a profile with env overrides, then validate critical fields.

    Raises:
        ConfigError: If ``llm.api_key_ref`` env var is unset or ``llm.model`` is empty.
    """
    profile = load_profile_with_env_override(path)

    ref = profile.llm.api_key_ref
    if not ref or not os.getenv(ref):
        raise ConfigError(
            f"LLM API key env var '{ref}' is not set",
            field="llm.api_key_ref",
        )

    if not profile.llm.model.strip():
        raise ConfigError(
            "LLM model must not be empty",
            field="llm.model",
        )

    return profile


def find_config_path(cli_override: str | None = None) -> str:
    """Resolve the configuration file path.

    Resolution order:
    1. *cli_override* (if provided and the file exists)
    2. ``assistant.yaml`` in CWD
    3. ``assistant.yml`` in CWD

    Raises:
        ConfigError: If no configuration file is found.
    """
    if cli_override is not None:
        if Path(cli_override).is_file():
            return cli_override
        raise ConfigError(
            f"Specified config file not found: {cli_override}",
            field="config_path",
        )

    for name in ("assistant.yaml", "assistant.yml"):
        candidate = Path.cwd() / name
        if candidate.is_file():
            return str(candidate)

    raise ConfigError(
        "No configuration file found (tried assistant.yaml, assistant.yml in CWD)",
        field="config_path",
    )
