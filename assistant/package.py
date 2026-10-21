import json
import re
from datetime import datetime, timezone
from assistant.evidence import digest
from assistant.model import generate_json
from assistant.schemas import letter_for
from assistant.edit_policy import new_numeric_claim
from assistant.state import json_input
from assistant.google import tabs, body_text


def letter_text(jobs, app):
    match = re.search(r'/document/d/([A-Za-z0-9_-]+)', app.get('cover_letter_url', ''))
    if not match:
        raise ValueError('Create a cover-letter draft first.')
    document_tabs = tabs(jobs.google.document(match.group(1)))
    if len(document_tabs) != 1:
        raise ValueError('Cover-letter review requires a single-tab document; inspect the draft manually.')
    return body_text(document_tabs[0]['documentTab']['body'])


def show_letter(jobs, arguments):
    app_id, app = jobs.application(arguments)
    text = letter_text(jobs, app)
    return json.dumps({'draft_url': app['cover_letter_url'], 'text': text, 'text_hash': digest(text),
        'review_template': {'application_id': app_id, 'text_hash': digest(text),
            'decision': 'CHOOSE approve|omit', 'reviewed': True, 'note': ''},
        'warning': 'Inspect every claim against the accepted evidence. A valid citation does not establish implementation, scale or business impact.'}, indent=2)


def review_letter(jobs, arguments):
    data = json_input(arguments)
    if (set(data) != {'application_id', 'text_hash', 'decision', 'reviewed', 'note'} or data['reviewed'] is not True
            or data['decision'] not in ('approve', 'omit') or not isinstance(data['note'], str) or not data['note'].strip()):
        raise ValueError('Provide application_id, current text_hash, decision:approve|omit, reviewed:true and a review note.')
    app_id, app = jobs.application(data['application_id'])
    if digest(letter_text(jobs, app)) != data['text_hash']:
        raise ValueError('Cover-letter text changed; inspect /show_cover_letter before reviewing again.')
    record = {'decision': data['decision'], 'text_hash': data['text_hash'], 'note': data['note'].strip(),
              'recorded_at': datetime.now(timezone.utc).isoformat()}
    app['cover_letter_review'] = record
    app.setdefault('cover_letter_review_history', []).append(record)
    jobs.save(app_id, app)
    return 'Cover letter ' + ('approved for inclusion.' if data['decision'] == 'approve' else 'omitted from the application package; draft preserved.')


def included_letter_url(jobs, app):
    if not app.get('cover_letter_url'):
        return ''
    review = app.get('cover_letter_review', {})
    if review.get('decision') == 'omit':
        return ''
    if review.get('decision') != 'approve' or review.get('text_hash') != digest(letter_text(jobs, app)):
        raise ValueError('Review the current cover-letter draft with /show_cover_letter and /review_cover_letter before tracking.')
    return app['cover_letter_url']


def cover_letter(jobs, arguments, model=generate_json):
    app_id, app = jobs.application(arguments)
    if not app.get('source_snapshot'):
        raise ValueError('Run /compare_resume first to establish source evidence.')
    from assistant.comparison_review import generation_sources
    approved_sources = generation_sources(app)
    paragraphs = app.get('cover_letter_draft')
    if not paragraphs:
        output = model('Return {"paragraphs":[{"text":"one cover-letter paragraph","source_id":"supplied source ID",'
            '"quote":"exact supporting source quote"}]}. Write 2–4 concise first-person cover-letter paragraphs, at most 200 words in total, in the voice of the candidate, using I/my. Address the role directly; never describe or summarize the resume. Each paragraph must be supported by its source. '
            'Do not invent experience, metrics, names or employers. Do not add scale, scalability, multiple data sources, business impact, deployment or expertise claims unless the quoted source explicitly states them. Prefer modest literal wording over embellishment. Distinguish independent GenAI projects from commercial data engineering. '
            'No greeting or signature; those are handled separately.', {'jd': app['input']['jd'], 'sources': approved_sources}, schema=letter_for(approved_sources))
        paragraphs = output.get('paragraphs')
    if not isinstance(paragraphs, list) or not 2 <= len(paragraphs) <= 4:
        raise ValueError('Model must supply 2–4 cited cover-letter paragraphs.')
    sources = {s['id']: s['text'] for s in approved_sources}
    for p in paragraphs:
        if not isinstance(p, dict) or not all(isinstance(p.get(k), str) and p[k].strip() for k in ('text', 'source_id', 'quote')):
            raise ValueError('Invalid cited paragraph.')
        if p['source_id'] not in sources or p['quote'] not in sources[p['source_id']]:
            raise ValueError('Cover-letter citation is not present in its source.')
        if new_numeric_claim('', p['text'], p['quote']):
            raise ValueError('Cover-letter numerical claims must occur in their accepted quotation.')
    if not app.get('cover_letter_draft'):
        app['cover_letter_draft'] = paragraphs
        app['cover_letter_folder_id'] = jobs.config('cover_letter_folder_id')
        jobs.save(app_id, app)
    paragraphs = app['cover_letter_draft']
    text = 'Dear Hiring Team,\n\n' + '\n\n'.join(p['text'] for p in paragraphs) + '\n\nThank you for your consideration.\n'
    app['cover_letter_url'] = jobs.google.create_document(app['cover_letter_folder_id'], 'Cover Letter Draft — ' + app_id, app_id + '-cover', text)
    jobs.save(app_id, app)
    return json.dumps({'draft_url': app['cover_letter_url'], 'evidence': paragraphs,
        'review_required': 'Review factual meaning and layout before use. Verified quotes do not establish that every claim is supported.'}, indent=2)


def summary(jobs, arguments):
    app_id, app = jobs.application(arguments)
    missing = []
    from assistant.comparison_review import reviewed_sources
    try:
        reviewed_sources(app)
    except ValueError:
        missing.append('Review comparison evidence and select a resume')
    try:
        letter = included_letter_url(jobs, app) or ('Omitted' if app.get('cover_letter_url') else 'Not requested')
    except ValueError:
        letter = 'Unreviewed draft'
        missing.append('Review or omit the cover-letter draft')
    for key, description in [('jd_url', 'Save JD'), ('comparison', 'Compare resumes'), ('draft', 'Create resume draft'),
                             ('reviewed', 'Review and approve current resume'), ('tracker_url', 'Save tracker entry')]:
        if not app.get(key):
            missing.append(description)
    if app.get('pending_edits'):
        missing.append('Reconcile pending edits')
    if app.get('reviewed'):
        from assistant.resumes import find_tab
        from assistant.google import body_text
        state = app['draft']
        actual = body_text(find_tab(jobs.google.document(state['doc_id']), state['tab_id'])['documentTab']['body'])
        if digest(actual) != app.get('approved_text_hash'):
            missing.append('Resume changed since approval; review again')
    return json.dumps({'application_id': app_id,
        'status': 'Prepared for you to apply' if not missing else 'Preparation incomplete',
        'jd': app.get('jd_url'), 'resume': app.get('draft', {}).get('url'),
        'cover_letter': letter, 'cover_letter_draft': app.get('cover_letter_url'), 'tracker': app.get('tracker_url'),
        'remaining': missing, 'note': 'No job application has been submitted. Cover-letter and PDF layout checks remain manual.'}, indent=2)
