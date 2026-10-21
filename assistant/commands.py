"""Command handlers are deterministic; plain chat alone goes to the model."""
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Action:
    name: str
    description: str
    handler: Callable[[str], str]


class CommandRegistry:
    def __init__(self):
        self.actions = {}
        self.register(Action('help', 'List available commands.', self.help))

    def register(self, action):
        if action.name in self.actions:
            raise ValueError(f'Duplicate command: {action.name}')
        self.actions[action.name] = action

    def help(self, arguments=''):
        return '\n'.join(f'/{a.name} — {a.description}' for a in self.actions.values())

    def execute(self, text):
        """Return None for ordinary chat; commands never fall through to an LLM."""
        text = text.strip()
        if not text.startswith('/'):
            return None
        parts = text[1:].split(maxsplit=1)
        name = parts[0] if parts else ''
        arguments = parts[1] if len(parts) > 1 else ''
        action = self.actions.get(name)
        if action is None:
            return f'Unknown command /{name}. Use /help.'
        try:
            return action.handler(arguments)
        except (ValueError, OSError) as exc:
            return f'Action failed: {exc}'
