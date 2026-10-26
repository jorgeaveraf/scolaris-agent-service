import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.admin import repository


class RecordingCursor:
    def __init__(self):
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, statement, params):
        self.statements.append((statement, params))

    def fetchone(self):
        return {"count": 0}

    def fetchall(self):
        return []


class RecordingConnection:
    def __init__(self, cursor):
        self.recording_cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return self.recording_cursor


class DocumentsUpdatedFilterTests(unittest.TestCase):
    def test_updated_range_applies_to_count_and_items(self):
        start = datetime(2026, 10, 26, 6, tzinfo=timezone.utc)
        end = datetime(2026, 10, 27, 6, tzinfo=timezone.utc)
        cursor = RecordingCursor()

        with patch.object(repository, "_connect", return_value=RecordingConnection(cursor)):
            repository.list_documents(
                filters={"updated_from": start, "updated_before": end},
                limit=10,
                offset=0,
            )

        self.assertEqual(len(cursor.statements), 2)
        for sql, params in cursor.statements:
            self.assertIn("updated_at >= %s", sql)
            self.assertIn("updated_at < %s", sql)
            self.assertNotIn("vigencia = %s", sql)
            self.assertEqual(params[:2], [start, end])


if __name__ == "__main__":
    unittest.main()
