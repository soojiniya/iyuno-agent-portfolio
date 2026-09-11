import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from tools import calculator_tool, date_diff_tool, format_tool_results, select_and_run_tools, text_stats_tool


class ToolCallingTest(unittest.TestCase):
    def test_calculator_tool_evaluates_arithmetic(self):
        result = calculator_tool("2 + 3 * 4")

        self.assertEqual(result.name, "calculator")
        self.assertEqual(result.output, "14")

    def test_text_stats_tool_counts_words_and_characters(self):
        result = text_stats_tool("hello world 테스트")

        self.assertEqual(result.name, "text_stats")
        self.assertIn("words=3", result.output)

    def test_date_diff_tool_calculates_days(self):
        result = date_diff_tool("2026-01-01", "2026-01-10")

        self.assertEqual(result.name, "date_diff")
        self.assertEqual(result.output, "9 days")

    def test_select_and_run_tools_routes_multiple_tools(self):
        results = select_and_run_tools(
            "Calculate 10 / 2 and tell me word count for this text. Also 날짜 차이 2026-01-01 2026-01-03"
        )
        names = [result.name for result in results]

        self.assertIn("calculator", names)
        self.assertIn("text_stats", names)
        self.assertIn("date_diff", names)
        self.assertIn("Tool calls:", format_tool_results(results))

    def test_select_and_run_tools_returns_empty_when_no_tool_needed(self):
        self.assertEqual(select_and_run_tools("Write a polite email."), [])
        self.assertEqual(format_tool_results([]), "Tool calls: none")


if __name__ == "__main__":
    unittest.main()
