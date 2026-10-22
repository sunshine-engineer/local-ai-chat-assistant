"""Run an action without starting Streamlit: python -m assistant.cli /help.

File: assistant/cli.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import os
import sys

from dotenv import load_dotenv

from assistant.runtime import build_registry


def main():
    """Execute a slash command from arguments and optional standard input.

    Returns:
        Exit code 0 for handled success, 1 for command failure, or 2 for missing/non-command input.
    """
    load_dotenv()
    os.environ["ASSISTANT_CLI"] = "1"
    text = " ".join(sys.argv[1:])
    if not sys.stdin.isatty():
        payload = sys.stdin.read().strip()
        if payload:
            text += " " + payload
    registry = build_registry()
    result = registry.execute(text)
    print(result if result is not None else "Provide a command; use /help.")
    return 2 if result is None else (1 if registry.last_error else 0)


if __name__ == "__main__":
    sys.exit(main())
