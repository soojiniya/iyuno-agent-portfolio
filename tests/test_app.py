import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from app import AgentRunResult, normalize_markdown_escapes, run_agent


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)

        class Response:
            def __init__(self, output_text):
                self.output_text = output_text

        return Response(self.outputs.pop(0))


class FakeClient:
    def __init__(self, outputs):
        self.responses = FakeResponses(outputs)


class AgentWorkflowTest(unittest.TestCase):
    def test_normalize_markdown_escapes_unescapes_common_markdown(self):
        escaped = r"\*\*[현재 배송 위치]\*\*"

        self.assertEqual(
            normalize_markdown_escapes(escaped),
            "**[현재 배송 위치]**",
        )

    def test_run_agent_returns_steps_when_requested(self):
        client = FakeClient(
            [
                "analysis",
                "draft",
                r"\*\*final\*\*",
            ]
        )
        events = []

        result = run_agent(
            "배송 안내 메시지를 작성해줘",
            client=client,
            include_steps=True,
            verbose=False,
            progress_callback=lambda name, status: events.append((name, status)),
        )

        self.assertIsInstance(result, AgentRunResult)
        self.assertEqual(result.final_answer, "**final**")
        self.assertEqual([step.name for step in result.steps], ["요청 분석", "초안 생성", "품질 검토"])
        self.assertEqual(len(client.responses.calls), 3)
        self.assertIn(("품질 검토", "complete"), events)

    def test_run_agent_keeps_string_return_for_existing_callers(self):
        client = FakeClient(["analysis", "draft", "final"])

        self.assertEqual(run_agent("작업", client=client, verbose=False), "final")


if __name__ == "__main__":
    unittest.main()
