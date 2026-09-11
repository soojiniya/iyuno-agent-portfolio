import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from app import AgentRunResult, AgentState, normalize_markdown_escapes, run_agent, run_rag_agent


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
        self.embeddings = FakeEmbeddings()


class FakeEmbeddings:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        texts = kwargs["input"]

        class Item:
            def __init__(self, embedding):
                self.embedding = embedding

        class Response:
            def __init__(self, data):
                self.data = data

        data = []
        for text in texts:
            lower = text.lower()
            data.append(
                Item(
                    [
                        float("workflow" in lower or "agent" in lower),
                        float("shipping" in lower),
                        float("review" in lower),
                    ]
                )
            )

        return Response(data)


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
        self.assertIsInstance(result.state, AgentState)
        self.assertEqual(result.state.original_request, "배송 안내 메시지를 작성해줘")
        self.assertEqual(result.state.analysis, "analysis")
        self.assertEqual(result.state.draft, "draft")
        self.assertEqual(result.state.review, "**final**")
        self.assertEqual(result.state.final_answer, "**final**")
        self.assertEqual(result.final_answer, "**final**")
        self.assertEqual([step.name for step in result.steps], ["요청 분석", "초안 생성", "품질 검토"])
        self.assertEqual(len(client.responses.calls), 3)
        self.assertIn(("품질 검토", "complete"), events)

    def test_run_agent_keeps_string_return_for_existing_callers(self):
        client = FakeClient(["analysis", "draft", "final"])

        self.assertEqual(run_agent("작업", client=client, verbose=False), "final")

    def test_run_agent_with_tools_adds_tool_step_and_context(self):
        client = FakeClient(["analysis", "draft", "final"])

        result = run_agent(
            "Calculate 2 + 3 * 4",
            client=client,
            include_steps=True,
            verbose=False,
            use_tools=True,
        )

        self.assertEqual([step.name for step in result.steps], ["요청 분석", "Tool Calling", "초안 생성", "품질 검토"])
        self.assertIn("calculator", result.steps[1].output)
        self.assertIn("14", result.steps[1].output)
        self.assertIn("Tool results:", client.responses.calls[1]["input"])
        self.assertIn("calculator", client.responses.calls[1]["input"])
        self.assertIn("calculator", result.state.tool_results)
        self.assertIn("14", result.state.tool_results)

    def test_run_rag_agent_appends_citations(self):
        client = FakeClient(["analysis", "draft", "final"])

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "agent.md").write_text(
                "The agent workflow has analysis, draft generation, and quality review.",
                encoding="utf-8",
            )

            result = run_rag_agent(
                "agent workflow review",
                client=client,
                data_dir=data_dir,
                include_steps=True,
                verbose=False,
            )

        self.assertIsInstance(result, AgentRunResult)
        self.assertIn("final", result.final_answer)
        self.assertIn("Sources:", result.final_answer)
        self.assertIn("agent.md#chunk-1", result.final_answer)
        self.assertIn("agent.md#chunk-1", result.state.citations)
        self.assertIn("quality review", result.state.retrieved_context)
        self.assertEqual(result.state.review, "final")
        self.assertIn("Sources:", result.state.final_answer)
        self.assertEqual(len(client.responses.calls), 3)
        self.assertGreaterEqual(len(client.embeddings.calls), 2)

    def test_run_rag_agent_with_tools_adds_tool_context(self):
        client = FakeClient(["analysis", "draft", "final"])

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "agent.md").write_text(
                "The agent workflow has analysis, draft generation, and quality review.",
                encoding="utf-8",
            )

            result = run_rag_agent(
                "agent workflow review and calculate 8 + 2",
                client=client,
                data_dir=data_dir,
                include_steps=True,
                verbose=False,
                use_tools=True,
            )

        self.assertIn("Tool Calling", [step.name for step in result.steps])
        tool_step = next(step for step in result.steps if step.name == "Tool Calling")
        self.assertIn("calculator", tool_step.output)
        self.assertIn("10", tool_step.output)
        self.assertIn("Tool results:", client.responses.calls[1]["input"])
        self.assertIn("calculator", result.state.tool_results)
        self.assertIn("10", result.state.tool_results)

    def test_agent_state_summary_contains_core_fields(self):
        state = AgentState(
            original_request="original",
            analysis="analysis",
            retrieved_context="context",
            tool_results="tool",
            draft="draft",
            review="review",
            final_answer="final",
        )

        summary = state.to_summary_markdown()

        self.assertIn("Original request", summary)
        self.assertIn("Analysis", summary)
        self.assertIn("Retrieved RAG context", summary)
        self.assertIn("Tool execution result", summary)
        self.assertIn("Final answer", summary)


if __name__ == "__main__":
    unittest.main()
