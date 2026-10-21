import json
from assistant.evidence import digest
from assistant.model import generate_json
from assistant.schemas import letter_for


def cover_letter(jobs, arguments, model=generate_json):
    app_id, app = jobs.application(arguments)
    if not app.get('source_snapshot'):
        raise ValueError('Run /compare_resume first to establish source evidence.')
    if not app.get('cover_letter_draft'):
        output = model('Return {"paragraphs":[{"text":"one cover-letter paragraph","source_id":"supplied source ID",'
            '"quote":"exact supporting source quote"}]}. Write 2–4 concise first-person cover-letter paragraphs, at most 200 words in total, in the voice of the candidate, using I/my. Address the role directly; never describe or summarize the resume. Each paragraph must be supported by its source. '
            'Do not invent experience, metrics, names or employers. Do not add scale, scalability, multiple data sources, business impact, deployment or expertise claims unless the quoted source explicitly states them. Prefer modest literal wording over embellishment. Distinguish independent GenAI projects from commercial data engineering. '
            'No greeting or signature; those are handled separately.', {'jd': app['input']['jd'], 'sources': app['source_snapshot']}, schema=letter_for(app['source_snapshot']))
        paragraphs = output.get('paragraphs')
        if not isinstance(paragraphs, list) or not 2 <= len(paragraphs) <= 4:
            raise ValueError('Model must supply 2–4 cited cover-letter paragraphs.')
        sources = {s['id']: s['text'] for s in app['source_snapshot']}
        for p in paragraphs:
            if not isinstance(p, dict) or not all(isinstance(p.get(k), str) and p[k].strip() for k in ('text', 'source_id', 'quote')):
                raise ValueError('Invalid cited paragraph.')
            if p['source_id'] not in sources or p['quote'] not in sources[p['source_id']]:
                raise ValueError('Cover-letter citation is not present in its source.')
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
        'cover_letter': app.get('cover_letter_url', 'Not requested'), 'tracker': app.get('tracker_url'),
        'remaining': missing, 'note': 'No job application has been submitted. Cover-letter and PDF layout checks remain manual.'}, indent=2)
