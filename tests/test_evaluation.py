import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
EVALUATION_DIR = ROOT_DIR / "evaluation"
sys.path.insert(0, str(EVALUATION_DIR))

from evaluate_agent import DEFAULT_CASES_PATH, load_cases, run_evaluation


class EvaluationTest(unittest.TestCase):
    def test_sample_cases_cover_required_categories_and_minimum_size(self):
        cases = load_cases(DEFAULT_CASES_PATH)
        categories = {case["category"] for case in cases}

        self.assertGreaterEqual(len(cases), 30)
        self.assertEqual(
            categories,
            {"general_agent", "rag", "tool_calling", "mixed_rag_tool"},
        )

        for case in cases:
            self.assertIn("required_keywords", case)
            self.assertIn("expected_behavior", case)

    def test_run_evaluation_computes_core_metrics_without_openai_api(self):
        cases = load_cases(DEFAULT_CASES_PATH)

        report = run_evaluation(cases, data_dir=ROOT_DIR / "data", top_k=3)
        summary = report["summary"]

        self.assertEqual(summary["total_cases"], len(cases))
        self.assertGreaterEqual(summary["task_success_rate"], 0.9)
        self.assertGreaterEqual(summary["keyword_accuracy"], 0.9)
        self.assertGreaterEqual(summary["recall_at_k"], 0.9)
        self.assertGreaterEqual(summary["citation_rate"], 0.9)
        self.assertIn("faithfulness_proxy", summary)
        self.assertGreater(summary["estimated_total_tokens"], 0)

    def test_metrics_report_can_be_saved_as_json(self):
        cases = load_cases(DEFAULT_CASES_PATH)[:4]
        report = run_evaluation(cases, data_dir=ROOT_DIR / "data", top_k=3)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "metrics.json"
            output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            saved = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertIn("summary", saved)
        self.assertIn("by_category", saved)
        self.assertIn("results", saved)


if __name__ == "__main__":
    unittest.main()
