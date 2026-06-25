"""Tests for the minimal FastAPI analyst server."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.backend.pipeline import run_pipeline
from src.backend.server import app


class AnalystServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def _dashboard_path(self, directory: str) -> Path:
        *_, dashboard_path = run_pipeline(
            input_path=Path("examples/sample_recent_posts.csv"),
            limit=10,
            provider_name="manual",
            output_dir=Path(directory) / "demo",
        )
        return dashboard_path

    def test_health_endpoint(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_dashboard_data_endpoint_returns_latest_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            dashboard_path = self._dashboard_path(temporary_directory)
            with patch("src.backend.server.DASHBOARD_PATH", dashboard_path):
                response = self.client.get("/api/dashboard-data")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["dataset_overview"]["post_count"], 10)

    def test_analyst_chat_endpoint_with_manual_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            dashboard_path = self._dashboard_path(temporary_directory)
            with patch("src.backend.server.DASHBOARD_PATH", dashboard_path):
                response = self.client.post(
                    "/api/analyst-chat",
                    json={
                        "question": "Which posts performed best recently?",
                        "provider": "manual",
                    },
                )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["provider"], "manual")
        self.assertFalse(payload["llm_called"])
        self.assertIn("summary", payload)
        self.assertTrue(payload["evidence"])

    def test_analyst_chat_endpoint_reports_missing_dashboard_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_path = Path(temporary_directory) / "missing.json"
            with patch("src.backend.server.DASHBOARD_PATH", missing_path):
                response = self.client.post(
                    "/api/analyst-chat",
                    json={"question": "What should I post tomorrow?"},
                )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Run the backend pipeline", response.json()["detail"])

    def test_invalid_provider_is_rejected_by_request_schema(self) -> None:
        response = self.client.post(
            "/api/analyst-chat",
            json={"question": "What should I post tomorrow?", "provider": "deepseek"},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
