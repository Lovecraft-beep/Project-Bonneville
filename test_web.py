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
    def test_campaign_state_survives_application_restart(self):
        web.campaign_app.advance_turn()

        expected_turn = web.campaign_app.campaign.turn_number
        expected_campaign_id = web.campaign_app.campaign.campaign_id
        save_path = web.campaign_app.save_path

        restarted_app = CampaignApplication(save_path)

        self.assertEqual(
            restarted_app.campaign.campaign_id,
            expected_campaign_id,
        )
        self.assertEqual(
            restarted_app.campaign.turn_number,
            expected_turn,
        )
    def test_new_campaign_confirmation_is_read_only(self):
        campaign_id = web.campaign_app.campaign.campaign_id
        turn_number = web.campaign_app.campaign.turn_number

        response = self.client.get("/new")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Start a New Campaign?", response.data)
        self.assertEqual(
            web.campaign_app.campaign.campaign_id,
            campaign_id,
        )
        self.assertEqual(
            web.campaign_app.campaign.turn_number,
            turn_number,
        )
    def test_new_campaign_resets_persists_and_redirects(self):
        web.campaign_app.advance_turn()
        old_campaign_id = web.campaign_app.campaign.campaign_id
        save_path = web.campaign_app.save_path

        self.assertGreater(web.campaign_app.campaign.turn_number, 1)

        response = self.client.post("/new")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/")
        self.assertNotEqual(
            web.campaign_app.campaign.campaign_id,
            old_campaign_id,
        )
        self.assertEqual(web.campaign_app.campaign.turn_number, 1)
        self.assertTrue(save_path.exists())

        restored = CampaignApplication(save_path)
        self.assertEqual(
            restored.campaign.campaign_id,
            web.campaign_app.campaign.campaign_id,
        )
        self.assertEqual(restored.campaign.turn_number, 1)

    def test_research_page_renders_application_research_summary(self):
        response = self.client.get("/research")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Research &amp; Development", response.data)
        self.assertIn(b"Aerodynamics", response.data)
        self.assertIn(b"Engineering Resources", response.data)

    def test_select_research_program_persists_and_redirects(self):
        era = web.campaign_app.campaign.current_era
        save_path = web.campaign_app.save_path

        response = self.client.post(
            "/research/program",
            data={"program_id": "aerodynamic_pioneer"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/research")
        self.assertEqual(
            web.campaign_app.campaign.development_programs[era],
            "aerodynamic_pioneer",
        )

        restored = CampaignApplication(save_path)
        self.assertEqual(
            restored.campaign.development_programs[era],
            "aerodynamic_pioneer",
        )

if __name__ == "__main__":
    unittest.main()