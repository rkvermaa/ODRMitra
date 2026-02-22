"""Dynaconf settings configuration"""

from pathlib import Path
from dynaconf import Dynaconf, Validator

PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"

settings = Dynaconf(
    envvar_prefix="APP",
    settings_files=[
        str(CONFIG_DIR / "settings.toml"),
        str(CONFIG_DIR / "settings.local.toml"),
        str(CONFIG_DIR / ".secrets.toml"),
    ],
    environments=True,
    env_switcher="APP_ENV",
)

settings.validators.register(
    Validator("DATABASE_URL", must_exist=True),
    Validator("REDIS_URL", must_exist=True),
    Validator("JWT_SECRET", must_exist=True, min_len=32),
    Validator("DEEPSEEK_API_KEY", must_exist=True),
)


def validate_settings():
    """Validate all settings on startup."""
    settings.validators.validate()
