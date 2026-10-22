"""Provisional model judgments and explicit, snapshot-bound reviewer decisions.

File: assistant/comparison_review.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import json
import re
from datetime import datetime, timezone

from assistant.evidence import digest, validate_matches
from assistant.state import json_input

STATUSES = ("supported", "partial", "gap")
STOP = set(
    "a an the and or with of to in for on as is are be that this it by from required desirable experience strong skills work working ability knowledge".split()
)
TECH = (
    "python",
    "sql",
    "fastapi",
    "docker",
    "kubernetes",
    "langgraph",
    "langchain",
    "rag",
    "mongodb",
    "redis",
    "pgvector",
    "postgresql",
    "aws",
    "gcp",
    "airflow",
    "spark",
    "kafka",
)


def flags(requirement, quote, text, kind):
    """Identify narrow relevance, context and qualifier warning signals.

    Args:
        requirement: Selected literal JD requirement.
        quote: Literal supporting quotation to inspect.
        text: Text to inspect or transform without changing the original value.
        kind: Evidence category, such as resume or independent project evidence.

    Returns:
        List of heuristic warning identifiers; absence does not certify support.
    """
    if not quote:
        return []
    result = []

    def words(value):
        """Tokenize specific source terms after removing common words.

        Args:
            value: Value to validate, compare or persist.

        Returns:
            Set of normalized specific terms excluding common stop words.
        """
        return set(re.findall(r"[a-z0-9+#]+", value.lower())) - STOP

    if not words(requirement).intersection(words(quote)):
        result.append("no_specific_term_overlap")
    mentioned = [term for term in TECH if re.search(r"\b" + term + r"\b", requirement, re.I)]
    if any(not re.search(r"\b" + term + r"\b", quote, re.I) for term in mentioned):
        result.append("explicit_terms_missing")
    position = text.find(quote)
    preceding = text[:position] if position >= 0 else ""
    headings = [
        line.strip().lstrip("#").strip().lower()
        for line in preceding.splitlines()
        if line.lstrip().startswith("#")
        or line.strip().lower() in ("next steps", "future work", "roadmap")
    ]
    if re.search(
        r"\b(plan(?:ned)?|future|intend|will|would|without|not|never|no|non[- ]production)\b",
        quote,
        re.I,
    ) or (headings and re.search(r"next|future|improve|roadmap|plan", headings[-1])):
        result.append("future_or_negated_context")
    qualifier = re.findall(r"\b(commercial|production|deployed|deployment)\b", requirement.lower())
    if qualifier and (
        any(not re.search(r"\b" + word + r"\b", quote, re.I) for word in qualifier)
        or (kind == "evidence" and re.search(r"\b(commercial|production)\b", requirement, re.I))
    ):
        result.append("qualifier_not_established")
    return result


def proposals(matches, source):
    """Keep model matches provisional and attach inspection flags.

    Args:
        matches: Validated per-requirement model matches.
        source: Frozen source record or Google tab structure required by this operation.

    Returns:
        Provisional rows with requirement IDs, original verdicts and heuristic flags.
    """
    return [
        {
            "requirement_id": i,
            "requirement": row["requirement"],
            "proposed_status": row["status"],
            "status": "needs_review",
            "quote": row["quote"],
            "flags": flags(row["requirement"], row["quote"], source["text"], source["kind"]),
        }
        for i, row in enumerate(matches)
    ]


def show(jobs, arguments):
    """Expose the frozen comparison and an incomplete human-review template.

    Args:
        jobs: Jobs coordinator providing workflow state and the Google adapter.
        arguments: Application ID returned by /save_jd.

    Returns:
        JSON containing the frozen comparison, full sources and incomplete review template.

    Raises:
        ValueError: The application is unknown or has no comparison.
    """
    app_id, app = jobs.application(arguments)
    if not app.get("comparison"):
        raise ValueError("Run /compare_resume first.")
    comparison = app["comparison"]
    return json.dumps(
        {
            "comparison": comparison,
            "snapshot_sources": app.get("source_snapshot", []),
            "review_template": {
                "application_id": app_id,
                "comparison_id": comparison.get("comparison_id"),
                "source_id": "CHOOSE_SOURCE_ID",
                "reviewed": True,
                "decisions": [
                    {
                        "requirement_id": i,
                        "status": "CHOOSE supported|partial|gap",
                        "quote": "",
                        "note": "",
                        "acknowledged_flags": [],
                    }
                    for i in range(len(comparison["requirements"]))
                ],
            },
            "instructions": "Fill every decision after checking the source. Do not copy proposal verdicts without review. Review projects needed for generation before drafting. Legacy comparisons without review_version=1 need a new application variant.",
        },
        indent=2,
    )


def reviewed_sources(app):
    """Require current comparison review and select eligible evidence sources.

    Args:
        app: Saved application record, including its input and comparison snapshot.

    Returns:
        Selected reviewed resume plus eligible reviewed project records.

    Raises:
        ValueError: Review is missing, legacy, stale, or not bound to the selected source snapshot.
    """
    comparison = app.get("comparison", {})
    selected = comparison.get("recommended_source_id")
    if comparison.get("review_version") != 1 or not selected:
        raise ValueError(
            "Review the proposed comparison using /review_comparison before drafting, edits, approval or tracking. Legacy draft artifacts are preserved; start a new application variant if its comparison predates this gate."
        )
    if comparison.get("source_digest") != digest(app.get("source_snapshot")) or comparison.get(
        "jd_digest"
    ) != digest(app["input"]["jd"]):
        raise ValueError(
            "Reviewed comparison source/JD snapshot changed. Recompare and review before continuing."
        )
    reviews = comparison.get("reviews", {})
    if selected not in reviews or reviews[selected].get("comparison_id") != comparison.get(
        "comparison_id"
    ):
        raise ValueError("Selected resume comparison has not been reviewed for this snapshot.")
    ids = {selected} | {
        key
        for key, value in reviews.items()
        if value.get("comparison_id") == comparison["comparison_id"]
    }
    # Other resumes cannot become evidence for the selected resume's claims.
    return [
        s
        for s in app["source_snapshot"]
        if s["id"] == selected or (s["kind"] == "evidence" and s["id"] in ids)
    ]


def generation_sources(app):
    """Restrict generation facts to accepted non-gap quotations.

    Args:
        app: Saved application record, including its input and comparison snapshot.

    Returns:
        Source records reduced to accepted non-gap quotations.

    Raises:
        ValueError: Review is stale or no accepted non-gap quotation is available.
    """
    result = []
    sources = reviewed_sources(app)
    comparison = app["comparison"]
    groups = comparison["resumes"] + comparison["project_evidence"]
    for source in sources:
        entry = next(row for row in groups if row["source_id"] == source["id"])
        quotes = list(
            dict.fromkeys(
                row["quote"] for row in entry["reviewed_matches"] if row["status"] != "gap"
            )
        )
        if quotes:
            result.append({**source, "text": "\n".join(quotes)})
    if not result:
        raise ValueError(
            "No reviewed supporting quotations are available for generation. Copy/review the resume manually or review additional evidence first."
        )
    return result


def review(jobs, arguments):
    """Record explicit decisions for every selected requirement in one source.

    Args:
        jobs: Jobs coordinator providing workflow state and the Google adapter.
        arguments: JSON object payload matching this command's fields in docs/COMMANDS.md.

    Returns:
        JSON describing the recorded source decisions and explicitly selected resume.

    Raises:
        ValueError: The review payload, selected source, quotations, flag acknowledgements or snapshot binding is invalid, or drafting has frozen decisions.
    """
    data = json_input(arguments)
    if (
        set(data) != {"application_id", "comparison_id", "source_id", "decisions", "reviewed"}
        or data["reviewed"] is not True
    ):
        raise ValueError(
            "Provide application_id, comparison_id, source_id, decisions and reviewed:true."
        )
    app_id, app = jobs.application(data["application_id"])
    comparison = app.get("comparison", {})
    if comparison.get("review_version") != 1 or data["comparison_id"] != comparison.get(
        "comparison_id"
    ):
        raise ValueError(
            "Comparison snapshot changed or predates review controls. Inspect /show_comparison; use a new application variant for a legacy draft."
        )
    if comparison.get("source_digest") != digest(app.get("source_snapshot")) or comparison.get(
        "jd_digest"
    ) != digest(app["input"]["jd"]):
        raise ValueError("Comparison source/JD snapshot changed. Recompare first.")
    if app.get("draft") or app.get("cover_letter_draft"):
        raise ValueError("Comparison decisions are frozen after a resume or letter draft exists.")
    source = next((s for s in app["source_snapshot"] if s["id"] == data["source_id"]), None)
    if not source:
        raise ValueError("Select a source_id from this comparison snapshot.")
    decisions = data["decisions"]
    requirements = comparison["requirements"]
    if not isinstance(decisions, list) or len(decisions) != len(requirements):
        raise ValueError("Provide one explicit decision for every selected requirement.")
    checked, notes = {}, []
    for row in decisions:
        if not isinstance(row, dict) or set(row) - {
            "requirement_id",
            "status",
            "quote",
            "note",
            "acknowledged_flags",
        }:
            raise ValueError("Invalid review decision fields.")
        index = row.get("requirement_id")
        if type(index) is not int or not 0 <= index < len(requirements) or index in checked:
            raise ValueError("Requirement IDs must be valid and unique.")
        note = row.get("note")
        if not isinstance(note, str) or not note.strip():
            raise ValueError("Each decision needs a reviewer note explaining its evidence or gap.")
        status, quote = row.get("status"), row.get("quote")
        validate_matches(
            {"matches": [{"requirement": requirements[index], "status": status, "quote": quote}]},
            [requirements[index]],
            source["text"],
        )
        issues = flags(requirements[index], quote, source["text"], source["kind"])
        ack = row.get("acknowledged_flags", [])
        if (
            not isinstance(ack, list)
            or any(not isinstance(value, str) for value in ack)
            or sorted(ack) != sorted(issues)
        ):
            raise ValueError(
                "Correct the quotation/verdict or explicitly acknowledge every current flag; include a reviewer note."
            )
        if (
            source["kind"] == "evidence"
            and status == "supported"
            and re.search(r"\b(commercial|production)\b", requirements[index], re.I)
        ):
            raise ValueError(
                "Project documentation alone cannot establish a fully supported commercial/production requirement."
            )
        checked[index] = {
            "requirement_id": index,
            "requirement": requirements[index],
            "status": status,
            "quote": quote,
            "note": note.strip(),
            "flags": issues,
            "acknowledged_flags": ack,
        }
        notes.append({"requirement_id": index, "note": note.strip()})
    group = comparison["resumes"] if source["kind"] == "resume" else comparison["project_evidence"]
    target = next(r for r in group if r["source_id"] == source["id"])
    target["reviewed_matches"] = [checked[i] for i in range(len(requirements))]
    target["counts"] = {
        status: sum(row["status"] == status for row in checked.values()) for status in STATUSES
    }
    target["review_state"] = "reviewed"
    comparison.setdefault("reviews", {})[source["id"]] = {
        "comparison_id": comparison["comparison_id"],
        "notes": notes,
    }
    comparison.setdefault("review_history", []).append(
        {
            "source_id": source["id"],
            "comparison_id": comparison["comparison_id"],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "decisions": target["reviewed_matches"],
        }
    )
    if source["kind"] == "resume":
        comparison["recommended_source_id"] = source["id"]
    app["reviewed"] = False
    app.pop("approved_text_hash", None)
    jobs.save(app_id, app)
    return json.dumps(
        {
            "source_id": source["id"],
            "counts": target["counts"],
            "selected_resume": comparison.get("recommended_source_id"),
            "next": "Review any project sources needed for generation before drafting. Then /draft_resume APPLICATION_ID.",
            "warning": "These are reviewer decisions, not independently proven facts or an ATS score.",
        },
        indent=2,
    )
