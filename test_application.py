"""Tests for the UI-independent campaign application boundary."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import management
from application import CampaignApplication
from management import CampaignState, load_campaign, save_campaign


class CampaignApplicationTests(unittest.TestCase):
    def test_constructor_loads_existing_campaign_or_creates_fresh_campaign(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "campaign.json"
            existing = CampaignState()
            existing.turn_number = 7
            save_campaign(existing, save_path)

            loaded_app = CampaignApplication(save_path)
            self.assertEqual(loaded_app.campaign.campaign_id, existing.campaign_id)
            self.assertEqual(loaded_app.campaign.turn_number, 7)

            fresh_path = Path(directory) / "fresh-campaign.json"
            fresh_app = CampaignApplication(fresh_path)
            self.assertIsInstance(fresh_app.campaign, CampaignState)
            self.assertEqual(fresh_app.campaign.turn_number, 1)
            self.assertFalse(fresh_path.exists())

    def test_new_campaign_resets_state_and_removes_existing_save(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "campaign.json"
            existing = CampaignState()
            existing.turn_number = 7
            save_campaign(existing, save_path)
            app = CampaignApplication(save_path)

            fresh = app.new_campaign()

            self.assertIs(fresh, app.campaign)
            self.assertNotEqual(fresh.campaign_id, existing.campaign_id)
            self.assertEqual(fresh.turn_number, 1)
            self.assertFalse(save_path.exists())

    def test_save_persists_current_campaign(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "campaign.json"
            app = CampaignApplication(save_path)
            app.campaign.team.name = "Test Bonneville Team"

            app.save()

            persisted = load_campaign(save_path)
            self.assertEqual(persisted.campaign_id, app.campaign.campaign_id)
            self.assertEqual(persisted.team.name, "Test Bonneville Team")

    def test_advance_turn_advances_and_automatically_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "campaign.json"
            app = CampaignApplication(save_path)
            self.assertEqual(app.campaign.turn_number, 1)

            app.advance_turn()

            self.assertEqual(app.campaign.turn_number, 2)
            self.assertEqual(load_campaign(save_path).turn_number, 2)

    def test_advance_turn_returns_management_result_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "campaign.json"
            app = CampaignApplication(save_path)
            completed_ids = ("engine_technology", "tyre_technology")

            with patch(
                "management.advance_turn", return_value=completed_ids
            ) as advance:
                result = app.advance_turn()

            advance.assert_called_once_with(app.campaign, days=None)
            self.assertIs(result, completed_ids)

    def test_summary_has_expected_fields_and_is_json_serialisable(self):
        with tempfile.TemporaryDirectory() as directory:
            app = CampaignApplication(Path(directory) / "campaign.json")
            app.campaign.world.headlines = ["Test headline"]
            app.campaign.world.reactions = ["Test reaction"]

            summary = app.summary()

            self.assertEqual(
                set(summary),
                {
                    "campaign_id",
                    "turn_number",
                    "current_year",
                    "current_day_of_year",
                    "current_season",
                    "current_era",
                    "team",
                    "world_record",
                    "headlines",
                    "reactions",
                },
            )
            self.assertEqual(
                set(summary["team"]),
                {
                    "name",
                    "cash",
                    "reputation",
                    "engineers",
                    "mechanics",
                    "workshop_level",
                },
            )
            self.assertEqual(
                set(summary["world_record"]),
                {"speed_mph", "holder", "year"},
            )
            self.assertEqual(summary["headlines"], ["Test headline"])
            self.assertEqual(summary["reactions"], ["Test reaction"])
            json.dumps(summary)

    def test_application_can_be_used_without_importing_ui_modules(self):
        script = """
import sys
import tempfile
from pathlib import Path

from application import CampaignApplication

with tempfile.TemporaryDirectory() as directory:
    app = CampaignApplication(Path(directory) / "campaign.json")
    app.summary()

assert "tkinter" not in sys.modules
assert "ui.app" not in sys.modules
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
