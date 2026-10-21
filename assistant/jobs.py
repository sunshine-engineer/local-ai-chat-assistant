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
        self.google.sandbox_folder_id = self.store.get('config', {}).get('sandbox_folder_id')

    def register(self, registry):
        from assistant import evidence, resumes, tracking, package, layout
        commands = [
            ('init_tracker', 'Create a dedicated tab in the sandbox tracker copy.', lambda a: tracking.initialize(self, a)),
            ('track_application', 'Preview a tracker row; add --write to save it.', lambda a: tracking.track(self, a)),
            ('draft_cover_letter', 'Generate and save an optional cited cover-letter draft.', lambda a: package.cover_letter(self, a)),
            ('application_summary', 'Show application links, completion and remaining checks.', lambda a: package.summary(self, a)),
            ('draft_resume', 'Copy the recommended resume into a new sandbox tab.', lambda a: resumes.draft(self, a)),
            ('format_resume', 'Preview compact draft formatting; add --write to apply and invalidate approval.', lambda a: layout.format_resume(self, a)),
            ('suggest_edits', 'Suggest cited resume changes without writing to Google.', lambda a: resumes.suggest(self, a)),
            ('apply_edits', 'Apply selected reviewed edit IDs from a JSON payload.', lambda a: resumes.apply(self, a)),
            ('reset_edits', 'Keep current draft and discard local suggestions/pending edits after review.', lambda a: resumes.reset(self, a)),
            ('approve_resume', 'Record your review of draft content and layout.', lambda a: resumes.approve(self, a)),
            ('refresh_sources', 'Read configured reference files and resume tabs.', lambda a: evidence.refresh(self, a)),
            ('show_sources', 'List source catalogue and skipped files.', lambda a: evidence.show(self, a)),
            ('compare_resume', 'Compare an application ID against resume and project evidence.', lambda a: evidence.compare(self, a)),
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
                   'cover_letter_folder_id', 'tracker_id', 'tracker_tab',
                   'sandbox_folder_id', 'resume_tab_ids'}
        if set(data) - allowed:
            raise ValueError('Unknown configuration key(s). See docs/COMMANDS.md.')
        config = {**self.store.get('config', {}), **data}
        for key in ('jd_folder_id', 'resume_doc_id', 'tracker_id', 'cover_letter_folder_id', 'sandbox_folder_id'):
            if key in config:
                identifier(config[key])
        for key in ('source_folder_ids', 'local_source_dirs', 'resume_tab_ids'):
            if key in config and (not isinstance(config[key], list) or not all(isinstance(v, str) for v in config[key])):
                raise ValueError(f'{key} must be a list of strings.')
        for value in config.get('source_folder_ids', []):
            identifier(value)
        if 'tracker_tab' in config and not isinstance(config['tracker_tab'], str):
            raise ValueError('tracker_tab must be a string.')
        protected = self.store.get('protected_original_ids', [])
        if any(config.get(k) in protected for k in ('sandbox_folder_id', 'resume_doc_id', 'tracker_id', 'jd_folder_id', 'cover_letter_folder_id')):
            raise ValueError('An original resource is protected. Configure its sandbox copy instead.')
        self.store.put('config', config)
        self.google.sandbox_folder_id = config.get('sandbox_folder_id')
        return 'Configuration saved. /sources shows configured resources.'

    def sources(self, arguments=''):
        return json.dumps(self.store.get('config', {}), indent=2)

    def config(self, key):
        value = self.store.get('config', {}).get(key)
        if not value:
            raise ValueError(f'Configure {key} first with /configure.')
        return value

    def application(self, arguments):
        if not isinstance(arguments, str):
            raise ValueError('Application ID must be a string.')
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
