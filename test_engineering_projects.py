"""Tests for multi-turn campaign engineering projects."""

import tempfile
import unittest
from pathlib import Path

from management import (
    CampaignState,
    advance_turn,
    load_campaign,
    save_campaign,
    start_engineering_project,
)


class EngineeringProjectTests(unittest.TestCase):
    def test_wind_deflector_takes_three_turns_and_reserves_engineer(self):
        campaign = CampaignState()
        starting_cash = campaign.team.cash

        project = start_engineering_project(
            campaign, "aerodynamics", "wind_deflector"
        )

        self.assertEqual(project.turns_total, 3)
        self.assertEqual(campaign.team.cash, starting_cash - 5_000)
        self.assertEqual(campaign.available_engineers, 0)
        self.assertFalse(
            campaign.research.has_aerodynamics_technology("wind_deflector")
        )
        self.assertFalse(advance_turn(campaign))
        self.assertFalse(
            campaign.research.has_aerodynamics_technology("wind_deflector")
        )
        self.assertFalse(advance_turn(campaign))
        self.assertFalse(
            campaign.research.has_aerodynamics_technology("wind_deflector")
        )

        completed = advance_turn(campaign)

        self.assertEqual(completed, ("wind_deflector",))
        self.assertTrue(
            campaign.research.has_aerodynamics_technology("wind_deflector")
        )
        self.assertEqual(campaign.available_engineers, 1)
        self.assertEqual(campaign.engineering_projects, [])

    def test_project_progress_and_staffing_survive_save_load(self):
        campaign = CampaignState()
        start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        advance_turn(campaign)

        with tempfile.TemporaryDirectory() as temporary_directory:
            save_path = Path(temporary_directory) / "campaign.json"
            save_campaign(campaign, save_path)
            restored = load_campaign(save_path)

        self.assertEqual(len(restored.engineering_projects), 1)
        self.assertEqual(restored.engineering_projects[0].turns_remaining, 2)
        self.assertEqual(restored.available_engineers, 0)
        self.assertFalse(
            restored.research.has_aerodynamics_technology("wind_deflector")
        )

    def test_project_start_rejects_locked_duplicate_and_underfunded_projects(self):
        campaign = CampaignState()

        with self.assertRaisesRegex(ValueError, "prerequisites"):
            start_engineering_project(campaign, "aerodynamics", "basic_streamlining")

        start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        cash_after_start = campaign.team.cash
        with self.assertRaisesRegex(ValueError, "already in progress"):
            start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        self.assertEqual(campaign.team.cash, cash_after_start)

        poor_campaign = CampaignState()
        poor_campaign.team.cash = 4_999
        with self.assertRaisesRegex(ValueError, "insufficient funds"):
            start_engineering_project(
                poor_campaign, "aerodynamics", "wind_deflector"
            )

    def test_project_start_requires_unassigned_engineers(self):
        campaign = CampaignState()
        campaign.team.engineers = 0

        with self.assertRaisesRegex(ValueError, "unassigned engineers"):
            start_engineering_project(campaign, "aerodynamics", "wind_deflector")


if __name__ == "__main__":
    unittest.main()
