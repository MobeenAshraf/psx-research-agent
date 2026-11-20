import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from evals import model_benchmark as benchmark


class ModelBenchmarkTests(unittest.TestCase):
    def test_comparison_keeps_model_mismatches_and_shared_errors(self):
        case = {
            "id": "report", "stage": "extraction", "audit_references": {},
            "expected": {"operating_profit": 100, "ebitda": 80, "shares": None, "assets": 500},
        }
        trials = [
            {"case": "report", "repeat": 1, "model": name,
             **benchmark.grade(case, values)}
            for name, values in [
                ("first", {"operating_profit": 90, "ebitda": 80, "shares": None, "assets": 500}),
                ("second", {"operating_profit": 90, "ebitda": 85, "assets": 500}),
            ]
        ]
        trials.append({"case": "report", "repeat": 1, "model": "failed"})
        comparison, = benchmark.compare_field_audits([case], trials)
        self.assertEqual(comparison["unavailable_models"], ["failed"])
        self.assertEqual(comparison["fields_compared"], 4)
        fields = {row["field"]: row for row in comparison["findings"]}
        self.assertNotIn("assets", fields)
        self.assertTrue(fields["operating_profit"]["all_compared_models_wrong"])
        self.assertEqual(fields["operating_profit"]["mismatched_pairs"], [])
        self.assertEqual(fields["ebitda"]["mismatched_pairs"], [["first", "second"]])
        self.assertEqual(fields["shares"]["mismatched_pairs"], [["first", "second"]])

    def test_field_audit_resolves_note_rows_and_reports_missing_values(self):
        case = {
            "stage": "extraction",
            "expected": {"rows.#count": 2, "rows.@Zero line|Nil line.value": 0, "profit": 50},
            "audit_references": {"profit": "p. 5"},
            "audit_alternatives": {"profit": [{"value": 45, "reason": "After finance costs"}]},
        }
        result = benchmark.grade(case, {"rows": [{"item": "Other", "value": 20}], "profit": 45})
        self.assertEqual([row["status"] for row in result["field_audit"]], ["wrong_value", "omitted", "wrong_value"])
        self.assertEqual(result["field_audit"][-1]["reason"], "After finance costs")
        self.assertEqual(result["field_audit"][-1]["source"], "p. 5")
        self.assertEqual(benchmark.field({"rows": [{"item": "Nil-line", "value": 0}]}, "rows.@Zero line|Nil line.value"), 0)

    def test_missing_null_and_numeric_strings_fail(self):
        case = {
            "stage": "extraction",
            "expected": {"revenue.current": 100, "eps": None, "capital_expenditures": 1},
            "critical": ["eps"],
        }
        result = benchmark.grade(
            case, {"revenue": {"current": "100"}, "capital_expenditures": True}
        )
        self.assertEqual(result["score"], 0)
        self.assertFalse(result["critical_ok"])
        self.assertFalse(result["passed"])
        valid = {"revenue": {"current": 100}, "eps": None, "capital_expenditures": 1}
        self.assertTrue(benchmark.grade(case, valid)["passed"])

    def test_malformed_and_truncated_responses_retain_billed_cost(self):
        case = {"stage": "analysis", "id": "example", "expected": {"value": 1}}
        session = Mock()
        for content, finish_reason in [("invalid", "stop"), ('{"value": 1}', "length")]:
            with self.subTest(finish_reason=finish_reason):
                session.post.return_value.json.return_value = {
                    "id": "generation",
                    "usage": {"cost": 0.005},
                    "choices": [{"finish_reason": finish_reason, "message": {"content": content}}],
                }
                trial = benchmark.run_trial(session, case, {}, "test/model", 1, 30)
                self.assertFalse(trial["passed"])
                self.assertFalse(trial["valid_json"])
                self.assertEqual(trial["cost_usd"], 0.005)

    def test_extraction_encodes_public_pdf_once_per_payload(self):
        case = {
            "id": "remote", "stage": "extraction", "pdf_url": "https://example.org/test.pdf"
        }
        response = Mock(content=b"%PDF-test")
        with (
            TemporaryDirectory() as directory,
            patch.object(benchmark.requests, "get", return_value=response) as download,
        ):
            options = {"fetch_pdf": True, "pdf_cache": Path(directory)}
            payload = benchmark.prepare_payload(case, benchmark.DEFAULT_CASES.parent, **options)
            self.assertEqual(payload, benchmark.prepare_payload(case, benchmark.DEFAULT_CASES.parent, **options))
        download.assert_called_once_with(case["pdf_url"], timeout=60)
        system, user = payload["messages"]
        self.assertIsInstance(system["content"], str)
        self.assertEqual(user["content"][1]["file"]["file_data"], "data:application/pdf;base64,JVBERi10ZXN0")

    def test_wrong_pdf_hash_is_rejected_without_persisting_it(self):
        case = {
            "id": "pinned", "pdf_url": "https://example.org/test.pdf", "pdf_sha256": "0" * 64,
        }
        with (
            TemporaryDirectory() as directory,
            patch.object(benchmark.requests, "get", return_value=Mock(content=b"%PDF-other")),
        ):
            cache = Path(directory)
            with self.assertRaisesRegex(ValueError, "pinned SHA-256"):
                benchmark.load_pdf(case, cache)
            self.assertEqual(list(cache.iterdir()), [])

    def test_live_cli_keeps_baseline_and_writes_comparison(self):
        session = Mock()
        session.headers = {}
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=False)

        def post(_url, *, json, timeout):
            cost = 0.01 if json["model"] == "test/baseline" else 0.001
            response = Mock()
            response.json.return_value = {
                "model": json["model"],
                "provider": "test",
                "usage": {"cost": cost},
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": '{"investor_summary": "Fixture", "value": 1}'},
                }],
            }
            return response

        session.post.side_effect = post
        with TemporaryDirectory() as directory:
            case_file = Path(directory) / "cases.json"
            case_file.write_text(json.dumps([{
                "stage": "analysis",
                "id": "example",
                "input": {},
                "expected": {"value": 1},
            }]))
            output = Path(directory) / "report.json"
            with (
                patch.object(benchmark.requests, "Session", return_value=session),
                patch.dict(benchmark.os.environ, {
                    "OPENROUTER_API_KEY": "test-key", "ANALYSIS_MODEL": "test/baseline",
                }),
                patch("builtins.print"),
            ):
                exit_code = benchmark.main([
                    "--live", "--cases", str(case_file), "--output", str(output),
                    "--stage", "analysis", "--model", "test/challenger", "--repeats", "2",
                ])
            report = json.loads(output.read_text())

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(report["trials"]), 4)
        self.assertEqual(report["cheapest_passing"], {"analysis": "test/challenger"})
        self.assertAlmostEqual(report["summary"][1]["cost_savings_vs_baseline_pct"], 90)
        self.assertEqual(report["summary"][1]["score_delta_vs_baseline"], 0)

    def test_missing_cost_does_not_rank_as_free(self):
        rows = [
            {
                "stage": "analysis", "model": model, "passed": True,
                "score": 1, "valid_json": True, "cost_usd": cost, "latency_s": 1,
            }
            for model, cost in [("baseline", 0.01), ("unknown", None)]
        ]
        summaries, winners = benchmark.summarize(rows, {"analysis": "baseline"})
        self.assertIsNone(summaries[1]["cost_per_pass_usd"])
        self.assertEqual(winners, {"analysis": "baseline"})
        _, incomplete_winners = benchmark.summarize(rows, {"analysis": "baseline"}, {"analysis"})
        self.assertEqual(incomplete_winners, {})


if __name__ == "__main__":
    unittest.main()
