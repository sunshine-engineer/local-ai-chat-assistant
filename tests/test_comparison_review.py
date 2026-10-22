"""Regression coverage for comparison review.

File: tests/test_comparison_review.py
Maintainer: sunshine-engineer
Modified: 2026-10-23
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from assistant import comparison_review, package, requirements, resumes, tracking
from assistant.evidence import compare, digest
from assistant.jobs import Jobs
from assistant.state import Store


class ComparisonReviewTest(unittest.TestCase):
    """Exercise comparison review contracts using isolated fixtures."""

    def setUp(self):
        """Create isolated temporary state and explicit provider fixtures for each test."""
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cloud = Mock()
        self.jobs = Jobs(Store(directory.name), self.cloud)
        self.source = {
            "id": "resume",
            "kind": "resume",
            "title": "Resume",
            "text": "Avery Example\nBuilt Python ETL.",
            "doc_id": "copy",
            "tab_id": "source",
            "url": "synthetic://resume",
        }
        self.project = {
            "id": "project",
            "kind": "evidence",
            "title": "Project",
            "text": "Independent Python ETL prototype.",
            "url": "synthetic://project",
        }
        self.jobs.save("app", {"input": {"jd": "Required: Python ETL."}})
        requirements.review(
            self.jobs, '{"application_id":"app","candidate_ids":[0],"reviewed":true}'
        )
        self.jobs.store.put(
            "catalogue",
            {"sources": [self.source, self.project], "digest": digest([self.source, self.project])},
        )
        self.model = lambda instruction, data, **kwargs: {
            "matches": [
                {
                    "requirement": data["requirements"][0],
                    "status": "supported",
                    "quote": data["source"].splitlines()[0],
                }
            ]
        }
        compare(self.jobs, "app", self.model)

    def payload(self, **changes):
        """Build the exact review payload for the current synthetic comparison.

        Args:
            changes: Explicit field overrides for the test review payload.

        Returns:
            Fixture value or structured response consumed by the regression.
        """
        c = self.jobs.application("app")[1]["comparison"]
        return json.dumps(
            {
                "application_id": "app",
                "comparison_id": c["comparison_id"],
                "source_id": "resume",
                "decisions": [
                    {
                        "requirement_id": 0,
                        "status": "supported",
                        "quote": "Built Python ETL.",
                        "note": "The resume explicitly records the required Python ETL work.",
                    }
                ],
                "reviewed": True,
                **changes,
            }
        )

    def test_versioned_failure_fixtures_always_remain_proposals(self):
        """Verify versioned failure fixtures always remain proposals."""
        rows = json.loads(
            (Path(__file__).resolve().parents[1] / "assistant/comparison_cases.json").read_text()
        )
        for row in rows:
            with self.subTest(case=row["id"]):
                source = {"kind": row["kind"], "text": row["source"]}
                actual = comparison_review.proposals(
                    [
                        {
                            "requirement": row["requirement"],
                            "status": row["proposed_status"],
                            "quote": row["quote"],
                        }
                    ],
                    source,
                )[0]
                self.assertEqual(actual["status"], "needs_review")
                self.assertEqual(actual["flags"], row["flags"])

    def test_bad_name_citation_has_no_accepted_counts_or_selected_resume(self):
        """Verify bad name citation has no accepted counts or selected resume."""
        c = self.jobs.application("app")[1]["comparison"]
        self.assertIsNone(c["recommended_source_id"])
        self.assertIsNone(c["resumes"][0]["counts"])
        self.assertIn("no_specific_term_overlap", c["resumes"][0]["matches"][0]["flags"])
        self.assertEqual(c["resumes"][0]["matches"][0]["status"], "needs_review")

    def test_unreviewed_proposal_cannot_cause_remote_writes(self):
        """Verify unreviewed proposal cannot cause remote writes."""
        for action in (resumes.draft, resumes.suggest, resumes.approve, package.cover_letter):
            with (
                self.subTest(action=action.__name__),
                self.assertRaisesRegex(ValueError, "Review the proposed comparison"),
            ):
                action(self.jobs, "app")
        with self.assertRaises(ValueError):
            tracking.track(self.jobs, "app --write")
        self.cloud.batch.assert_not_called()
        self.cloud.create_document.assert_not_called()
        self.assertIn("Review comparison evidence", package.summary(self.jobs, "app"))

    def test_correction_selects_resume_and_excludes_unreviewed_projects(self):
        """Verify correction selects resume and excludes unreviewed projects."""
        comparison_review.review(self.jobs, self.payload())
        app = self.jobs.application("app")[1]
        self.assertEqual([s["id"] for s in comparison_review.reviewed_sources(app)], ["resume"])
        self.assertEqual(app["comparison"]["resumes"][0]["counts"]["supported"], 1)
        self.assertEqual(app["comparison"]["resumes"][0]["matches"][0]["quote"], "Avery Example")
        self.assertEqual(
            app["comparison"]["resumes"][0]["reviewed_matches"][0]["quote"], "Built Python ETL."
        )
        self.assertFalse(app["reviewed"])
        facts = comparison_review.generation_sources(app)
        self.assertEqual(facts[0]["text"], "Built Python ETL.")
        self.assertNotIn("Avery Example", facts[0]["text"])
        self.assertEqual(len(app["comparison"]["review_history"]), 1)

    def test_stale_incomplete_and_blanket_review_are_rejected(self):
        """Verify stale incomplete and blanket review are rejected."""
        for payload in (
            self.payload(comparison_id="stale"),
            self.payload(decisions=[]),
            self.payload(reviewed=False),
            self.payload(
                decisions=[
                    {
                        "requirement_id": 0,
                        "status": "supported",
                        "quote": "Built Python ETL.",
                        "note": "",
                    }
                ]
            ),
        ):
            with self.assertRaises(ValueError):
                comparison_review.review(self.jobs, payload)

    def test_flag_override_is_explicit_and_recorded(self):
        """Verify flag override is explicit and recorded."""
        decision = {
            "requirement_id": 0,
            "status": "partial",
            "quote": "Avery Example",
            "note": "Test explicit override; this is not a valid skill claim.",
        }
        with self.assertRaisesRegex(ValueError, "acknowledge"):
            comparison_review.review(self.jobs, self.payload(decisions=[decision]))
        decision["acknowledged_flags"] = ["no_specific_term_overlap", "explicit_terms_missing"]
        comparison_review.review(self.jobs, self.payload(decisions=[decision]))
        reviewed = self.jobs.application("app")[1]["comparison"]["resumes"][0]["reviewed_matches"][
            0
        ]
        self.assertEqual(reviewed["acknowledged_flags"], decision["acknowledged_flags"])

    def test_changed_snapshot_and_post_draft_review_stop(self):
        """Verify changed snapshot and post draft review stop."""
        app = self.jobs.application("app")[1]
        app["source_snapshot"][0]["text"] += " Changed"
        self.jobs.save("app", app)
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            comparison_review.review(self.jobs, self.payload())
        compare(self.jobs, "app", self.model)
        comparison_review.review(self.jobs, self.payload())
        app = self.jobs.application("app")[1]
        app["draft"] = {"ready": True}
        self.jobs.save("app", app)
        with self.assertRaisesRegex(ValueError, "frozen"):
            comparison_review.review(self.jobs, self.payload())

    def test_project_cannot_fully_establish_commercial_employment(self):
        """Verify project cannot fully establish commercial employment."""
        app = self.jobs.application("app")[1]
        app["input"]["jd"] = "Commercial production Python."
        app.pop("comparison")
        self.jobs.save("app", app)
        requirements.review(
            self.jobs, '{"application_id":"app","candidate_ids":[0],"reviewed":true}'
        )
        compare(self.jobs, "app", self.model)
        decision = {
            "requirement_id": 0,
            "status": "supported",
            "quote": self.project["text"],
            "note": "Test project-only employment claim.",
            "acknowledged_flags": ["qualifier_not_established"],
        }
        with self.assertRaisesRegex(ValueError, "Project documentation alone"):
            comparison_review.review(
                self.jobs, self.payload(source_id="project", decisions=[decision])
            )

    def test_all_gap_decisions_do_not_generate_unsupported_claims(self):
        """Verify all gap decisions do not generate unsupported claims."""
        decision = {
            "requirement_id": 0,
            "status": "gap",
            "quote": "",
            "note": "No accepted supporting fact selected.",
        }
        comparison_review.review(self.jobs, self.payload(decisions=[decision]))
        model = Mock()
        with self.assertRaisesRegex(ValueError, "No reviewed supporting quotations"):
            package.cover_letter(self.jobs, "app", model)
        model.assert_not_called()
        self.cloud.create_document.assert_not_called()

    def test_recompare_invalidates_previous_human_decisions(self):
        """Verify recompare invalidates previous human decisions."""
        old = self.payload()
        comparison_review.review(self.jobs, old)

        def model(instruction, data, **kwargs):
            """Return the synthetic model response needed by this regression.

            Args:
                instruction: Task instructions, kept separate from untrusted source material.
                data: Structured source data supplied to the model or test callback.
                kwargs: Additional provider or test-double keyword arguments.

            Returns:
                Fixture value or structured response consumed by the regression.
            """
            return {
                "matches": [{"requirement": data["requirements"][0], "status": "gap", "quote": ""}]
            }

        compare(self.jobs, "app", model)
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            comparison_review.review(self.jobs, old)
        with self.assertRaises(ValueError):
            comparison_review.reviewed_sources(self.jobs.application("app")[1])

    def test_show_provides_incomplete_template_that_cannot_be_blanket_accepted(self):
        """Verify show provides incomplete template that cannot be blanket accepted."""
        data = json.loads(comparison_review.show(self.jobs, "app"))
        with self.assertRaises(ValueError):
            comparison_review.review(self.jobs, json.dumps(data["review_template"]))

    def test_diagnostic_does_not_hide_invalid_responses_or_enable_automation(self):
        """Verify diagnostic does not hide invalid responses or enable automation."""
        from assistant.evaluate import evaluate

        cases = json.loads(
            (Path(__file__).resolve().parents[1] / "assistant/comparison_cases.json").read_text()
        )
        report = evaluate(cases, Mock(side_effect=ValueError("Invalid output")))
        self.assertEqual(report["cases"], 8)
        self.assertEqual(report["invalid_responses"], 8)
        self.assertEqual(report["fixture_passes"], 0)
        self.assertFalse(report["automatic_acceptance_enabled"])

    def test_negative_qualifier_and_indented_future_heading_are_flagged(self):
        """Verify negative qualifier and indented future heading are flagged."""
        self.assertIn(
            "future_or_negated_context",
            comparison_review.flags(
                "Production Python",
                "Non-production Python service.",
                "Non-production Python service.",
                "resume",
            ),
        )
        self.assertIn(
            "qualifier_not_established",
            comparison_review.flags(
                "Commercial Python",
                "Noncommercial Python prototype.",
                "Noncommercial Python prototype.",
                "resume",
            ),
        )
        self.assertIn(
            "future_or_negated_context",
            comparison_review.flags(
                "Python", "Add Python.", "  ## Next steps\nAdd Python.", "evidence"
            ),
        )

    def test_diagnostic_separates_service_failure_without_printing_raw_error(self):
        """Verify diagnostic separates service failure without printing raw error."""
        from assistant.evaluate import evaluate

        def unavailable(*args, **kwargs):
            """Simulate a private provider failure for sanitized diagnostic checks.

            Args:
                args: Additional CLI arguments or test callback positional arguments.
                kwargs: Additional provider or test-double keyword arguments.

            Raises:
                ValueError: The explicit fixture invariant or expected-failure path is violated.
            """
            raise ValueError("PRIVATE SERVICE RESPONSE") from OSError("PRIVATE ADDRESS")

        case = {
            "id": "service",
            "requirement": "Python",
            "source": "Python",
            "kind": "resume",
            "expected_status": "supported",
            "expected_quotes": ["Python"],
        }
        report = evaluate([case], unavailable)
        self.assertEqual(report["results"][0]["failure_category"], "transport_or_service_error")
        self.assertNotIn("PRIVATE", json.dumps(report))
