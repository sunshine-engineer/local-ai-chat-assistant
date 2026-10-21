"""Write prepared applications into a dedicated tab in the copied workbook."""
import hashlib
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote
from assistant.resumes import find_tab
from assistant.google import body_text
from assistant.evidence import digest
from assistant.state import json_input

HEADERS = ['Application ID', 'Company', 'Role', 'Job URL', 'JD', 'Resume', 'Cover Letter', 'Status', 'Prepared Date']
KEYS = ['application_id', 'company', 'role', 'job_url', 'jd_url', 'resume_url', 'cover_letter_url', 'status', 'prepared_date']


def settings(jobs):
    sheet_id, tab = jobs.config('tracker_id'), jobs.config('tracker_tab')
    if tab != 'Assistant Applications':
        raise ValueError('This version writes only to a dedicated Assistant Applications tab in the sandbox workbook.')
    jobs.google.check_write(sheet_id)
    url = 'https://sheets.googleapis.com/v4/spreadsheets/' + quote(sheet_id, safe='')
    return sheet_id, tab, url


def quoted_tab(tab):
    return "'" + tab.replace("'", "''") + "'"


def values(jobs, url, tab, cells):
    a1 = quoted_tab(tab) + '!' + cells
    return jobs.google.call('GET', url + '/values/' + quote(a1, safe=''), params={'valueRenderOption': 'FORMULA'}).get('values', [])


def initialize(jobs, arguments=''):
    spreadsheet_id, tab, url = settings(jobs)
    metadata = jobs.google.call('GET', url, params={'fields': 'sheets.properties'})
    existing = [s['properties'] for s in metadata.get('sheets', []) if s['properties']['title'] == tab]
    if existing:
        if values(jobs, url, tab, 'A1:I1') != [HEADERS]:
            raise ValueError('Assistant Applications exists with unexpected headers; refusing to alter it.')
        return 'Assistant Applications tab already exists with expected headers.'
    sheet_id = int(hashlib.sha256((spreadsheet_id + tab).encode()).hexdigest()[:7], 16)
    if any(s['properties']['sheetId'] == sheet_id for s in metadata.get('sheets', [])):
        raise ValueError('Reserved sheet ID collides with an existing tab.')
    requests = [
        {'addSheet': {'properties': {'sheetId': sheet_id, 'title': tab,
            'gridProperties': {'rowCount': 1000, 'columnCount': len(HEADERS), 'frozenRowCount': 1}}}},
        {'updateCells': {'start': {'sheetId': sheet_id, 'rowIndex': 0, 'columnIndex': 0},
            'rows': [{'values': [{'userEnteredValue': {'stringValue': h}} for h in HEADERS]}], 'fields': 'userEnteredValue'}},
        {'repeatCell': {'range': {'sheetId': sheet_id, 'startRowIndex': 0, 'endRowIndex': 1},
            'cell': {'userEnteredFormat': {'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.85, 'green': 0.91, 'blue': 0.98}}}, 'fields': 'userEnteredFormat'}},
    ]
    jobs.google.call('POST', url + ':batchUpdate', json={'requests': requests})
    if values(jobs, url, tab, 'A1:I1') != [HEADERS]:
        raise ValueError('Tracker initialization readback failed.')
    return 'Created Assistant Applications in the sandbox copy. Existing tabs preserved.'


def proposed_row(jobs, app_id, app):
    draft = app.get('draft', {})
    if not app.get('reviewed') or not draft.get('ready') or app.get('pending_edits'):
        raise ValueError('Review the resume and run /approve_resume before tracking.')
    actual = body_text(find_tab(jobs.google.document(draft['doc_id']), draft['tab_id'])['documentTab']['body'])
    if digest(actual) != app.get('approved_text_hash'):
        raise ValueError('Resume changed after approval. Review and approve it again.')
    data = app['input']
    date = app.get('prepared_date') or datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat()
    return dict(zip(KEYS, [app_id, data.get('company', ''), data.get('role', ''), data.get('url', ''),
        app.get('jd_url', ''), draft['url'], app.get('cover_letter_url', ''), 'Prepared', date]))


def track(jobs, arguments):
    # Default is a preview; writing requires the explicit write flag.
    parts = arguments.strip().split()
    if len(parts) not in (1, 2) or (len(parts) == 2 and parts[1] != '--write'):
        raise ValueError('Use /track_application APPLICATION_ID [--write].')
    app_id, app = jobs.application(parts[0])
    row = proposed_row(jobs, app_id, app)
    if len(parts) == 1:
        return json.dumps({'proposed_row': row, 'write_command': f'/track_application {app_id} --write'}, indent=2)
    spreadsheet_id, tab, url = settings(jobs)
    if app.get('tracker_target') and app['tracker_target'] != {'id': spreadsheet_id, 'tab': tab}:
        raise ValueError('This application already targets a different tracker. Restore its original configuration.')
    app.setdefault('prepared_date', row['prepared_date'])
    app.setdefault('tracker_target', {'id': spreadsheet_id, 'tab': tab})
    jobs.save(app_id, app)
    all_rows = values(jobs, url, tab, 'A1:I1000')
    if not all_rows or all_rows[0] != HEADERS:
        raise ValueError('Run /init_tracker first; headers must match exactly.')
    matches = [(i + 1, r) for i, r in enumerate(all_rows) if r and r[0] == app_id]
    if len(matches) > 1:
        raise ValueError('Duplicate application IDs found; reconcile manually.')
    expected = [row[k] for k in KEYS]
    if matches:
        target_row, actual = matches[0]
        if (actual + [''] * len(HEADERS))[:len(HEADERS)] != expected:
            raise ValueError('Existing tracker entry differs from this application. Review it manually; no overwrite occurred.')
    else:
        if row['job_url'] and any(len(r) > 3 and r[3] == row['job_url'] for r in all_rows[1:]):
            raise ValueError('This job URL is already tracked under a different application ID.')
        target_row = app.setdefault('tracker_pending_row', len(all_rows) + 1)
        if target_row > 1000:
            raise ValueError('Tracker capacity reached (999 applications). Extend support before continuing.')
        jobs.save(app_id, app)
        current = values(jobs, url, tab, f'A{target_row}:I{target_row}')
        if any(any(v != '' for v in r) for r in current):
            raise ValueError('Reserved tracker row is occupied; refusing to overwrite content or formulas.')
        a1 = quoted_tab(tab) + f'!A{target_row}:I{target_row}'
        # RAW avoids interpreting malicious JD-derived cell text as formulas.
        jobs.google.call('PUT', url + '/values/' + quote(a1, safe=''),
                         params={'valueInputOption': 'RAW'}, json={'range': a1, 'values': [expected]})
    verified = values(jobs, url, tab, f'A{target_row}:I{target_row}')
    if not verified or (verified[0] + [''] * len(HEADERS))[:len(HEADERS)] != expected:
        raise ValueError('Tracker readback did not match; rerun the same write command to reconcile.')
    app['tracker_url'] = f'https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit'
    app['tracker_row'] = target_row
    jobs.save(app_id, app)
    return f"Prepared application verified in tracker row {target_row}. {app['tracker_url']}"
