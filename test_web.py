"""Tests for the Project Bonneville Flask web adapter."""

from pathlib import Path
import tempfile
import unittest

import web
from application import CampaignApplication

class WebAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        save_path = Path(self.temporary_directory.name) / "campaign.json"

        self.original_campaign_app = web.campaign_app
        web.campaign_app = CampaignApplication(save_path)

        self.client = web.app.test_client()

    def tearDown(self):
        web.campaign_app = self.original_campaign_app
        self.temporary_directory.cleanup()

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

    def test_end_turn_redirects_to_dashboard(self):
        before = web.campaign_app.campaign.turn_number

        response = self.client.post("/turn")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")
        self.assertEqual(
            web.campaign_app.campaign.turn_number,
            before + 1,
        )
    def test_end_turn_advances_persists_and_redirects(self):
        before = web.campaign_app.campaign.turn_number
        save_path = web.campaign_app.save_path

        response = self.client.post("/turn")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")
        self.assertEqual(web.campaign_app.campaign.turn_number, before + 1)
        self.assertTrue(save_path.exists())

        restored = CampaignApplication(save_path)
        self.assertEqual(
            restored.campaign.turn_number,
            web.campaign_app.campaign.turn_number,
        )
if __name__ == "__main__":
    unittest.main()