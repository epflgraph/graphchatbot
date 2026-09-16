import os
from configparser import ConfigParser
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

load_dotenv()


class BaseConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class RcpConfig(BaseConfig):
    base_url: str
    api_key: str


class ElasticsearchConfig(BaseConfig):
    index: str
    host: str | None = None
    port: str | None = None
    username: str | None = None
    password: str | None = None
    cafile: str | None = None


class GraphsearchConfig(BaseConfig):
    base_url: str


class GraphaiConfig(BaseConfig):
    host: str
    port: str
    username: str
    password: str


class CacheConfig(BaseConfig):
    cache_dir: Path | None = None

    @field_validator("cache_dir", mode="before")
    @classmethod
    def _clear_cache_dir_if_empty(cls, raw: str | None) -> str | None:
        # "" -> None: an unset `cache_dir:` in the ini parses to "", and Path("") is
        # Path("."), which is truthy — so `cache_dir or default` wouldn't fall back.
        return raw or None


class LangfuseConfig(BaseConfig):
    host: str | None = None
    secret_key: str | None = None
    public_key: str | None = None
    environment: str | None = None


class MoodleConfig(BaseConfig):
    base_url: str | None = None
    token: str | None = None
    timeout: float = Field(default=10.0, gt=0)

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    @model_validator(mode="after")
    def _require_both_or_neither(self) -> "MoodleConfig":
        if bool(self.base_url) != bool(self.token):
            raise ValueError("Moodle config needs both base_url and token, or neither")
        return self


class MoodlePollingConfig(BaseConfig):
    """Polling that keeps a graded course's topic groups in step with its tagged quizzes."""

    interval_seconds: float = Field(default=30.0, gt=0)


class AppConfig(BaseConfig):
    rcp: RcpConfig
    elasticsearch: ElasticsearchConfig
    graphsearch: GraphsearchConfig
    graphai: GraphaiConfig
    cache: CacheConfig = Field(default_factory=CacheConfig)
    langfuse: LangfuseConfig = Field(default_factory=LangfuseConfig)
    moodle: MoodleConfig = Field(default_factory=MoodleConfig)
    moodle_polling: MoodlePollingConfig = Field(default_factory=MoodlePollingConfig)


# Overridable so the test suite can point at a placeholder config (see `tests/__init__.py`).
CONFIG_PATH_ENV_VAR = "GRAPHCHATBOT_CONFIG"
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.ini"

parser = ConfigParser()
parser.read(os.environ.get(CONFIG_PATH_ENV_VAR) or DEFAULT_CONFIG_PATH)

raw_config = {section: dict(parser[section]) for section in parser.sections()}
config = AppConfig.model_validate(raw_config)
