import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from feedback import FeedbackRecord, initialize_feedback_db, list_feedback, save_feedback


class FeedbackStorageTest(unittest.TestCase):
    def test_initialize_feedback_db_creates_schema(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "feedback.db"

            initialize_feedback_db(db_path)

            self.assertTrue(db_path.exists())
            self.assertEqual(list_feedback(db_path), [])

    def test_save_and_list_feedback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "feedback.db"

            feedback_id = save_feedback(
                FeedbackRecord(
                    timestamp="2026-09-11T00:00:00+00:00",
                    original_request="Write a customer email",
                    final_answer="Final answer",
                    use_rag=True,
                    use_tools=False,
                    rating="helpful",
                    comment="Clear and useful",
                ),
                db_path,
            )
            rows = list_feedback(db_path)

        self.assertEqual(feedback_id, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["original_request"], "Write a customer email")
        self.assertEqual(rows[0]["final_answer"], "Final answer")
        self.assertEqual(rows[0]["use_rag"], 1)
        self.assertEqual(rows[0]["use_tools"], 0)
        self.assertEqual(rows[0]["rating"], "helpful")
        self.assertEqual(rows[0]["comment"], "Clear and useful")

    def test_invalid_rating_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "feedback.db"

            with self.assertRaises(ValueError):
                save_feedback(
                    FeedbackRecord(
                        original_request="request",
                        final_answer="answer",
                        use_rag=False,
                        use_tools=False,
                        rating="neutral",
                    ),
                    db_path,
                )


if __name__ == "__main__":
    unittest.main()
