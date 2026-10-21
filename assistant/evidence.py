import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import quote
from assistant.google import DOC, tabs, body_text
from assistant.model import generate_json
from assistant.schemas import matches_for


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def refresh(jobs, arguments=''):
    config = jobs.store.get('config', {})
    sources, skipped = [], []
    resume_doc = jobs.config('resume_doc_id')
    selected = config.get('resume_tab_ids', [])
    doc = jobs.google.document(resume_doc)
    for tab in tabs(doc):
        props = tab['tabProperties']
        if selected and props['tabId'] not in selected:
            continue
        if not selected and ('cover letter' in props.get('title', '').lower() or props.get('title', '').startswith('Assistant —')):
            continue
        text = body_text(tab['documentTab']['body'])
        if text.strip():
            sources.append({'id': resume_doc + ':' + props['tabId'], 'kind': 'resume',
                'title': props.get('title', ''), 'text': text, 'doc_id': resume_doc, 'tab_id': props['tabId'],
                'url': f'https://docs.google.com/document/d/{resume_doc}/edit?tab={props["tabId"]}'})
    for folder in config.get('source_folder_ids', []):
        for file in jobs.google.files(f"'{folder}' in parents and trashed=false"):
            if file['id'] == resume_doc:
                continue
            if file['mimeType'] == DOC:
                for tab in tabs(jobs.google.document(file['id'])):
                    props = tab['tabProperties']
                    sources.append({'id': file['id'] + ':' + props['tabId'], 'kind': 'evidence',
                        'title': file['name'] + ' / ' + props.get('title', ''),
                        'text': body_text(tab['documentTab']['body']),
                        'url': f'https://docs.google.com/document/d/{file["id"]}/edit?tab={props["tabId"]}'})
            elif file['mimeType'] in ('text/plain', 'text/markdown'):
                # Explicitly report unsupported remote text instead of silently omitting it.
                skipped.append(file['name'] + ': download as local Markdown/text for this version')
            else:
                skipped.append(file['name'] + ': unsupported format or subfolder (no recursive Drive scan)')
    for directory in config.get('local_source_dirs', []):
        root = Path(directory).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f'Local source directory does not exist: {root}')
        for path in sorted(root.rglob('*')):
            if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
                continue
            if path.suffix.lower() not in ('.md', '.txt') or any(p.startswith('.') for p in path.relative_to(root).parts):
                continue
            if path.stat().st_size > 100000:
                skipped.append(str(path) + ': exceeds 100 KB')
                continue
            sources.append({'id': 'local:' + digest(str(path))[:16], 'kind': 'evidence',
                'title': str(path.relative_to(root)), 'text': path.read_text(encoding='utf-8'), 'url': str(path)})
    if not any(s['kind'] == 'resume' for s in sources):
        raise ValueError('No non-empty resume tabs found. Check resume_tab_ids.')
    if sum(len(s['text']) for s in sources) > 2000000:
        raise ValueError('Source catalogue exceeds 2 million characters. Narrow the configured sources.')
    jobs.store.put('catalogue', {'sources': sources, 'skipped': skipped, 'digest': digest(sources)})
    return json.dumps({'sources': [{k: v for k, v in s.items() if k != 'text'} for s in sources], 'skipped': skipped}, indent=2)


def show(jobs, arguments=''):
    catalogue = jobs.store.get('catalogue')
    if not catalogue:
        raise ValueError('Run /refresh_sources first.')
    return json.dumps({'sources': [{k: v for k, v in s.items() if k != 'text'} for s in catalogue['sources']], 'skipped': catalogue['skipped']}, indent=2)


def validate_requirements(output, jd):
    requirements = output.get('requirements')
    if not isinstance(requirements, list) or not requirements or len(requirements) > 30:
        raise ValueError('Model must return 1–30 JD requirements.')
    if not all(isinstance(r, str) and r.strip() and r in jd for r in requirements):
        raise ValueError('Model requirement is not an exact quote from the JD.')
    return list(dict.fromkeys(requirements))


def validate_matches(output, requirements, source_text):
    matches = output.get('matches')
    if not isinstance(matches, list) or len(matches) != len(requirements):
        raise ValueError('Model must assess every extracted requirement.')
    by_requirement = {}
    for row in matches:
        if not isinstance(row, dict):
            raise ValueError('Invalid match output.')
        requirement, status, evidence = row.get('requirement'), row.get('status'), row.get('quote')
        if requirement not in requirements or requirement in by_requirement or status not in ('supported', 'partial', 'gap'):
            raise ValueError('Invalid requirement or status in comparison.')
        if not isinstance(evidence, str) or (status != 'gap' and (not evidence.strip() or evidence not in source_text)):
            raise ValueError('Comparison evidence must be an exact source quote.')
        if status == 'gap' and evidence:
            raise ValueError('A gap must not claim supporting evidence.')
        by_requirement[requirement] = {'requirement': requirement, 'status': status, 'quote': evidence}
    return [by_requirement[r] for r in requirements]


def assess(requirements, source, kind, model):
    size = int(os.getenv('ASSISTANT_REQUIREMENT_BATCH_SIZE', '3'))
    if not 1 <= size <= 5:
        raise ValueError('ASSISTANT_REQUIREMENT_BATCH_SIZE must be between 1 and 5.')
    matches = []
    for start in range(0, len(requirements), size):
        batch = requirements[start:start + size]
        instruction = ('Return {"matches":[{"requirement":"exact supplied requirement","status":"supported|partial|gap",'
            '"quote":"exact source quote, empty for gap"}]}. Assess EVERY supplied requirement, exactly once in supplied order. '
            'Use supported only when ALL skills, duties and qualifiers in that sentence are explicitly evidenced. Use partial when only some are evidenced, and gap when none are evidenced. '
            'Portfolio experience does not support a requirement for commercial production experience. Do not infer missing years or qualifications. ')
        if kind == 'evidence':
            instruction += 'This is supporting documentation, not proof of employment or deployment.'
        output = model(instruction, {'source': source, 'requirements': batch}, schema=matches_for(batch, source))
        matches.extend(validate_matches(output, batch, source))
    return matches


def compare(jobs, arguments, model=generate_json):
    app_id, app = jobs.application(arguments)
    if app.get('draft'):
        raise ValueError('Comparison is fixed once a draft is created. Continue reviewing that draft; use a new JD input for a separate application variant.')
    catalogue = jobs.store.get('catalogue')
    if not catalogue:
        raise ValueError('Run /refresh_sources first.')
    from assistant.requirements import selected
    requirements = selected(app)
    comparisons = []
    for source in catalogue['sources']:
        if source['kind'] != 'resume':
            continue
        matches = assess(requirements, source['text'], 'resume', model)
        counts = {status: sum(m['status'] == status for m in matches) for status in ('supported', 'partial', 'gap')}
        comparisons.append({'source_id': source['id'], 'title': source['title'], 'url': source['url'], 'counts': counts, 'matches': matches})
    comparisons.sort(key=lambda c: (-c['counts']['supported'], -c['counts']['partial'], c['source_id']))
    if not comparisons:
        raise ValueError('No resumes in catalogue.')
    # Project evidence is assessed separately, never counted as experience on the resume.
    evidence = []
    for source in catalogue['sources']:
        if source['kind'] != 'evidence' or not source['text'].strip():
            continue
        evidence.append({'source_id': source['id'], 'url': source['url'],
                         'matches': assess(requirements, source['text'], 'evidence', model)})
    result = {'requirements': requirements, 'recommended_source_id': comparisons[0]['source_id'],
              'resumes': comparisons, 'project_evidence': evidence, 'catalogue_digest': catalogue['digest'],
              'warning': 'Counts cover only the manually selected JD requirements. Model judgments require human review. Exact quotations are verified; semantic support and source truth are not. Counts are not an ATS score or hiring prediction.'}
    app['comparison'] = result
    app['source_snapshot'] = catalogue['sources']
    jobs.save(app_id, app)
    return json.dumps(result, indent=2)
