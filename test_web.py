"""Tests for the Project Bonneville Flask web adapter."""

import unittest

from web import app


class WebAdapterTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_health_endpoint(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Project Bonneville", response.data)

    def test_health_check(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"Project Bonneville: OK")

    def test_dashboard_renders_campaign(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Campaign", response.data)
        self.assertIn(b"Team", response.data)


if __name__ == "__main__":
    unittest.main()