"""Regression tests for scan rows abandoned by critical failures."""

from contextlib import contextmanager
from unittest.mock import patch

import db


class _Cursor:
    def __init__(self, rows=None):
        self.executions = []
        self._rows = list(rows or [])

    def execute(self, query, params=None):
        self.executions.append((query, params))

    def fetchall(self):
        return self._rows


@contextmanager
def _cursor_context(cursor):
    yield cursor


def test_close_incomplete_scans_marks_abandoned_runs_failed():
    cursor = _Cursor([{"id": 41}, {"id": 42}])

    with patch("db.get_cursor", return_value=_cursor_context(cursor)):
        closed_ids = db.close_incomplete_scans()

    query, params = cursor.executions[0]
    normalized_query = " ".join(query.split())
    assert closed_ids == [41, 42]
    assert "SET ended_at = NOW()" in normalized_query
    assert "errors = GREATEST(COALESCE(errors, 0), 1)" in normalized_query
    assert "WHERE ended_at IS NULL" in normalized_query
    assert params is None
