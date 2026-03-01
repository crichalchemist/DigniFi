"""Tests for health check endpoints."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from config.views import (
    VERSION,
    _check_database,
    _check_disk_space,
    _check_uptime,
    health_check,
    health_check_detailed,
)


def _parse(response) -> dict:
    """Parse JsonResponse content (RequestFactory responses lack .json())."""
    return json.loads(response.content)


# --- Pure function unit tests ---


@pytest.mark.django_db
def test_check_database_ok():
    result = _check_database()
    assert result["status"] == "ok"


@patch("config.views.connection")
def test_check_database_error(mock_conn):
    mock_conn.cursor.side_effect = Exception("connection refused")
    result = _check_database()
    assert result["status"] == "error"
    assert "connection refused" in result["detail"]


def test_check_disk_space_ok(tmp_path):
    result = _check_disk_space(tmp_path)
    assert result["status"] in ("ok", "warning")
    assert "free_mb" in result
    assert "total_mb" in result
    assert "percent_used" in result


def test_check_disk_space_nonexistent():
    result = _check_disk_space(Path("/nonexistent/path/that/does/not/exist"))
    assert result["status"] == "error"


def test_check_uptime():
    result = _check_uptime()
    assert result["status"] == "ok"
    assert result["uptime_seconds"] >= 0


# --- Integration tests ---


@pytest.mark.django_db
class TestHealthCheckEndpoint:
    def setup_method(self):
        self.factory = RequestFactory()

    def test_health_check_returns_ok(self):
        request = self.factory.get("/health/")
        response = health_check(request)
        assert response.status_code == 200
        data = _parse(response)
        assert data["status"] == "ok"
        assert data["database"] == "ok"

    def test_health_check_detailed_returns_all_checks(self):
        request = self.factory.get("/health/detailed/")
        response = health_check_detailed(request)
        assert response.status_code == 200
        data = _parse(response)
        assert data["version"] == VERSION
        assert "checks" in data
        assert "database" in data["checks"]
        assert "disk_generated_forms" in data["checks"]
        assert "disk_media" in data["checks"]
        assert "uptime" in data["checks"]

    def test_health_check_detailed_overall_status(self):
        request = self.factory.get("/health/detailed/")
        response = health_check_detailed(request)
        data = _parse(response)
        assert data["status"] in ("ok", "warning", "error")

    @patch("config.views._check_database")
    def test_health_check_detailed_propagates_error(self, mock_db):
        mock_db.return_value = {"status": "error", "detail": "db down"}
        request = self.factory.get("/health/detailed/")
        response = health_check_detailed(request)
        data = _parse(response)
        assert data["status"] == "error"
