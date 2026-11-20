import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from evals import model_benchmark as benchmark


class ModelBenchmarkTests(unittest.TestCase):
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
        cases = json.loads(benchmark.DEFAULT_CASES.read_text())
        response = Mock(content=b"%PDF-test")
        with patch.object(benchmark.requests, "get", return_value=response) as download:
            payload = benchmark.prepare_payload(cases[0], benchmark.DEFAULT_CASES.parent, fetch_pdf=True)
        download.assert_called_once_with(cases[0]["pdf_url"], timeout=60)
        system, user = payload["messages"]
        self.assertIsInstance(system["content"], str)
        self.assertEqual(user["content"][1]["file"]["file_data"], "data:application/pdf;base64,JVBERi10ZXN0")

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
