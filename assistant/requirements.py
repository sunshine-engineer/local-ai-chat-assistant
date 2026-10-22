"""Manual JD scope review: candidate enumeration never delegates coverage to a model.

File: assistant/requirements.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import json

from assistant.evidence import digest, validate_requirements
from assistant.schemas import quote_candidates
from assistant.state import json_input


def candidates(app):
    """Enumerate all bounded JD sentence and line candidates without model selection.

    Args:
        app: Saved application record, including its input and comparison snapshot.

    Returns:
        Validated requirement strings in their original order.

    Raises:
        ValueError: The JD produces zero or more than 200 sentence/line candidates.
    """
    result = quote_candidates(app["input"]["jd"])
    if not result or len(result) > 200:
        raise ValueError("JD must contain 1–200 sentence/line candidates; use a shorter JD.")
    return result


def show(jobs, arguments):
    """Display candidate IDs and current scope-review status.

    Args:
        jobs: Jobs coordinator providing workflow state and the Google adapter.
        arguments: Application ID returned by /save_jd.

    Returns:
        JSON candidate IDs, literal text and current review status.

    Raises:
        ValueError: The application or JD candidate scope is invalid.
    """
    app_id, app = jobs.application(arguments)
    return json.dumps(
        {
            "application_id": app_id,
            "candidates": [
                {"candidate_id": i, "text": text} for i, text in enumerate(candidates(app))
            ],
            "reviewed": app.get("requirements_review", {}).get("jd_hash")
            == digest(app["input"]["jd"]),
            "instructions": "Select all relevant duties, qualifications and required/desirable skills, including gaps. Exclude marketing and hiring instructions. Run /review_requirements with application_id, candidate_ids and reviewed:true. No model selects or removes candidates.",
        },
        indent=2,
    )


def review(jobs, arguments):
    """Persist explicitly selected literal JD scope and invalidate old comparisons.

    Args:
        jobs: Jobs coordinator providing workflow state and the Google adapter.
        arguments: JSON object payload matching this command's fields in docs/COMMANDS.md.

    Returns:
        JSON selected literal requirements and the next comparison command.

    Raises:
        ValueError: Scope is frozen or the payload does not select 1–30 unique valid candidate IDs with explicit review.
    """
    data = json_input(arguments)
    if (
        set(data) != {"application_id", "candidate_ids", "reviewed"}
        or data.get("reviewed") is not True
    ):
        raise ValueError(
            "Provide application_id, candidate_ids and reviewed:true after reviewing the JD."
        )
    app_id, app = jobs.application(data["application_id"])
    if app.get("draft") or app.get("cover_letter_draft"):
        raise ValueError(
            "Requirements are fixed once a resume or letter draft exists. Use a new application variant."
        )
    rows = candidates(app)
    ids = data["candidate_ids"]
    if (
        not isinstance(ids, list)
        or not 1 <= len(ids) <= 30
        or any(type(i) is not int or i < 0 or i >= len(rows) for i in ids)
        or len(set(ids)) != len(ids)
    ):
        raise ValueError("Select 1–30 unique candidate_ids from /requirements.")
    selected = [rows[i] for i in sorted(ids)]
    app["requirements_review"] = {
        "jd_hash": digest(app["input"]["jd"]),
        "candidate_ids": sorted(ids),
        "requirements": selected,
    }
    # Previous comparisons are invalid after changing their scope.
    app.pop("comparison", None)
    app.pop("source_snapshot", None)
    app["reviewed"] = False
    jobs.save(app_id, app)
    return json.dumps(
        {
            "requirements": selected,
            "next": "/compare_resume " + app_id,
            "warning": "Counts cover only the selected requirements; review the full JD for omissions.",
        },
        indent=2,
    )


def selected(app):
    """Require reviewed scope to match the current JD before comparison.

    Args:
        app: Saved application record, including its input and comparison snapshot.

    Returns:
        Validated requirement strings in their original order.

    Raises:
        ValueError: The JD has changed, review is absent, or selected quotations fail literal-scope checks.
    """
    review = app.get("requirements_review")
    if not review or review.get("jd_hash") != digest(app["input"]["jd"]):
        raise ValueError("Review JD scope first with /requirements and /review_requirements.")
    return validate_requirements({"requirements": review["requirements"]}, app["input"]["jd"])
