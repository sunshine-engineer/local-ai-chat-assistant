"""Read-only comparison inspection; decisions still go through explicit commands.

File: assistant/review_ui.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import json

import streamlit as st

from assistant.runtime import build_registry


def render_comparison_review():
    """Render read-only proposal, source and reviewer-decision inspection controls."""
    with st.expander("Inspect comparison evidence", expanded=False):
        st.caption(
            "Read-only inspection. Use /review_comparison to record your decisions; this panel never approves evidence."
        )
        application_id = st.text_input("Application ID", key="comparison_application_id").strip()
        if st.button("Load comparison", key="load_comparison"):
            st.session_state.pop("comparison_inspection", None)
            # Application IDs are single tokens, just like the command interface.
            if not application_id or len(application_id.split()) != 1:
                st.error("Enter one application ID from /save_jd.")
            else:
                registry = build_registry()
                result = registry.execute("/show_comparison " + application_id)
                if registry.last_error:
                    st.error(result)
                else:
                    st.session_state.comparison_inspection = (application_id, json.loads(result))
        loaded = st.session_state.get("comparison_inspection")
        if not loaded or loaded[0] != application_id:
            return
        data = loaded[1]
        comparison = data["comparison"]
        st.caption(
            "Loaded snapshot: "
            + str(comparison.get("comparison_id", "legacy"))
            + ". Load again after commands to refresh this view. Flags are incomplete heuristics; missing flags do not prove support."
        )
        selected = comparison.get("recommended_source_id")
        st.text("Reviewer-selected resume: " + (selected or "None — review required"))
        groups = comparison["resumes"] + comparison["project_evidence"]
        sources = {source["id"]: source for source in data["snapshot_sources"]}
        options = [row["source_id"] for row in groups]
        source_id = st.selectbox(
            "Evidence source",
            options,
            format_func=lambda value: (
                sources[value].get("title", value) + " [" + sources[value]["kind"] + "] — " + value
            ),
        )
        entry = next(row for row in groups if row["source_id"] == source_id)
        st.text("Source reference: " + sources[source_id].get("url", "Unavailable"))
        st.text(
            "Review state: "
            + entry.get("review_state", "legacy — new application variant required")
        )
        counts = entry.get("counts")
        st.text(
            "Accepted reviewer counts: "
            + (json.dumps(counts) if counts is not None else "Not established")
        )
        if entry.get("proposed_counts") is not None:
            st.text("Unreviewed model counts: " + json.dumps(entry["proposed_counts"]))
        requirement_id = st.selectbox(
            "Requirement ID", list(range(len(comparison["requirements"])))
        )
        st.text(comparison["requirements"][requirement_id])
        proposal = entry["matches"][requirement_id]
        reviewed = next(
            (
                row
                for row in entry.get("reviewed_matches", [])
                if row["requirement_id"] == requirement_id
            ),
            None,
        )
        left, right = st.columns(2)
        with left:
            st.write("Model proposal — requires review")
            st.text("Proposed verdict: " + proposal.get("proposed_status", proposal["status"]))
            st.code(proposal["quote"] or "(No supporting quotation)", language=None)
            st.text("Proposal flags: " + ", ".join(proposal.get("flags", [])))
        with right:
            st.write("Recorded reviewer decision")
            if reviewed:
                st.text("Verdict: " + reviewed["status"])
                st.code(reviewed["quote"] or "(Gap — no supporting quotation)", language=None)
                st.text("Review note: " + reviewed["note"])
                st.text("Acknowledged flags: " + ", ".join(reviewed.get("acknowledged_flags", [])))
            else:
                st.text("No decision recorded for this requirement.")
        with st.expander("Full frozen source — inspect surrounding context"):
            st.code(sources[source_id]["text"], language=None)
        if comparison.get("review_version") != 1:
            st.warning(
                "This legacy comparison cannot authorize new work. Use a new application variant and compare again."
            )
            return
        template = {**data["review_template"], "source_id": source_id}
        st.caption(
            "The template intentionally leaves every verdict, quotation and note incomplete. "
            "Inspect all requirements, complete the JSON, then submit /review_comparison. "
            "Review needed projects before creating a resume or letter draft."
        )
        st.code(json.dumps(template, indent=2), language="json")
