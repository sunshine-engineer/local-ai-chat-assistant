import os
import json
from urllib.request import Request, urlopen
from assistant.commands import Action, CommandRegistry


def model_status(arguments=''):
    host = os.getenv('OLLAMA_HOST', 'http://localhost:11434').rstrip('/')
    try:
        with urlopen(host + '/api/tags', timeout=5) as response:
            names = [m['name'] for m in json.load(response).get('models', [])]
        return 'Ollama reachable. Installed models: ' + (', '.join(names) or 'none')
    except (OSError, ValueError):
        return 'Ollama unavailable. Start Ollama and check OLLAMA_HOST.'


def build_registry():
    registry = CommandRegistry()
    registry.register(Action('status', 'Check local model connectivity.', model_status))
    from assistant.jobs import Jobs
    Jobs().register(registry)
    return registry
