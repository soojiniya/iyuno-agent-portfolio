import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


DEFAULT_FEEDBACK_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "feedback.db"
FEEDBACK_DB_PATH_ENV = "IYUNO_FEEDBACK_DB_PATH"
VALID_RATINGS = {"helpful", "not_helpful"}


@dataclass
class FeedbackRecord:
    original_request: str
    final_answer: str
    use_rag: bool
    use_tools: bool
    rating: str
    comment: str = ""
    timestamp: Optional[str] = None


def get_feedback_db_path():
    configured_path = os.getenv(FEEDBACK_DB_PATH_ENV)
    return Path(configured_path) if configured_path else DEFAULT_FEEDBACK_DB_PATH


def connect_feedback_db(db_path=None):
    path = Path(db_path) if db_path else get_feedback_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)


def initialize_feedback_db(db_path=None):
    with closing(connect_feedback_db(db_path)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                original_request TEXT NOT NULL,
                final_answer TEXT NOT NULL,
                use_rag INTEGER NOT NULL,
                use_tools INTEGER NOT NULL,
                rating TEXT NOT NULL CHECK (rating IN ('helpful', 'not_helpful')),
                comment TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.commit()


def save_feedback(record, db_path=None):
    if record.rating not in VALID_RATINGS:
        raise ValueError("feedback rating must be one of: helpful, not_helpful")

    timestamp = record.timestamp or datetime.now(timezone.utc).isoformat()
    initialize_feedback_db(db_path)

    with closing(connect_feedback_db(db_path)) as connection:
        cursor = connection.execute(
            """
            INSERT INTO feedback (
                timestamp,
                original_request,
                final_answer,
                use_rag,
                use_tools,
                rating,
                comment
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                record.original_request,
                record.final_answer,
                int(record.use_rag),
                int(record.use_tools),
                record.rating,
                record.comment or "",
            ),
        )
        connection.commit()
        return cursor.lastrowid


def list_feedback(db_path=None, limit=None) -> List[dict]:
    initialize_feedback_db(db_path)

    query = """
        SELECT
            id,
            timestamp,
            original_request,
            final_answer,
            use_rag,
            use_tools,
            rating,
            comment
        FROM feedback
        ORDER BY id DESC
    """
    params = ()

    if limit is not None:
        query += " LIMIT ?"
        params = (int(limit),)

    with closing(connect_feedback_db(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()

    return [dict(row) for row in rows]
