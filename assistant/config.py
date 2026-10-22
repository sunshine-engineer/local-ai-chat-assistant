"""Resolve typed runtime settings from environment variables and non-secret defaults.

File: assistant/config.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import os
import tomllib
from functools import lru_cache
from pathlib import Path

DEFAULTS_PATH = Path(__file__).resolve().parents[1] / "config" / "defaults.toml"


@lru_cache(maxsize=1)
def defaults():
    """Read the packaged defaults once without reading private environment files.

    Returns:
        Mapping of setting sections to non-secret default values.

    Raises:
        OSError: The packaged defaults cannot be read.
        tomllib.TOMLDecodeError: The defaults file contains invalid TOML.
    """
    with DEFAULTS_PATH.open("rb") as handle:
        return tomllib.load(handle)


def setting(section, key, environment):
    """Resolve a setting with its default's type and dynamic environment precedence.

    Args:
        section: TOML defaults section containing the setting.
        key: Setting name within that section.
        environment: Environment variable overriding the packaged value.

    Returns:
        Environment override converted to the default's type, or the default value.

    Raises:
        ValueError: A numeric override cannot be converted to the required type.
        KeyError: The requested default section or key is missing.

    Examples:
        >>> setting("ollama", "host", "AN_UNUSED_EXAMPLE_VARIABLE")
        'http://localhost:11434'
    """
    default = defaults()[section][key]
    value = os.getenv(environment)
    return default if value is None else type(default)(value)
