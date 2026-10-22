"""Create owned draft tabs and apply explicitly selected, reviewed changes.

File: assistant/resumes.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import json

from assistant.edit_policy import new_numeric_claim, protected_edit
from assistant.evidence import digest
from assistant.google import body_text, tabs
from assistant.model import generate_json
from assistant.schemas import edits_for
from assistant.state import json_input


def utf16(text):
    """Count UTF-16 code units for Google Docs index calculations.

    Args:
        text: Text to inspect or transform without changing the original value.

    Returns:
        Number of UTF-16 code units in the input.

    Examples:
        >>> utf16("A😀")
        3
    """
    return len(text.encode("utf-16-le")) // 2


def find_tab(document, tab_id):
    """Find a document tab by its stable identifier.

    Args:
        document: Google document response containing nested tabs.
        tab_id: Stable Google document tab identifier.

    Returns:
        Matching Google document tab structure.

    Raises:
        ValueError: The requested tab no longer exists.
    """
    for tab in tabs(document):
        if tab["tabProperties"]["tabId"] == tab_id:
            return tab
    raise ValueError("Resume tab no longer exists.")


def unchanged_tabs(document, except_id):
    """Fingerprint every tab except the owned write target.

    Args:
        document: Google document response containing nested tabs.
        except_id: Tab identifier excluded from the preservation fingerprint.

    Returns:
        Mapping of untouched tab IDs to content/style digests.
    """
    return {
        t["tabProperties"]["tabId"]: digest(t["documentTab"])
        for t in tabs(document)
        if t["tabProperties"]["tabId"] != except_id
    }


def clone_requests(source, target_id):
    """Build paragraph/text cloning requests and reject unsupported structures.

    Args:
        source: Frozen source record or Google tab structure required by this operation.
        target_id: Identifier of the new owned destination tab.

    Returns:
        Pair of exact source text and destination-only API requests.

    Raises:
        ValueError: The source has empty text or unsupported lists, tables, suggestions, objects or document structures.
    """
    document_tab = source["documentTab"]
    for key in ("headers", "footers", "footnotes", "inlineObjects", "positionedObjects"):
        if document_tab.get(key):
            raise ValueError(f"Resume has unsupported {key}; use a paragraph-only template.")
    text = body_text(document_tab["body"])
    if not text.endswith("\n") or not text.strip():
        raise ValueError("Resume must contain non-empty paragraphs.")
    requests = [{"insertText": {"location": {"index": 1, "tabId": target_id}, "text": text[:-1]}}]
    # Each tab has its own page and named styles; never update another tab's style.
    document_style = {
        k: v
        for k, v in document_tab.get("documentStyle", {}).items()
        if k
        in {
            "background",
            "pageNumberStart",
            "marginTop",
            "marginBottom",
            "marginRight",
            "marginLeft",
            "pageSize",
            "marginHeader",
            "marginFooter",
        }
    }
    if document_style:
        requests.append(
            {
                "updateDocumentStyle": {
                    "tabId": target_id,
                    "documentStyle": document_style,
                    "fields": ",".join(document_style),
                }
            }
        )
    for named in document_tab.get("namedStyles", {}).get("styles", []):
        style = {
            k: v for k, v in named.items() if k in {"namedStyleType", "textStyle", "paragraphStyle"}
        }
        if style.get("paragraphStyle"):
            style["paragraphStyle"] = {
                k: v for k, v in style["paragraphStyle"].items() if k != "headingId"
            }
        if style.get("namedStyleType"):
            requests.append(
                {
                    "updateNamedStyle": {
                        "tabId": target_id,
                        "namedStyle": style,
                        "fields": ",".join(style),
                    }
                }
            )
    position = 1
    for item in document_tab["body"].get("content", []):
        if "sectionBreak" in item and item.get("startIndex", 0) == 0:
            continue
        if "paragraph" not in item:
            raise ValueError("Tables, images, and section breaks are unsupported for tab cloning.")
        paragraph = item["paragraph"]
        if set(paragraph) - {"elements", "paragraphStyle"}:
            raise ValueError("Lists and suggested changes require a simpler resume template.")
        start = position
        for element in paragraph.get("elements", []):
            if "textRun" not in element or set(element) - {"startIndex", "endIndex", "textRun"}:
                raise ValueError("Non-text resume elements are unsupported.")
            run = element["textRun"]
            if set(run) - {"content", "textStyle"}:
                raise ValueError("Suggested text changes must be resolved first.")
            end = position + utf16(run["content"])
            style = run.get("textStyle", {})
            if style:
                requests.append(
                    {
                        "updateTextStyle": {
                            "range": {"tabId": target_id, "startIndex": position, "endIndex": end},
                            "textStyle": style,
                            "fields": ",".join(style),
                        }
                    }
                )
            position = end
        style = {k: v for k, v in paragraph.get("paragraphStyle", {}).items() if k != "headingId"}
        if style and position > start:
            requests.append(
                {
                    "updateParagraphStyle": {
                        "range": {"tabId": target_id, "startIndex": start, "endIndex": position},
                        "paragraphStyle": style,
                        "fields": ",".join(style),
                    }
                }
            )
    return text, requests


def draft(jobs, arguments):
    """Create or reconcile a reviewed resume copy in its owned sandbox tab.

    Args:
        jobs: Jobs coordinator providing workflow state and the Google adapter.
        arguments: Application ID returned by /save_jd.

    Returns:
        Verified owned draft URL and manual-layout-review guidance.

    Raises:
        ValueError: Comparison review, source snapshot, supported structure or owned draft reconciliation/preservation fails.
    """
    app_id, app = jobs.application(arguments)
    if app.get("draft", {}).get("ready"):
        return "Draft already exists: " + app["draft"]["url"]
    comparison = app.get("comparison")
    if not comparison:
        raise ValueError("Run /compare_resume first.")
    from assistant.comparison_review import reviewed_sources

    reviewed_sources(app)
    selected = next(
        s for s in app["source_snapshot"] if s["id"] == comparison["recommended_source_id"]
    )
    doc_id = selected["doc_id"]
    jobs.google.check_write(doc_id)
    doc = jobs.google.document(doc_id)
    source = find_tab(doc, selected["tab_id"])
    if body_text(source["documentTab"]["body"]) != selected["text"]:
        raise ValueError("Source resume changed since comparison. Refresh and compare again.")
    # Validate support before creating a new tab.
    expected, _ = clone_requests(source, "placeholder")
    title = "Assistant — " + app_id
    draft_state = app.setdefault("draft", {"doc_id": doc_id, "title": title, "ready": False})
    if draft_state["doc_id"] != doc_id:
        raise ValueError(
            "Existing draft belongs to a different resume. Use its original comparison."
        )
    jobs.save(app_id, app)
    matches = [t for t in tabs(doc) if t["tabProperties"].get("title") == title]
    if len(matches) > 1:
        raise ValueError("Multiple draft tabs found; reconcile manually.")
    if not matches:
        jobs.google.batch(
            doc_id, [{"addDocumentTab": {"tabProperties": {"title": title}}}], doc["revisionId"]
        )
        doc = jobs.google.document(doc_id)
        matches = [t for t in tabs(doc) if t["tabProperties"].get("title") == title]
    if len(matches) != 1:
        raise ValueError("Draft tab creation could not be verified. Retry the same command.")
    target = matches[0]
    tab_id = target["tabProperties"]["tabId"]
    before = unchanged_tabs(doc, tab_id)
    actual = body_text(target["documentTab"]["body"])
    if not actual.strip():
        _, requests = clone_requests(source, tab_id)
        jobs.google.batch(doc_id, requests, doc["revisionId"])
    elif actual != expected:
        raise ValueError("Draft tab differs from the expected copy. Refusing to overwrite.")
    checked = jobs.google.document(doc_id)
    if (
        body_text(find_tab(checked, tab_id)["documentTab"]["body"]) != expected
        or unchanged_tabs(checked, tab_id) != before
    ):
        raise ValueError("Draft verification failed or another tab changed; inspect manually.")
    draft_state.update(
        {
            "tab_id": tab_id,
            "text": expected,
            "ready": True,
            "url": f"https://docs.google.com/document/d/{doc_id}/edit?tab={tab_id}",
        }
    )
    jobs.save(app_id, app)
    return (
        "Resume copied into a new tab. Content verified; inspect layout before applying.\n"
        + draft_state["url"]
    )


def validate_edits(output, text, sources):
    """Reject unsupported citations, protected spans, new numbers and overlapping edits.

    Args:
        output: Structured model output to validate.
        text: Text to inspect or transform without changing the original value.
        sources: Evidence records with stable identifiers and literal source text.

    Returns:
        Validated non-overlapping edit records with exact accepted source citations.

    Raises:
        ValueError: Edits exceed limits, lack exact accepted citations, overlap, change protected spans or introduce unsupported digit values.
    """
    edits = output.get("edits")
    if not isinstance(edits, list) or len(edits) > 20:
        raise ValueError("Model must return at most 20 edits.")
    by_id = {s["id"]: s["text"] for s in sources}
    validated = []
    spans = []
    for edit in edits:
        if not isinstance(edit, dict):
            raise ValueError("Invalid edit.")
        before, after, source_id, quote = (
            edit.get(k) for k in ("before", "after", "source_id", "quote")
        )
        if not all(isinstance(v, str) for v in (before, after, source_id, quote)):
            raise ValueError("Edit fields must be strings.")
        if (
            not before.strip()
            or not after.strip()
            or before == after
            or "\n" in before
            or "\n" in after
            or text.count(before) != 1
        ):
            raise ValueError(
                "Each edit must replace one unique non-empty text span within a paragraph."
            )
        if source_id not in by_id or not quote.strip() or quote not in by_id[source_id]:
            raise ValueError("Edit requires an exact source citation.")
        if protected_edit(text, before):
            raise ValueError(
                "JD tailoring cannot change detected name/contact lines. Edit identity details manually in the sandbox copy."
            )
        if new_numeric_claim(before, after, quote):
            raise ValueError(
                "Replacement introduces numerical claims absent from the original span and cited evidence."
            )
        start = text.index(before)
        end = start + len(before)
        if any(start < b and end > a for a, b in spans):
            raise ValueError("Edits overlap; regenerate simpler suggestions.")
        spans.append((start, end))
        validated.append({"before": before, "after": after, "source_id": source_id, "quote": quote})
    return validated


def suggest(jobs, arguments, model=generate_json):
    """Propose cited edits using accepted facts without changing the remote draft.

    Args:
        jobs: Jobs coordinator providing workflow state and the Google adapter.
        arguments: Application ID returned by /save_jd.
        model: Injectable structured-output model callable; defaults to the local provider.

    Returns:
        JSON proposals, exact edit-batch ID and explicit-review guidance.

    Raises:
        ValueError: Accepted evidence or a completed draft is missing, edits are pending, or model proposals fail validation.
    """
    app_id, app = jobs.application(arguments)
    from assistant.comparison_review import generation_sources

    sources = generation_sources(app)
    state = app.get("draft", {})
    if not state.get("ready"):
        raise ValueError("Run /draft_resume first.")
    if app.get("pending_edits"):
        raise ValueError(
            "Resolve the pending /apply_edits command before generating new suggestions."
        )
    doc = jobs.google.document(state["doc_id"])
    text = body_text(find_tab(doc, state["tab_id"])["documentTab"]["body"])
    output = model(
        'Return {"edits":[{"before":"unique exact resume text","after":"replacement within same paragraph",'
        '"source_id":"supplied source ID","quote":"exact source evidence"}]}. Maximum 20 edits. '
        "Use only supplied facts. No invented metrics, employers, skills, years, or commercial GenAI experience. "
        "Improve relevance to the JD. Do not alter identity/contact lines or introduce numerical claims absent from the original span and cited quotation. Preserve personal portfolio versus employment distinction. before and after must contain no newline characters and must differ. Return edits:[] when there is no useful supported change.",
        {"jd": app["input"]["jd"], "resume": text, "sources": sources},
        schema=edits_for(text, sources),
    )
    edits = validate_edits(output, text, sources)
    app["suggestions"] = {
        "base_text": text,
        "edits": edits,
        "comparison_id": app["comparison"]["comparison_id"],
    }
    app["suggestions"]["edit_batch_id"] = edit_batch_id(app["suggestions"])
    app["reviewed"] = False
    jobs.save(app_id, app)
    return json.dumps(
        {
            "edit_batch_id": app["suggestions"]["edit_batch_id"],
            "edits": [{"edit_id": i, **e} for i, e in enumerate(edits)],
            "review_required": "Review every replacement and citation. Exact quotes do not prove semantic support. /apply_edits requires explicit reviewed:true.",
        },
        indent=2,
    )


def edit_batch_id(suggestions):
    """Bind an edit selection to the exact proposal text and comparison snapshot.

    Args:
        suggestions: Saved edit proposal batch and its comparison binding.

    Returns:
        Stable digest binding this exact batch to its snapshot.
    """
    return digest({key: suggestions.get(key) for key in ("base_text", "edits", "comparison_id")})[
        :16
    ]


def replacement_requests(text, edits, tab_id):
    """Build reverse-ordered UTF-16 edit requests and expected final text.

    Args:
        text: Text to inspect or transform without changing the original value.
        edits: Validated selected edits containing unique before/after spans.
        tab_id: Stable Google document tab identifier.

    Returns:
        Pair of expected final text and reverse-ordered API requests.
    """
    changes = sorted([(text.index(e["before"]), e) for e in edits], reverse=True)
    expected = text
    requests = []
    for start, edit in changes:
        index = 1 + utf16(text[:start])
        requests.extend(
            [
                {
                    "deleteContentRange": {
                        "range": {
                            "tabId": tab_id,
                            "startIndex": index,
                            "endIndex": index + utf16(edit["before"]),
                        }
                    }
                },
                {
                    "insertText": {
                        "location": {"tabId": tab_id, "index": index},
                        "text": edit["after"],
                    }
                },
            ]
        )
        expected = expected[:start] + edit["after"] + expected[start + len(edit["before"]) :]
    return expected, requests


def apply(jobs, arguments):
    """Apply only explicitly reviewed current-batch edits with guarded retry readback.

    Args:
        jobs: Jobs coordinator providing workflow state and the Google adapter.
        arguments: JSON object payload matching this command's fields in docs/COMMANDS.md.

    Returns:
        Verified draft URL and renewed content/layout approval guidance.

    Raises:
        ValueError: Review, exact batch binding, selected IDs, cached facts or revision/readback reconciliation fails.
    """
    data = json_input(arguments)
    if data.get("reviewed") is not True:
        raise ValueError("Review the suggestions and supply reviewed:true to apply selected edits.")
    app_id, app = jobs.application(data.get("application_id", ""))
    from assistant.comparison_review import reviewed_sources

    reviewed_sources(app)
    state, suggestions = app.get("draft", {}), app.get("suggestions")
    if suggestions and suggestions.get("comparison_id") != app["comparison"]["comparison_id"]:
        raise ValueError(
            "Suggestions predate this reviewed comparison. Generate fresh suggestions."
        )
    if suggestions and (
        not isinstance(data.get("edit_batch_id"), str)
        or data["edit_batch_id"] != suggestions.get("edit_batch_id")
        or data["edit_batch_id"] != edit_batch_id(suggestions)
    ):
        raise ValueError(
            "Supply the current edit_batch_id from /suggest_edits; stale or changed proposals cannot be applied."
        )
    ids = data.get("edit_ids")
    if (
        not suggestions
        or not isinstance(ids, list)
        or not ids
        or any(type(i) is not int or i < 0 or i >= len(suggestions["edits"]) for i in ids)
        or len(set(ids)) != len(ids)
    ):
        raise ValueError("Provide valid unique edit_ids from /suggest_edits.")
    signature = digest(sorted(ids))
    if app.get("applied_signature") == signature and app.get("applied_suggestions") == digest(
        suggestions
    ):
        return "These selected edits were already applied. " + state["url"]
    selected = [suggestions["edits"][i] for i in ids]
    from assistant.comparison_review import generation_sources

    validate_edits({"edits": selected}, suggestions["base_text"], generation_sources(app))
    expected, requests = replacement_requests(suggestions["base_text"], selected, state["tab_id"])
    pending = {"signature": signature, "before": suggestions["base_text"], "after": expected}
    if app.get("pending_edits") and app["pending_edits"] != pending:
        raise ValueError("A different edit batch is pending; rerun its original command first.")
    app["pending_edits"] = pending
    app["reviewed"] = False
    jobs.save(app_id, app)
    doc_id, tab_id = state["doc_id"], state["tab_id"]
    doc = jobs.google.document(doc_id)
    actual = body_text(find_tab(doc, tab_id)["documentTab"]["body"])
    before_tabs = unchanged_tabs(doc, tab_id)
    if actual == suggestions["base_text"]:
        jobs.google.batch(doc_id, requests, doc["revisionId"])
    elif actual != expected:
        raise ValueError("Draft changed after suggestions. Refusing to overwrite external edits.")
    checked = jobs.google.document(doc_id)
    if (
        body_text(find_tab(checked, tab_id)["documentTab"]["body"]) != expected
        or unchanged_tabs(checked, tab_id) != before_tabs
    ):
        raise ValueError("Edit verification failed; inspect the draft manually.")
    state["text"] = expected
    app.update(
        {
            "pending_edits": None,
            "applied_signature": signature,
            "applied_suggestions": digest(suggestions),
        }
    )
    jobs.save(app_id, app)
    return (
        "Selected edits applied and content verified. Inspect layout, then /approve_resume APPLICATION_ID.\n"
        + state["url"]
    )


def approve(jobs, arguments):
    """Record human review against the current draft text hash.

    Args:
        jobs: Jobs coordinator providing workflow state and the Google adapter.
        arguments: Application ID returned by /save_jd.

    Returns:
        Confirmation binding human review to the current draft text.

    Raises:
        ValueError: Review is missing or the draft is incomplete or has pending edits.
    """
    app_id, app = jobs.application(arguments)
    from assistant.comparison_review import reviewed_sources

    reviewed_sources(app)
    state = app.get("draft", {})
    if not state.get("ready") or app.get("pending_edits"):
        raise ValueError("A completed draft without pending writes is required.")
    text = body_text(
        find_tab(jobs.google.document(state["doc_id"]), state["tab_id"])["documentTab"]["body"]
    )
    app.update({"reviewed": True, "approved_text_hash": digest(text)})
    jobs.save(app_id, app)
    return "Your review of content and layout has been recorded. " + state["url"]


def reset(jobs, arguments):
    """Preserve the remote draft while explicitly abandoning local edit state.

    Args:
        jobs: Jobs coordinator providing workflow state and the Google adapter.
        arguments: JSON object payload matching this command's fields in docs/COMMANDS.md.

    Returns:
        Confirmation that the remote draft was preserved and local edit state cleared.

    Raises:
        ValueError: The caller has not confirmed keeping the current text or no completed draft exists.
    """
    data = json_input(arguments)
    if data.get("keep_current") is not True:
        raise ValueError(
            "Inspect the current Google draft and supply keep_current:true to discard local edit state."
        )
    app_id, app = jobs.application(data.get("application_id", ""))
    state = app.get("draft", {})
    if not state.get("ready"):
        raise ValueError("A completed draft is required before resetting edit state.")
    doc = jobs.google.document(state["doc_id"])
    text = body_text(find_tab(doc, state["tab_id"])["documentTab"]["body"])
    if app.get("pending_edits"):
        app.setdefault("abandoned_edit_batches", []).append(app["pending_edits"])
    state["text"] = text
    app.update({"pending_edits": None, "reviewed": False})
    for key in ("suggestions", "applied_signature", "applied_suggestions", "approved_text_hash"):
        app.pop(key, None)
    jobs.save(app_id, app)
    return (
        "Current Google draft preserved. Local edit state cleared; generate new suggestions or review and approve again. "
        + state["url"]
    )
