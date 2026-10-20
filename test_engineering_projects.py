"""Tests for multi-turn campaign engineering projects."""

import tempfile
import unittest
from pathlib import Path

from engines import PIONEER_SINGLE_CYLINDER
from management import (
    CampaignState,
    GarageVehicle,
    advance_turn,
    build_vehicle,
    development_failure_risk_multiplier,
    load_campaign,
    select_development_program,
    save_campaign,
    start_engineering_project,
    vehicle_construction_complexity,
)
from reliability import resolve_run_failure


class SponsorDevelopmentTests(unittest.TestCase):
    def test_vehicle_delivery_rewards_development_without_testing(self):
        from management import sign_sponsor

        campaign = CampaignState()
        campaign.team.reputation = 5
        sign_sponsor(campaign, "dunlop")
        entry = GarageVehicle(
            "Development Car", "improvised_chassis", PIONEER_SINGLE_CYLINDER.name,
            "2-Speed Transmission", "Wooden block brakes",
        )
        build_vehicle(campaign, entry, 1000)
        cash = campaign.team.cash
        advance_turn(campaign)
        self.assertEqual(campaign.completed_runs, 0)
        self.assertEqual(campaign.completed_development_milestones, 1)
        self.assertEqual(campaign.team.cash, cash - 450 + 4000)
        self.assertTrue(any("Dunlop objective met" in item for item in campaign.world.headlines))

    def test_existing_development_is_not_retroactively_rewarded_after_signing(self):
        from management import check_sponsor_objectives, sign_sponsor

        campaign = CampaignState(completed_development_milestones=3)
        objective = sign_sponsor(campaign, "castrol")
        self.assertEqual(objective.development_at_issue, 3)
        self.assertEqual(check_sponsor_objectives(campaign), [])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "campaign.json"
            save_campaign(campaign, path)
            restored = load_campaign(path)
        self.assertEqual(restored.completed_development_milestones, 3)
        self.assertEqual(restored.sponsorship.objective_for("castrol").development_at_issue, 3)
        self.assertEqual(check_sponsor_objectives(restored), [])

    def test_saved_run_quotas_become_ongoing_development_partnerships(self):
        from management import sign_sponsor

        campaign = CampaignState()
        objective = sign_sponsor(campaign, "castrol")
        objective.kind = "runs"
        objective.target = 3
        objective.turns_remaining = 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "campaign.json"
            save_campaign(campaign, path)
            restored = load_campaign(path)
        replacement = restored.sponsorship.objective_for("castrol")
        self.assertEqual(replacement.kind, "development")
        self.assertEqual(replacement.target, 1)
        self.assertIsNone(replacement.turns_remaining)
        self.assertIn("castrol", restored.sponsorship.active_sponsors)

    def test_repeated_tests_neither_earn_technical_rewards_nor_require_renewal(self):
        from management import complete_run, sign_sponsor

        campaign = CampaignState()
        sign_sponsor(campaign, "castrol")
        cash = campaign.team.cash
        for _ in range(6):
            self.assertEqual(complete_run(campaign, 0, 20), [])
            advance_turn(campaign)
        self.assertEqual(campaign.team.cash, cash - 6 * campaign.team.payroll_per_turn_gbp)
        self.assertIn("castrol", campaign.sponsorship.active_sponsors)
        self.assertIsNone(campaign.sponsorship.objective_for("castrol").turns_remaining)

    def test_finished_research_pays_without_a_run_and_cannot_pay_twice(self):
        from management import sign_sponsor

        campaign = CampaignState()
        sign_sponsor(campaign, "castrol")
        select_development_program(campaign, "aerodynamic_pioneer")
        start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        cash = campaign.team.cash
        advance_turn(campaign)
        self.assertEqual(campaign.team.cash, cash - 450)
        advance_turn(campaign)
        self.assertEqual(campaign.completed_runs, 0)
        self.assertEqual(campaign.team.cash, cash - 900 + 3000)
        self.assertEqual(campaign.sponsorship.objective_for("castrol").development_at_issue, 1)
        advance_turn(campaign)
        self.assertEqual(campaign.team.cash, cash - 1350 + 3000)


class PersonnelTests(unittest.TestCase):
    def test_recruitment_confirmation_quotes_recurring_wages_and_projected_cash(self):
        from types import SimpleNamespace
        from unittest.mock import Mock, patch
        from ui.app import BonnevilleApp
        from management import hire_specialist_engineer

        campaign = CampaignState()
        app = SimpleNamespace(campaign=campaign, team_action=Mock())
        action = lambda state: hire_specialist_engineer(state, "engine")
        with patch("ui.app.messagebox.askyesno", return_value=False) as confirm:
            BonnevilleApp.hire_staff_action(app, action, "Engine specialist", 16000, 650)
        self.assertIn("GBP 650 every turn", confirm.call_args.args[1])
        self.assertIn("GBP 82,900", confirm.call_args.args[1])
        app.team_action.assert_not_called()
        with patch("ui.app.messagebox.askyesno", return_value=True):
            BonnevilleApp.hire_staff_action(app, action, "Engine specialist", 16000, 650)
        app.team_action.assert_called_once_with(action, "Engine specialist hired")

    def test_parallel_projects_reserve_specialist_and_standard_staff_separately(self):
        from management import dismiss_engineer, hire_specialist_engineer

        campaign = CampaignState()
        select_development_program(campaign, "aerodynamic_pioneer")
        campaign.research.aerodynamics_technology.append("wind_deflector")
        hire_specialist_engineer(campaign, "aerodynamics")
        aero = start_engineering_project(campaign, "aerodynamics", "wheel_fairings_/_spats")
        engine = start_engineering_project(campaign, "engine", "pioneer_engines")
        self.assertEqual(aero.specialists, ["aerodynamics"])
        self.assertEqual(engine.specialists, [])
        self.assertEqual(campaign.available_engineers, 0)
        with self.assertRaisesRegex(ValueError, "unassigned standard"):
            dismiss_engineer(campaign)

    def test_specialist_used_outside_specialty_has_no_speed_bonus(self):
        from management import dismiss_engineer, hire_specialist_engineer

        campaign = CampaignState()
        select_development_program(campaign, "aerodynamic_pioneer")
        hire_specialist_engineer(campaign, "engine")
        dismiss_engineer(campaign)
        project = start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        self.assertEqual(project.turns_total, 2)
        self.assertEqual(project.specialists, ["engine"])
        self.assertEqual(campaign.available_engineers, 0)

    def test_staff_quality_and_project_assignments_survive_save_load(self):
        from management import available_engineer_specialties, hire_experienced_mechanic, hire_specialist_engineer

        campaign = CampaignState()
        select_development_program(campaign, "power_gambler")
        hire_specialist_engineer(campaign, "aerodynamics")
        hire_experienced_mechanic(campaign)
        start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        advance_turn(campaign)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "campaign.json"
            save_campaign(campaign, path)
            restored = load_campaign(path)
        self.assertEqual(restored.team, campaign.team)
        self.assertEqual(restored.team.payroll_per_turn_gbp, 1350)
        self.assertEqual(restored.engineering_projects[0].specialists, ["aerodynamics"])
        self.assertEqual(available_engineer_specialties(restored), [])

    def test_forecast_includes_sponsor_income_and_all_wages(self):
        from management import hire_engineer
        from sponsors import SPONSOR_CATALOG

        campaign = CampaignState()
        campaign.sponsorship.add_sponsor(SPONSOR_CATALOG[0].sponsor_id)
        cash = campaign.team.cash
        hire_engineer(campaign)
        self.assertEqual(campaign.turn_number, 1)
        self.assertEqual(campaign.team.cash, cash - 8000)
        expected = campaign.team.cash + campaign.sponsorship.income_per_turn_gbp - 700
        self.assertEqual(campaign.projected_next_turn_cash_gbp, expected)
        advance_turn(campaign)
        self.assertEqual(campaign.team.cash, expected)

    def test_release_reduces_future_payroll_without_refunding_recruitment(self):
        from management import dismiss_engineer, dismiss_mechanic, hire_engineer

        campaign = CampaignState()
        hire_engineer(campaign)
        cash = campaign.team.cash
        dismiss_engineer(campaign)
        dismiss_mechanic(campaign)
        self.assertEqual(campaign.team.cash, cash)
        self.assertEqual(campaign.team.payroll_per_turn_gbp, 350)
        with self.assertRaisesRegex(ValueError, "at least one engineer"):
            dismiss_engineer(campaign)

    def test_specialist_accelerates_only_matching_work_and_stays_reserved(self):
        from management import dismiss_engineer, engineering_project_terms, hire_specialist_engineer
        from research import AERODYNAMICS_TECHNOLOGY_TREE

        campaign = CampaignState()
        select_development_program(campaign, "aerodynamic_pioneer")
        hire_specialist_engineer(campaign, "aerodynamics")
        self.assertEqual(campaign.team.engineers, 2)
        self.assertEqual(campaign.team.payroll_per_turn_gbp, 1100)
        node = AERODYNAMICS_TECHNOLOGY_TREE[0]
        self.assertEqual(engineering_project_terms(campaign, "aerodynamics", node)[1], 1)
        self.assertEqual(engineering_project_terms(campaign, "engine", node)[1], 4)
        project = start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        self.assertEqual(project.specialists, ["aerodynamics"])
        self.assertEqual(campaign.available_engineers, 1)
        self.assertEqual(engineering_project_terms(campaign, "aerodynamics", node)[1], 2)
        with self.assertRaisesRegex(ValueError, "unassigned specialist"):
            dismiss_engineer(campaign, "aerodynamics")
        advance_turn(campaign)
        dismiss_engineer(campaign, "aerodynamics")
        self.assertEqual(campaign.team.payroll_per_turn_gbp, 450)

    def test_experienced_mechanic_improves_risk_and_repair_coverage(self):
        from management import Team, dismiss_mechanic, hire_experienced_mechanic
        from reliability import calculate_failure_probability, can_repair_trackside

        standard = Team(mechanics=1)
        campaign = CampaignState(team=Team(mechanics=0))
        hire_experienced_mechanic(campaign)
        self.assertEqual(campaign.team.payroll_per_turn_gbp, 500)
        self.assertFalse(can_repair_trackside(standard))
        self.assertTrue(can_repair_trackside(campaign.team))
        self.assertLess(
            calculate_failure_probability(PIONEER_SINGLE_CYLINDER, 100, campaign.team),
            calculate_failure_probability(PIONEER_SINGLE_CYLINDER, 100, standard),
        )
        dismiss_mechanic(campaign, experienced=True)
        self.assertEqual((campaign.team.mechanics, campaign.team.experienced_mechanics), (0, 0))

    def test_idle_and_allocated_staff_draw_wages_once_per_turn(self):
        campaign = CampaignState()
        self.assertEqual(campaign.team.payroll_per_turn_gbp, 450)
        select_development_program(campaign, "aerodynamic_pioneer")
        start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        cash = campaign.team.cash
        advance_turn(campaign)
        self.assertEqual(campaign.team.cash, cash - 450)
        advance_turn(campaign)
        self.assertEqual(campaign.team.cash, cash - 900)
        advance_turn(campaign)
        self.assertEqual(campaign.team.cash, cash - 1350)

    def test_payroll_can_create_a_visible_deficit_without_blocking_turns(self):
        campaign = CampaignState()
        campaign.team.cash = 100
        advance_turn(campaign)
        self.assertEqual(campaign.team.cash, -350)
        self.assertEqual(campaign.turn_number, 2)
        self.assertTrue(any("PAYROLL WARNING" in item for item in campaign.world.headlines))


class VehicleConstructionTests(unittest.TestCase):
    def entry(self, name="Construction Test", chassis_id="improvised_chassis"):
        return GarageVehicle(
            name,
            chassis_id,
            PIONEER_SINGLE_CYLINDER.name,
            "2-Speed Transmission",
            "Wooden block brakes",
        )

    def test_early_car_is_paid_now_and_delivered_next_turn_once(self):
        campaign = CampaignState()
        entry = self.entry()
        project = build_vehicle(campaign, entry, 1_000)
        self.assertEqual(campaign.team.cash, 99_000)
        self.assertEqual(campaign.turn_number, 1)
        self.assertEqual(project.turns_remaining, 1)
        self.assertEqual(campaign.garage.vehicles, [])
        advance_turn(campaign)
        self.assertEqual(campaign.garage.vehicles, [entry])
        self.assertEqual(campaign.vehicle_construction, [])
        self.assertTrue(any("CONSTRUCTION COMPLETE" in item for item in campaign.world.headlines))
        advance_turn(campaign)
        self.assertEqual(len(campaign.garage.vehicles), 1)

    def test_complex_car_waits_for_all_turns_and_survives_save_load(self):
        from research import CHASSIS_TECHNOLOGY_TREE

        campaign = CampaignState()
        entry = self.entry(chassis_id=CHASSIS_TECHNOLOGY_TREE[-1].technology_id)
        project = build_vehicle(campaign, entry, 1_000)
        self.assertEqual(project.complexity, 5)
        advance_turn(campaign)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "campaign.json"
            save_campaign(campaign, path)
            restored = load_campaign(path)
        self.assertIsInstance(restored.vehicle_construction[0].vehicle, GarageVehicle)
        self.assertEqual(restored.vehicle_construction[0].turns_remaining, 4)
        for remaining in (3, 2, 1):
            advance_turn(restored)
            self.assertEqual(restored.vehicle_construction[0].turns_remaining, remaining)
            self.assertEqual(restored.garage.vehicles, [])
        advance_turn(restored)
        self.assertEqual(restored.garage.vehicles, [entry])

    def test_complexity_uses_fitted_components_not_campaign_date(self):
        from research import CHASSIS_TECHNOLOGY_TREE

        self.assertEqual(
            [vehicle_construction_complexity(self.entry(chassis_id=node.technology_id))
             for node in CHASSIS_TECHNOLOGY_TREE[::5]],
            [1, 2, 3, 4, 5],
        )
        entry = self.entry()
        entry.brakes_name = "Carbon-carbon brakes"
        self.assertGreater(vehicle_construction_complexity(entry), 1)
        campaign = CampaignState(current_year=2000)
        self.assertEqual(build_vehicle(campaign, self.entry(), 100).turns_total, 1)

    def test_advanced_engine_or_aero_increases_complexity_on_a_simple_frame(self):
        from engines import ALL_ENGINES
        from research import AERODYNAMICS_TECHNOLOGY_TREE

        entry = self.entry()
        entry.engine_name = ALL_ENGINES[-1].name
        self.assertEqual(vehicle_construction_complexity(entry), 5)
        entry.engine_name = PIONEER_SINGLE_CYLINDER.name
        entry.aerodynamics_technology = (AERODYNAMICS_TECHNOLOGY_TREE[-1].technology_id,)
        self.assertEqual(vehicle_construction_complexity(entry), 5)

    def test_unfinished_car_cannot_be_run_or_serviced(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from management import fit_trackside_tyres
        from tracks import PUBLIC_ROADS
        from ui.app import BonnevilleApp

        campaign = CampaignState()
        project = build_vehicle(campaign, self.entry(), 100)
        app = SimpleNamespace(campaign=campaign, garage_return_required=False)
        for official in (False, True):
            with self.subTest(official=official), patch("ui.app.messagebox.showerror") as error:
                BonnevilleApp.execute_run(app, project.vehicle, PUBLIC_ROADS, record_attempt=official)
                self.assertEqual(error.call_args.args[0], "Vehicle under construction")
        with self.assertRaisesRegex(ValueError, "not in the active garage"):
            fit_trackside_tyres(campaign, project.vehicle)

    def test_queued_names_are_reserved_and_unaffordable_build_is_not_queued(self):
        from management import next_vehicle_name

        campaign = CampaignState()
        build_vehicle(campaign, self.entry("Bonneville Special 01"), 1_000)
        self.assertEqual(next_vehicle_name(campaign), "Bonneville Special 2")
        with self.assertRaisesRegex(ValueError, "name is already"):
            build_vehicle(campaign, self.entry("bonneville special 01"), 1_000)
        with self.assertRaisesRegex(ValueError, "insufficient funds"):
            build_vehicle(campaign, self.entry("Another Car"), 1_000_000)
        self.assertEqual(len(campaign.vehicle_construction), 1)
        self.assertEqual(campaign.team.cash, 99_000)


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
