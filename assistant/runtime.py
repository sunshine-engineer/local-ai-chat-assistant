"""Shared command-registry construction and local-model diagnostics.

File: assistant/runtime.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import json
from urllib.request import urlopen

from assistant.commands import Action, CommandRegistry
from assistant.config import setting


def model_status(arguments=""):
    """Report local-model connectivity without treating availability as model quality.

    Args:
        arguments: Unused argument string accepted for command-registry compatibility.

    Returns:
        Connectivity and installed-model diagnostic, including unavailable-service guidance.
    """
    host = setting("ollama", "host", "OLLAMA_HOST").rstrip("/")
    try:
        with urlopen(host + "/api/tags", timeout=5) as response:
            names = [m["name"] for m in json.load(response).get("models", [])]
        return "Ollama reachable. Installed models: " + (", ".join(names) or "none")
    except (OSError, ValueError):
        return "Ollama unavailable. Start Ollama and check OLLAMA_HOST."


def build_registry():
    """Construct the shared CLI and Streamlit command registry.

    Returns:
        Registry containing built-in diagnostics and job commands.
    """
    registry = CommandRegistry()
    registry.register(Action("status", "Check local model connectivity.", model_status))
    from assistant.jobs import Jobs

    Jobs().register(registry)
    return registry
