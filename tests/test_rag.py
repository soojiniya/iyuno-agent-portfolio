import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from rag import SimpleTextEmbedder, chunk_text, format_citations, retrieve


class RagTest(unittest.TestCase):
    def test_chunk_text_splits_long_documents_with_overlap(self):
        text = " ".join([f"word{i}" for i in range(100)])

        chunks = chunk_text(text, chunk_size=120, overlap=20)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk for chunk in chunks))

    def test_retrieve_returns_most_relevant_document_with_citation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir)
            (data_dir / "agent.md").write_text(
                "Agent workflow includes analysis draft review final result.",
                encoding="utf-8",
            )
            (data_dir / "shipping.txt").write_text(
                "Shipping delay email should include apology and delivery status.",
                encoding="utf-8",
            )
            embedder = SimpleTextEmbedder()

            results = retrieve(
                "How does the agent workflow review step work?",
                data_dir,
                embedder.embed,
                top_k=1,
            )

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].chunk.source, "agent.md")
            self.assertIn("agent.md#chunk-1", format_citations(results))

    def test_retrieve_empty_data_dir_returns_no_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            embedder = SimpleTextEmbedder()

            results = retrieve("anything", temp_dir, embedder.embed)

            self.assertEqual(results, [])
            self.assertEqual(format_citations(results), "Sources: No matching local documents found.")


if __name__ == "__main__":
    unittest.main()
