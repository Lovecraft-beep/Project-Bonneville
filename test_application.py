"""Tests for the UI-independent campaign application boundary."""

import json
from copy import deepcopy
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

    def test_research_summary_is_json_serialisable_and_has_all_branches(self):
        with tempfile.TemporaryDirectory() as directory:
            app = CampaignApplication(Path(directory) / "campaign.json")

            summary = app.research_summary()

            self.assertEqual(
                set(summary["branches"]),
                {"Engine", "Chassis", "Aerodynamics", "Gearbox", "Tyres", "Brakes"},
            )
            self.assertEqual(
                set(summary),
                {
                    "current_era",
                    "available_engineers",
                    "total_engineers",
                    "cash",
                    "selected_development_program",
                    "development_programs",
                    "active_engineering_projects",
                    "branches",
                },
            )
            for branch in summary["branches"].values():
                self.assertTrue(branch["technologies"])
                for technology in branch["technologies"]:
                    self.assertEqual(
                        set(technology),
                        {
                            "technology_id",
                            "name",
                            "era",
                            "description",
                            "status",
                            "effective_project_cost",
                            "effective_project_turns",
                            "engineers_required",
                        },
                    )
            json.dumps(summary)

    def test_opening_research_statuses_follow_existing_prerequisites(self):
        with tempfile.TemporaryDirectory() as directory:
            app = CampaignApplication(Path(directory) / "campaign.json")

            summary = app.research_summary()

            self.assertEqual(summary["selected_development_program"], None)
            self.assertEqual(
                summary["branches"]["Aerodynamics"]["technologies"][0]["status"],
                "PROGRAM REQUIRED",
            )
            management.select_development_program(
                app.campaign, "aerodynamic_pioneer"
            )
            available_summary = app.research_summary()
            self.assertEqual(
                available_summary["branches"]["Aerodynamics"]["technologies"][0][
                    "status"
                ],
                "AVAILABLE",
            )
            for branch_name in (
                "Engine",
                "Chassis",
                "Gearbox",
                "Tyres",
                "Brakes",
            ):
                self.assertEqual(
                    available_summary["branches"][branch_name]["technologies"][0][
                        "status"
                    ],
                    "LOCKED",
                    branch_name,
                )

    def test_research_summary_tracks_project_and_completion_status(self):
        with tempfile.TemporaryDirectory() as directory:
            app = CampaignApplication(Path(directory) / "campaign.json")
            management.select_development_program(
                app.campaign, "aerodynamic_pioneer"
            )
            project = management.start_engineering_project(
                app.campaign, "aerodynamics", "wind_deflector"
            )

            summary = app.research_summary()

            self.assertEqual(
                summary["branches"]["Aerodynamics"]["technologies"][0]["status"],
                "IN PROGRESS",
            )
            self.assertEqual(
                summary["active_engineering_projects"][0]["technology_id"],
                "wind_deflector",
            )
            for _ in range(project.turns_remaining):
                management.advance_turn(app.campaign)

            completed_summary = app.research_summary()

            self.assertEqual(
                completed_summary["branches"]["Aerodynamics"]["technologies"][0][
                    "status"
                ],
                "COMPLETE",
            )
            self.assertEqual(completed_summary["active_engineering_projects"], [])

    def test_research_summary_does_not_mutate_campaign_state(self):
        with tempfile.TemporaryDirectory() as directory:
            app = CampaignApplication(Path(directory) / "campaign.json")
            before = deepcopy(app.campaign)

            app.research_summary()

            self.assertEqual(app.campaign, before)

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

    def test_research_summary_exposes_development_program_choices(self):
        with tempfile.TemporaryDirectory() as directory:
            app = CampaignApplication(Path(directory) / "campaign.json")

            summary = app.research_summary()

            self.assertEqual(len(summary["development_programs"]), 3)
            self.assertEqual(
                {item["program_id"] for item in summary["development_programs"]},
                {
                    "aerodynamic_pioneer",
                    "power_gambler",
                    "engineering_perfectionist",
                },
            )
            json.dumps(summary)

    def test_select_development_program_persists_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "campaign.json"
            app = CampaignApplication(save_path)
            era = app.campaign.current_era

            app.select_development_program("aerodynamic_pioneer")

            self.assertEqual(
                app.campaign.development_programs[era],
                "aerodynamic_pioneer",
            )

            restored = CampaignApplication(save_path)
            self.assertEqual(
                restored.campaign.development_programs[era],
                "aerodynamic_pioneer",
            )

    def test_select_development_program_rejects_invalid_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "campaign.json"
            app = CampaignApplication(save_path)

            with self.assertRaises(ValueError):
                app.select_development_program("not_a_real_program")

            self.assertFalse(save_path.exists())
            self.assertEqual(app.campaign.development_programs, {})

    def test_start_research_project_persists_project(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "campaign.json"
            app = CampaignApplication(save_path)

            app.select_development_program("aerodynamic_pioneer")

            summary = app.research_summary()
            aero = summary["branches"]["Aerodynamics"]
            available = next(
                technology
                for technology in aero["technologies"]
                if technology["status"] == "AVAILABLE"
            )

            project = app.start_research_project(
                "aerodynamics",
                available["technology_id"],
            )

            self.assertEqual(project.technology_id, available["technology_id"])
            self.assertTrue(save_path.exists())

            restored = CampaignApplication(save_path)
            self.assertEqual(
                restored.campaign.engineering_projects[0].technology_id,
                available["technology_id"],
            )

if __name__ == "__main__":
    unittest.main()
