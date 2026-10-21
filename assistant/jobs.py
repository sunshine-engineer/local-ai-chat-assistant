import hashlib
import json
import re
from assistant.commands import Action
from assistant.state import Store, json_input
from assistant.google import Google, authenticate, FOLDER, DOC


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise ValueError('Use a Google resource ID, not a URL, in configuration.')
    return value


class Jobs:
    def __init__(self, store=None, google=None):
        self.store = store or Store()
        self.google = google or Google(self.store.root)

    def register(self, registry):
        commands = [
            ('google_connect', 'CLI only: connect using an OAuth Desktop client JSON path.', self.connect),
            ('configure', 'Save configured Google resource IDs and local source folders as JSON.', self.configure),
            ('sources', 'Show current resource configuration.', self.sources),
            ('save_jd', 'Save a JD JSON object to Google Docs; returns application ID.', self.save_jd),
        ]
        for name, description, handler in commands:
            def run(arguments, action=handler):
                with self.store.action_lock():
                    return action(arguments)
            registry.register(Action(name, description, run))

    def connect(self, arguments):
        import os
        if os.getenv('ASSISTANT_CLI') != '1':
            raise ValueError('Run /google_connect using python -m assistant.cli on your local desktop.')
        return authenticate(self.store.root, arguments.strip())

    def configure(self, arguments):
        data = json_input(arguments)
        allowed = {'source_folder_ids', 'local_source_dirs', 'jd_folder_id', 'resume_doc_id',
                   'cover_letter_folder_id', 'tracker_id', 'tracker_tab', 'tracker_columns'}
        if set(data) - allowed:
            raise ValueError('Unknown configuration key(s). See docs/COMMANDS.md.')
        config = {**self.store.get('config', {}), **data}
        for key in ('jd_folder_id', 'resume_doc_id', 'tracker_id', 'cover_letter_folder_id'):
            if key in config:
                identifier(config[key])
        for key in ('source_folder_ids', 'local_source_dirs'):
            if key in config and (not isinstance(config[key], list) or not all(isinstance(v, str) for v in config[key])):
                raise ValueError(f'{key} must be a list of strings.')
        for value in config.get('source_folder_ids', []):
            identifier(value)
        if 'tracker_tab' in config and not isinstance(config['tracker_tab'], str):
            raise ValueError('tracker_tab must be a string.')
        self.store.put('config', config)
        return 'Configuration saved. /sources shows configured resources.'

    def sources(self, arguments=''):
        return json.dumps(self.store.get('config', {}), indent=2)

    def config(self, key):
        value = self.store.get('config', {}).get(key)
        if not value:
            raise ValueError(f'Configure {key} first with /configure.')
        return value

    def application(self, arguments):
        app_id = arguments.strip()
        app = self.store.get('app:' + app_id)
        if not app:
            raise ValueError('Unknown application ID. Run /save_jd first.')
        return app_id, app

    def save(self, app_id, app):
        self.store.put('app:' + app_id, app)

    def save_jd(self, arguments):
        data = json_input(arguments)
        allowed = {'jd', 'company', 'role', 'url'}
        if set(data) - allowed or not isinstance(data.get('jd'), str) or not data['jd'].strip():
            raise ValueError('Provide jd text plus optional company, role and url strings.')
        if not all(isinstance(v, str) for v in data.values()):
            raise ValueError('JD fields must be strings.')
        if len(data['jd']) > 100000:
            raise ValueError('JD is too long (limit 100,000 characters).')
        app_id = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]
        app = self.store.get('app:' + app_id, {'input': data})
        folder = app.setdefault('jd_folder_id', self.config('jd_folder_id'))
        self.save(app_id, app)
        text = (f"{data.get('role') or 'Role unknown'} — {data.get('company') or 'Company unknown'}\n\n"
                f"Job URL: {data.get('url') or 'Unknown'}\nApplication ID: {app_id}\n\nOriginal job description\n\n{data['jd']}\n")
        app['jd_url'] = self.google.create_document(folder, f'JD — {app_id}', app_id + '-jd', text)
        self.save(app_id, app)
        return f"Application ID: {app_id}\nJD saved and content verified: {app['jd_url']}"
