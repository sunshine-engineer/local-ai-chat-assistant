"""Explicit formatting for assistant-owned drafts; never rewrites resume claims."""
import json
from math import isclose
from assistant.google import body_text
from assistant.resumes import find_tab, unchanged_tabs, utf16


def compact_requests(tab_id, text):
    target = {'tabId': tab_id, 'startIndex': 1, 'endIndex': 1 + utf16(text)}
    return [
        {'updateDocumentStyle': {'tabId': tab_id,
            'documentStyle': {k: {'magnitude': 36, 'unit': 'PT'} for k in
                ('marginTop', 'marginBottom', 'marginLeft', 'marginRight')},
            'fields': 'marginTop,marginBottom,marginLeft,marginRight'}},
        {'updateTextStyle': {'range': target,
            'textStyle': {'fontSize': {'magnitude': 10.5, 'unit': 'PT'}}, 'fields': 'fontSize'}},
        {'updateParagraphStyle': {'range': target,
            'paragraphStyle': {'lineSpacing': 105,
                'spaceAbove': {'magnitude': 0, 'unit': 'PT'},
                'spaceBelow': {'magnitude': 2, 'unit': 'PT'}},
            'fields': 'lineSpacing,spaceAbove,spaceBelow'}},
    ]


def verify_compact(tab):
    def points(value, expected):
        return value.get('unit') == 'PT' and isclose(value.get('magnitude', 0), expected, abs_tol=0.001)

    style = tab.get('documentStyle', {})
    for key in ('marginTop', 'marginBottom', 'marginLeft', 'marginRight'):
        if not points(style.get(key, {}), 36):
            raise ValueError('Compact margin readback did not match; retry the same command.')
    for item in tab['body'].get('content', []):
        if 'paragraph' not in item:
            continue
        paragraph = item['paragraph']
        style = paragraph.get('paragraphStyle', {})
        if (not isclose(style.get('lineSpacing', 0), 105, abs_tol=0.001) or
                not points(style.get('spaceAbove', {}), 0) or
                not points(style.get('spaceBelow', {}), 2)):
            raise ValueError('Compact paragraph readback did not match; retry the same command.')
        for element in paragraph.get('elements', []):
            run = element.get('textRun', {})
            if run.get('content', '').strip() and not points(run.get('textStyle', {}).get('fontSize', {}), 10.5):
                raise ValueError('Compact font readback did not match; retry the same command.')


def format_resume(jobs, arguments):
    parts = arguments.strip().split()
    if len(parts) not in (1, 2) or (len(parts) == 2 and parts[1] != '--write'):
        raise ValueError('Use /format_resume APPLICATION_ID [--write].')
    app_id, app = jobs.application(parts[0])
    state = app.get('draft', {})
    if not state.get('ready') or app.get('pending_edits'):
        raise ValueError('A completed draft without pending edits is required.')
    if len(parts) == 1:
        return json.dumps({'preset': 'compact', 'font_points': 10.5,
            'margins_points': 36, 'line_spacing_percent': 105,
            'paragraph_space_above_points': 0, 'paragraph_space_below_points': 2,
            'resume': state['url'], 'write_command': f'/format_resume {app_id} --write',
            'review_required': 'Preserves text, bold, links and alignment. Review the exported PDF; no page-count guarantee. Writing invalidates approval.'}, indent=2)
    doc_id, tab_id = state['doc_id'], state['tab_id']
    jobs.google.check_write(doc_id)
    doc = jobs.google.document(doc_id)
    target = find_tab(doc, tab_id)
    if target['tabProperties'].get('title') != state.get('title') or state.get('title') != 'Assistant — ' + app_id:
        raise ValueError('Formatting is limited to this application’s owned draft tab.')
    text = body_text(target['documentTab']['body'])
    before = unchanged_tabs(doc, tab_id)
    # Invalidate before the remote call: a timed-out write may have completed.
    app['reviewed'] = False
    app.pop('approved_text_hash', None)
    jobs.save(app_id, app)
    jobs.google.batch(doc_id, compact_requests(tab_id, text), doc['revisionId'])
    checked = jobs.google.document(doc_id)
    actual = find_tab(checked, tab_id)['documentTab']
    if body_text(actual['body']) != text or unchanged_tabs(checked, tab_id) != before:
        raise ValueError('Formatting verification failed; inspect the draft before continuing.')
    verify_compact(actual)
    app['layout_preset'] = 'compact'
    jobs.save(app_id, app)
    return 'Compact formatting applied; text and other tabs preserved. Review the PDF and run /approve_resume again.\n' + state['url']
