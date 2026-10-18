"""Tests for multi-turn campaign engineering projects."""

import tempfile
import unittest
from pathlib import Path

from engines import PIONEER_SINGLE_CYLINDER
from management import (
    CampaignState,
    advance_turn,
    development_failure_risk_multiplier,
    load_campaign,
    select_development_program,
    save_campaign,
    start_engineering_project,
)
from reliability import resolve_run_failure


class EngineeringProjectTests(unittest.TestCase):
    def test_turns_cycle_four_seasons_before_advancing_year(self):
        campaign = CampaignState()
        self.assertEqual((campaign.current_season, campaign.current_year), ("Spring", 1895))
        for season, year, day in (
            ("Summer", 1895, 92),
            ("Autumn", 1895, 183),
            ("Winter", 1895, 274),
            ("Spring", 1896, 1),
            ("Summer", 1896, 92),
        ):
            advance_turn(campaign)
            self.assertEqual((campaign.current_season, campaign.current_year), (season, year))
            self.assertEqual(campaign.current_day_of_year, day)
        self.assertEqual(campaign.turn_number, 6)

    def test_wind_deflector_takes_three_turns_and_reserves_engineer(self):
        campaign = CampaignState()
        starting_cash = campaign.team.cash
        select_development_program(campaign, "aerodynamic_pioneer")

        project = start_engineering_project(
            campaign, "aerodynamics", "wind_deflector"
        )

        self.assertEqual(project.turns_total, 2)
        self.assertEqual(campaign.team.cash, starting_cash - 4_000)
        self.assertEqual(campaign.available_engineers, 0)
        self.assertFalse(
            campaign.research.has_aerodynamics_technology("wind_deflector")
        )
        completed = advance_turn(campaign)
        self.assertFalse(completed)
        self.assertFalse(
            campaign.research.has_aerodynamics_technology("wind_deflector")
        )
        completed = advance_turn(campaign)

        self.assertEqual(completed, ("wind_deflector",))
        self.assertEqual((campaign.current_season, campaign.current_year), ("Autumn", 1895))
        self.assertTrue(
            campaign.research.has_aerodynamics_technology("wind_deflector")
        )
        self.assertIn(
            "RESEARCH COMPLETE: Wind Deflector is now available to the team.",
            campaign.world.headlines,
        )
        self.assertEqual(campaign.available_engineers, 1)
        self.assertEqual(campaign.engineering_projects, [])

    def test_project_progress_and_staffing_survive_save_load(self):
        campaign = CampaignState()
        select_development_program(campaign, "aerodynamic_pioneer")
        start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        advance_turn(campaign)

        with tempfile.TemporaryDirectory() as temporary_directory:
            save_path = Path(temporary_directory) / "campaign.json"
            save_campaign(campaign, save_path)
            restored = load_campaign(save_path)

        self.assertEqual(len(restored.engineering_projects), 1)
        self.assertEqual(restored.engineering_projects[0].turns_remaining, 1)
        self.assertEqual(
            restored.development_programs,
            {"Pioneers": "aerodynamic_pioneer"},
        )
        self.assertEqual(restored.available_engineers, 0)
        self.assertEqual((restored.current_season, restored.current_year), ("Summer", 1895))
        advance_turn(restored)
        self.assertEqual((restored.current_season, restored.current_year), ("Autumn", 1895))
        self.assertTrue(
            restored.research.has_aerodynamics_technology("wind_deflector")
        )

    def test_project_start_rejects_locked_duplicate_and_underfunded_projects(self):
        campaign = CampaignState()

        with self.assertRaisesRegex(ValueError, "prerequisites"):
            start_engineering_project(campaign, "aerodynamics", "basic_streamlining")

        select_development_program(campaign, "aerodynamic_pioneer")
        start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        cash_after_start = campaign.team.cash
        with self.assertRaisesRegex(ValueError, "already in progress"):
            start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        self.assertEqual(campaign.team.cash, cash_after_start)

        poor_campaign = CampaignState()
        select_development_program(poor_campaign, "aerodynamic_pioneer")
        poor_campaign.team.cash = 3_999
        with self.assertRaisesRegex(ValueError, "insufficient funds"):
            start_engineering_project(
                poor_campaign, "aerodynamics", "wind_deflector"
            )

    def test_project_start_requires_unassigned_engineers(self):
        campaign = CampaignState()
        campaign.team.engineers = 0
        select_development_program(campaign, "aerodynamic_pioneer")

        with self.assertRaisesRegex(ValueError, "unassigned engineers"):
            start_engineering_project(campaign, "aerodynamics", "wind_deflector")

    def test_development_program_is_binding_and_changes_project_economics(self):
        campaign = CampaignState()
        with self.assertRaisesRegex(ValueError, "choose a major development program"):
            start_engineering_project(campaign, "aerodynamics", "wind_deflector")

        select_development_program(campaign, "aerodynamic_pioneer")
        project = start_engineering_project(
            campaign, "aerodynamics", "wind_deflector"
        )
        self.assertEqual((project.turns_total, campaign.team.cash), (2, 96_000))
        with self.assertRaisesRegex(ValueError, "already committed"):
            select_development_program(campaign, "power_gambler")

        power_campaign = CampaignState()
        select_development_program(power_campaign, "power_gambler")
        penalized = start_engineering_project(
            power_campaign, "aerodynamics", "wind_deflector"
        )
        self.assertEqual(penalized.turns_total, 4)
        self.assertEqual(power_campaign.team.cash, 93_750)

    def test_program_risk_tradeoff_changes_with_the_historical_era(self):
        campaign = CampaignState()
        select_development_program(campaign, "power_gambler")
        power_risk = development_failure_risk_multiplier(campaign)
        self.assertEqual(power_risk, 1.15)
        baseline = resolve_run_failure(
            PIONEER_SINGLE_CYLINDER,
            100.0,
            campaign.team,
            random_value=1.0,
        ).failure_probability
        power = resolve_run_failure(
            PIONEER_SINGLE_CYLINDER,
            100.0,
            campaign.team,
            random_value=1.0,
            failure_risk_multiplier=power_risk,
        ).failure_probability
        self.assertGreater(power, baseline)

        campaign.current_year = 1915
        select_development_program(campaign, "engineering_perfectionist")
        perfectionist_risk = development_failure_risk_multiplier(campaign)
        self.assertEqual(perfectionist_risk, 0.75)
        perfectionist = resolve_run_failure(
            PIONEER_SINGLE_CYLINDER,
            100.0,
            campaign.team,
            random_value=1.0,
            failure_risk_multiplier=perfectionist_risk,
        ).failure_probability
        self.assertLess(perfectionist, baseline)


if __name__ == "__main__":
    unittest.main()
