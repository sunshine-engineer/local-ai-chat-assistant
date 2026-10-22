"""Command handlers are deterministic; plain chat alone goes to the model.

File: assistant/commands.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Action:
    """Describe one named command and its bounded handler.

    Attributes:
        name: Slash-command name without its leading slash.
        description: User-facing help text.
        handler: Callable receiving an argument string and returning result text.
    """

    name: str
    description: str
    handler: Callable[[str], str]


class CommandRegistry:
    """Route slash commands without delegating execution to a model."""

    def __init__(self):
        """Initialize the registry and register built-in help."""
        self.actions = {}
        self.last_error = False
        self.register(Action("help", "List available commands.", self.help))

    def register(self, action):
        """Register an action once under its unique command name.

        Args:
            action: Registered Action or captured command handler to invoke.

        Raises:
            ValueError: Input, ownership, review state or provider output fails this operation's validation.
        """
        if action.name in self.actions:
            raise ValueError(f"Duplicate command: {action.name}")
        self.actions[action.name] = action

    def help(self, arguments=""):
        """List the registered commands and their descriptions.

        Args:
            arguments: Command argument string; JSON payload or application ID as required by this handler.

        Returns:
            Newline-separated command names and descriptions.
        """
        return "\n".join(f"/{a.name} — {a.description}" for a in self.actions.values())

    def execute(self, text):
        """Execute a slash command or return None for ordinary chat.

        Args:
            text: Text to inspect or transform without changing the original value.

        Returns:
            Handler result or bounded failure message; None for ordinary chat.
        """
        self.last_error = False
        text = text.strip()
        if not text.startswith("/"):
            return None
        parts = text[1:].split(maxsplit=1)
        name = parts[0] if parts else ""
        arguments = parts[1] if len(parts) > 1 else ""
        action = self.actions.get(name)
        if action is None:
            self.last_error = True
            return f"Unknown command /{name}. Use /help."
        try:
            return action.handler(arguments)
        except (ValueError, OSError) as exc:
            self.last_error = True
            return f"Action failed: {exc}"
