"""Google REST adapter. Does not import chat or application business logic."""
import json
from pathlib import Path
from urllib.parse import quote

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/spreadsheets',
]
DOC = 'application/vnd.google-apps.document'
FOLDER = 'application/vnd.google-apps.folder'


class GoogleError(ValueError):
    pass


def authenticate(root, client_file):
    from google_auth_oauthlib.flow import InstalledAppFlow
    path = Path(client_file).expanduser().resolve()
    if not path.is_file():
        raise ValueError('OAuth Desktop client JSON file not found.')
    flow = InstalledAppFlow.from_client_secrets_file(str(path), SCOPES)
    credentials = flow.run_local_server(port=0, open_browser=True)
    save_token(root, credentials)
    return 'Google connected. Credentials saved privately on this machine.'


def save_token(root, credentials):
    path = Path(root) / 'token.json'
    # Open with restrictive permissions before writing a token.
    import os
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(credentials.to_json())
    path.chmod(0o600)


def authorized_session(root):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import AuthorizedSession, Request
    path = Path(root) / 'token.json'
    if not path.exists():
        raise GoogleError('Google is not connected. Run /google_connect in the terminal CLI.')
    try:
        credentials = Credentials.from_authorized_user_file(str(path), SCOPES)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            save_token(root, credentials)
        if not credentials.valid:
            raise GoogleError('Google authorization expired. Reconnect using /google_connect.')
        return AuthorizedSession(credentials)
    except (OSError, ValueError) as exc:
        raise GoogleError('Google credentials are invalid; reconnect.') from exc


def tabs(document):
    def walk(items):
        for tab in items:
            yield tab
            yield from walk(tab.get('childTabs', []))
    return list(walk(document.get('tabs', [])))


def body_text(body):
    out = []
    for item in body.get('content', []):
        if 'paragraph' in item:
            out.extend(e.get('textRun', {}).get('content', '') for e in item['paragraph'].get('elements', []))
        if 'table' in item:
            for row in item['table'].get('tableRows', []):
                for cell in row.get('tableCells', []):
                    out.append(body_text(cell))
    return ''.join(out)


class Google:
    def __init__(self, root, session=None):
        self.root, self._session = root, session

    def call(self, method, url, **kwargs):
        try:
            if self._session is None:
                self._session = authorized_session(self.root)
            response = self._session.request(method, url, timeout=60, **kwargs)
            if not response.ok:
                raise GoogleError(f'Google request failed (HTTP {response.status_code}); check permissions and configuration. Writes may require reconciliation before retry.')
            return response.json() if response.content else {}
        except GoogleError:
            raise
        except Exception as exc:
            # Never surface HTTP bodies, tokens or credentials in chat.
            raise GoogleError('Google connection failed; check network and authorization. A remote write may have completed; rerun the same command to reconcile.') from exc

    def metadata(self, file_id):
        return self.call('GET', 'https://www.googleapis.com/drive/v3/files/' + quote(file_id, safe=''),
                         params={'fields': 'id,name,mimeType,parents,trashed'})

    def document(self, doc_id):
        return self.call('GET', 'https://docs.googleapis.com/v1/documents/' + quote(doc_id, safe=''),
                         params={'includeTabsContent': 'true'})

    def batch(self, doc_id, requests, revision):
        return self.call('POST', 'https://docs.googleapis.com/v1/documents/' + quote(doc_id, safe='') + ':batchUpdate',
                         json={'requests': requests, 'writeControl': {'requiredRevisionId': revision}})

    def files(self, query):
        result, page = [], None
        while True:
            params = {'q': query, 'fields': 'nextPageToken,files(id,name,mimeType,parents)', 'pageSize': 100}
            if page:
                params['pageToken'] = page
            response = self.call('GET', 'https://www.googleapis.com/drive/v3/files', params=params)
            result.extend(response.get('files', []))
            page = response.get('nextPageToken')
            if not page:
                return result

    def create_document(self, folder, title, key, text):
        if self.metadata(folder).get('mimeType') != FOLDER:
            raise ValueError('Output destination must be a Google Drive folder.')
        matches = self.files(f"'{folder}' in parents and trashed=false and appProperties has {{ key='assistant_key' and value='{key}' }}")
        if len(matches) > 1:
            raise ValueError('Duplicate remote documents detected; reconcile them manually.')
        file = matches[0] if matches else self.call('POST', 'https://www.googleapis.com/drive/v3/files',
            params={'fields': 'id'}, json={'name': title, 'mimeType': DOC, 'parents': [folder],
                                          'appProperties': {'assistant_key': key}})
        doc = self.document(file['id'])
        all_tabs = tabs(doc)
        if len(all_tabs) != 1:
            raise ValueError('Generated document has unexpected tabs; review manually.')
        tab = all_tabs[0]
        actual = body_text(tab['documentTab']['body'])
        if not actual.strip():
            self.batch(file['id'], [{'insertText': {'location': {'index': 1, 'tabId': tab['tabProperties']['tabId']}, 'text': text}}], doc['revisionId'])
        elif actual.rstrip('\n') != text.rstrip('\n'):
            raise ValueError('Generated document was edited externally; refusing to overwrite it.')
        check = self.document(file['id'])
        if body_text(tabs(check)[0]['documentTab']['body']).rstrip('\n') != text.rstrip('\n'):
            raise ValueError('Google Doc content readback did not match.')
        return 'https://docs.google.com/document/d/' + file['id'] + '/edit'
