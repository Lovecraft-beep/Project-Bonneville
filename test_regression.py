"""Broader regression coverage across Project Bonneville's systems.

Complements test_gearbox.py (shift-logic edge cases) and test_compatibility.py
(full car/engine/gearbox/track simulation matrix) by exercising the
management, research, garage reconstruction, sponsorship, save/load, and
historical challenge systems that aren't covered elsewhere.
"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import records
from brakes import BRAKE_BY_NAME
from brakes import available_brakes
from cars import AVAILABLE_CARS
from chassis import CHASSIS_BY_ID
from diagnostics import (
    create_engineering_report,
    diagnose_run,
    suggest_gear_ratio_adjustment,
)
from engines import (
    ALL_ENGINES,
    ENGINE_TUNE_STAGES,
    NAPIER_LION,
    PIONEER_SINGLE_CYLINDER,
    next_engine_tune_stage,
    tune_engine,
)
from gearbox import PREBUILT_GEARBOXES, TRANSMISSION_CATALOG
from historical_challenges import CHALLENGES, simulate_challenge
from historical_records import HISTORICAL_TARGETS, next_historical_target
from management import (
    CampaignState,
    GarageVehicle,
    Team,
    advance_turn,
    adjust_vehicle_ratio_trackside,
    build_vehicle,
    calculate_run_cost,
    complete_run,
    fit_trackside_tyres,
    MAX_TESTS_PER_SESSION,
    hire_engineer,
    load_campaign,
    next_vehicle_name,
    retire_vehicle,
    reset_campaign,
    register_test_run,
    save_campaign,
    sign_sponsor,
    start_engineering_project,
)
from research import (
    AERODYNAMICS_TECHNOLOGY_TREE,
    CHASSIS_TECHNOLOGY_TREE,
    ENGINE_TECHNOLOGY_TREE,
    available_aerodynamics_technologies,
    available_brake_technologies,
    available_chassis_technologies,
    available_engine_technologies,
    available_tyre_technologies,
    current_chassis_era,
)
from reliability import calculate_failure_probability
from simulation import run_simulation
from sponsors import SPONSOR_CATALOG
from tracks import BONNEVILLE_SALT_FLATS, PUBLIC_ROADS, available_tracks
from vehicle_designer import (
    build_vehicle_from_garage_entry,
    apply_engine_tune,
)


def complete_engineering_project(campaign, branch, technology_id):
    project = start_engineering_project(campaign, branch, technology_id)
    while project in campaign.engineering_projects:
        advance_turn(campaign)

# A measured-mile speed above this is a sign of a bug (e.g. the "measured
# mile never reached" divide-by-zero regression), not a legitimately fast car.
IMPLAUSIBLE_SPEED_MPH = 2_000.0


class RunCostTests(unittest.TestCase):
    def test_public_road_run_cost_is_venue_fee_only(self):
        self.assertEqual(calculate_run_cost(PUBLIC_ROADS), 200)


class TestSessionTests(unittest.TestCase):
    def test_eight_hourly_tests_fit_one_session_and_advance_resets_it(self):
        campaign = CampaignState()
        for expected_count in range(1, MAX_TESTS_PER_SESSION + 1):
            self.assertEqual(register_test_run(campaign), expected_count)
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "campaign_state.json"
            save_campaign(campaign, path)
            campaign = load_campaign(path)
        self.assertEqual(campaign.tests_this_session, MAX_TESTS_PER_SESSION)
        with self.assertRaisesRegex(ValueError, "session is full"):
            register_test_run(campaign)

        advance_turn(campaign, days=0)

        self.assertEqual(campaign.tests_this_session, 0)


class VehicleNamingTests(unittest.TestCase):
    def test_name_defaults_follow_first_vehicle_and_skip_existing_names(self):
        campaign = CampaignState()
        self.assertEqual(next_vehicle_name(campaign), "Bonneville Special 01")
        campaign.garage.vehicles.append(
            GarageVehicle("Bluebird", "chassis", "engine", "gearbox", "brakes")
        )
        self.assertEqual(next_vehicle_name(campaign), "Bluebird 2")
        campaign.garage.vehicles.append(
            GarageVehicle("Bluebird 3", "chassis", "engine", "gearbox", "brakes")
        )
        self.assertEqual(next_vehicle_name(campaign), "Bluebird 4")

    def test_vehicle_builder_trims_names_and_rejects_duplicates(self):
        from ui.app import BonnevilleApp

        campaign = CampaignState()
        campaign.garage.vehicles.append(
            GarageVehicle("Bluebird", "chassis", "engine", "gearbox", "brakes")
        )
        app = SimpleNamespace(
            campaign=campaign,
            finish_vehicle_build=Mock(),
        )
        with patch("ui.app.messagebox.showerror") as show_error:
            BonnevilleApp.confirm_vehicle_name(app, "  bluebird  ")
            app.finish_vehicle_build.assert_not_called()
            show_error.assert_called_once()

        BonnevilleApp.confirm_vehicle_name(app, "  Bluebird 2  ")
        app.finish_vehicle_build.assert_called_once_with("Bluebird 2")


class EngineTuningTests(unittest.TestCase):
    def _garage_entry(self, stage=0):
        return GarageVehicle(
            vehicle_name="Tune Test",
            chassis_id=CHASSIS_TECHNOLOGY_TREE[5].technology_id,
            engine_name=NAPIER_LION.name,
            gearbox_name=TRANSMISSION_CATALOG[2].name,
            brakes_name="1920s mechanical drum brakes",
            engine_tune_stage=stage,
        )

    def test_each_stage_trades_reliability_for_power(self):
        previous = tune_engine(NAPIER_LION, 0)
        for stage in range(1, len(ENGINE_TUNE_STAGES)):
            tuned = tune_engine(NAPIER_LION, stage)
            self.assertGreater(tuned.power_hp, previous.power_hp)
            self.assertGreater(tuned.torque_nm, previous.torque_nm)
            self.assertLess(tuned.reliability, previous.reliability)
            previous = tuned
    def test_maximum_tune_stage_has_no_next_stage(self):
        self.assertEqual(next_engine_tune_stage(0), 1)
        self.assertIsNone(next_engine_tune_stage(len(ENGINE_TUNE_STAGES) - 1))

    def test_garage_does_not_offer_another_tune_at_stage_three(self):
        from ui.app import BonnevilleApp

        app = SimpleNamespace(
            campaign=CampaignState(),
            body=Mock(),
            show_page=Mock(),
            page_title=Mock(),
            card=Mock(return_value=Mock()),
            section=Mock(),
            action_button=Mock(),
        )
        scroll_area = Mock()
        container = Mock()
        page = Mock()
        app.body.winfo_children.return_value = [scroll_area]
        scroll_area.winfo_children.return_value = [container]
        container.winfo_children.return_value = [page]

        with patch("ui.app.tk.Frame"), patch("ui.app.tk.Label"):
            BonnevilleApp.open_garage_vehicle(app, self._garage_entry(stage=3))

        tune_labels = [
            call.args[1]
            for call in app.action_button.call_args_list
            if call.args[1].startswith("Tune engine:")
        ]
        self.assertEqual(tune_labels, [])

    def test_tuning_does_not_mutate_catalogue_engine(self):
        stock_power = NAPIER_LION.power_hp
        stock_reliability = NAPIER_LION.reliability
        tune_engine(NAPIER_LION, 3)
        self.assertEqual(NAPIER_LION.power_hp, stock_power)
        self.assertEqual(NAPIER_LION.reliability, stock_reliability)

    def test_reliability_never_drops_below_floor(self):
        tuned = tune_engine(PIONEER_SINGLE_CYLINDER, 3)
        self.assertGreaterEqual(tuned.reliability, 0.05)

    def test_retuning_is_based_on_stock_not_compounded(self):
        vehicle = build_vehicle_from_garage_entry(self._garage_entry())
        apply_engine_tune(vehicle, 3)
        apply_engine_tune(vehicle, 1)
        self.assertEqual(vehicle.engine.power_hp, tune_engine(NAPIER_LION, 1).power_hp)
        self.assertEqual(vehicle.power, vehicle.engine.power_hp)

    def test_garage_rebuild_restores_tune_stage(self):
        vehicle = build_vehicle_from_garage_entry(self._garage_entry(stage=2))
        self.assertEqual(vehicle.engine_tune_stage, 2)
        self.assertEqual(vehicle.engine.power_hp, tune_engine(NAPIER_LION, 2).power_hp)

    def test_tuned_engine_is_faster_and_riskier(self):
        stock = build_vehicle_from_garage_entry(self._garage_entry())
        tuned = build_vehicle_from_garage_entry(self._garage_entry(stage=3))
        track = BONNEVILLE_SALT_FLATS
        results = [
            run_simulation(
                vehicle,
                track_miles=track.length_miles,
                measured_mile_start=track.measured_mile_start,
                track_friction_factor=track.friction_factor,
                air_density_kg_m3=track.air_density_kg_m3,
            )
            for vehicle in (stock, tuned)
        ]
        self.assertGreater(
            results[1].measured_mile_speed_mph, results[0].measured_mile_speed_mph
        )
        team = Team()
        self.assertGreater(
            calculate_failure_probability(tuned.engine, 200.0, team),
            calculate_failure_probability(stock.engine, 200.0, team),
        )


class TracksideServiceTests(unittest.TestCase):
    def _garage_entry(self):
        return GarageVehicle(
            vehicle_name="Trackside Test",
            chassis_id=CHASSIS_TECHNOLOGY_TREE[5].technology_id,
            engine_name=NAPIER_LION.name,
            gearbox_name=TRANSMISSION_CATALOG[2].name,
            brakes_name="1920s mechanical drum brakes",
        )

    def test_gear_and_tyre_adjustments_persist_for_five_without_advancing_turn(self):
        campaign = CampaignState()
        entry = self._garage_entry()
        campaign.garage.vehicles.append(entry)
        starting_cash = campaign.team.cash
        starting_turn = campaign.turn_number
        original = build_vehicle_from_garage_entry(entry)

        adjust_vehicle_ratio_trackside(campaign, entry, None, -0.1)
        fit_trackside_tyres(campaign, entry)

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "campaign_state.json"
            save_campaign(campaign, path)
            loaded = load_campaign(path)
        rebuilt = build_vehicle_from_garage_entry(loaded.garage.vehicles[0])
        self.assertAlmostEqual(
            rebuilt.gearbox.final_drive_ratio,
            original.gearbox.final_drive_ratio - 0.1,
        )
        self.assertAlmostEqual(
            rebuilt.tyre_grip_factor, original.tyre_grip_factor + 0.03
        )
        self.assertEqual(loaded.team.cash, starting_cash - 10.0)
        self.assertEqual(loaded.turn_number, starting_turn)

    def test_mechanic_suggests_lengthening_final_drive_near_redline(self):
        vehicle = AVAILABLE_CARS["1"]()
        vehicle.gearbox.gears = (3.0, 2.0)
        result = SimpleNamespace(
            telemetry=[
                SimpleNamespace(
                    speed_mph=100.0,
                    engine_rpm=int(vehicle.engine.max_rpm * 0.95),
                    gear=2,
                    wheelspin=False,
                )
            ],
            average_acceleration_g=0.2,
            wheelspin_event_count=0,
        )

        suggestion = suggest_gear_ratio_adjustment(vehicle, result)

        self.assertEqual(suggestion.gear_index, None)
        self.assertEqual(suggestion.delta, -0.1)
        self.assertIn("Lengthen the final drive", suggestion.description)

    def test_trackside_screen_offers_ratio_steps_and_another_test(self):
        from ui.app import BonnevilleApp

        entry = self._garage_entry()
        vehicle = build_vehicle_from_garage_entry(entry)
        app = BonnevilleApp.__new__(BonnevilleApp)
        app.campaign = CampaignState()
        app.last_run_is_sandbox = False
        app.last_vehicle_entry = entry
        app.last_vehicle = vehicle
        app.last_result = SimpleNamespace(
            telemetry=[
                SimpleNamespace(
                    speed_mph=10.0,
                    engine_rpm=100,
                    gear=1,
                    wheelspin=False,
                )
            ],
            average_acceleration_g=0.2,
            wheelspin_event_count=0,
        )
        app.last_track = PUBLIC_ROADS
        app.last_trackside_ratio_adjusted = False
        app.scroll_area = Mock(return_value=Mock())
        app.page_title = Mock()
        app.section = Mock()
        app.action_button = Mock()

        with (
            patch("ui.app.tk.Frame"),
            patch("ui.app.tk.Label"),
            patch("ui.app.tk.Button") as button,
        ):
            BonnevilleApp.render_trackside_modifications(app)

        action_labels = [call.args[1] for call in app.action_button.call_args_list]
        self.assertTrue(any("RUN ANOTHER TEST HERE" in label for label in action_labels))
        self.assertTrue(any("APPLY SUGGESTION" in label for label in action_labels))
        ratio_steps = {call.kwargs["text"] for call in button.call_args_list}
        self.assertTrue({"-0.1", "+0.1"}.issubset(ratio_steps))


class PresetVehicleRegressionTests(unittest.TestCase):
    def test_all_preset_cars_simulate_without_crashing(self):
        for car_key, factory in AVAILABLE_CARS.items():
            vehicle = factory()
            result = run_simulation(
                vehicle,
                track_miles=BONNEVILLE_SALT_FLATS.length_miles,
                measured_mile_start=BONNEVILLE_SALT_FLATS.measured_mile_start,
                track_friction_factor=BONNEVILLE_SALT_FLATS.friction_factor,
                air_density_kg_m3=BONNEVILLE_SALT_FLATS.air_density_kg_m3,
            )
            self.assertGreaterEqual(result.peak_speed_mph, 0.0, car_key)
            self.assertLess(
                result.measured_mile_speed_mph, IMPLAUSIBLE_SPEED_MPH, car_key
            )


class ResearchProjectSetupTests(unittest.TestCase):
    def _research_app(self, campaign):
        from ui.app import BonnevilleApp

        app = BonnevilleApp.__new__(BonnevilleApp)
        app.campaign = campaign
        app.research_branch = "Engine"
        return app

    def test_only_aerodynamics_tab_is_available_at_campaign_start(self):
        app = self._research_app(CampaignState())
        self.assertTrue(app._research_branch_available("Aerodynamics"))
        for branch in ("Engine", "Chassis", "Gearbox", "Tyres", "Brakes"):
            self.assertFalse(app._research_branch_available(branch), branch)

    def test_research_tabs_follow_completed_prerequisites(self):
        campaign = self._pioneer_aero_campaign()
        app = self._research_app(campaign)
        self.assertTrue(app._research_branch_available("Chassis"))
        self.assertFalse(app._research_branch_available("Engine"))
        complete_engineering_project(campaign, "chassis", "carriage_frame")
        for branch in ("Chassis", "Engine", "Tyres", "Brakes"):
            self.assertTrue(app._research_branch_available(branch), branch)
        self.assertFalse(app._research_branch_available("Gearbox"))

    def test_active_project_and_resource_shortages_do_not_grey_unlocked_branch(self):
        campaign = CampaignState()
        start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        campaign.team.cash = 0
        app = self._research_app(campaign)
        self.assertEqual(campaign.available_engineers, 0)
        self.assertTrue(app._research_branch_available("Aerodynamics"))

    def test_fully_researched_branch_has_no_available_projects(self):
        campaign = CampaignState()
        campaign.research.engine_technology = [
            node.technology_id for node in ENGINE_TECHNOLOGY_TREE
        ]
        app = self._research_app(campaign)
        self.assertFalse(app._research_branch_available("Engine"))

    def _pioneer_aero_campaign(self):
        campaign = CampaignState()
        for node in AERODYNAMICS_TECHNOLOGY_TREE[:3]:
            complete_engineering_project(campaign, "aerodynamics", node.technology_id)
        return campaign

    def test_starting_team_can_complete_opening_path(self):
        campaign = self._pioneer_aero_campaign()
        complete_engineering_project(campaign, "chassis", "carriage_frame")
        complete_engineering_project(campaign, "engine", "pioneer_engines")
        self.assertEqual(campaign.team.engineers, 1)
        self.assertGreater(campaign.team.cash, 0)

class EngineeringDiagnosisTests(unittest.TestCase):
    def test_campaign_runs_open_debrief_and_failed_runs_do_not_save_records(self):
        from reliability import MISFIRE, RunOutcome
        from ui.app import BonnevilleApp

        vehicle = AVAILABLE_CARS["1"]()
        result = SimpleNamespace(
            telemetry=[SimpleNamespace(brake_fade=False, gear=2)],
            wheelspin_event_count=0, average_acceleration_g=0.2,
            maximum_brake_temperature_c=100.0, peak_speed_mph=112.4,
            measured_mile_speed_mph=100.0,
        )
        for failed in (False, True):
            with self.subTest(failed=failed):
                app = SimpleNamespace(
                    campaign=CampaignState(), last_report=None,
                    show_page=Mock(), advance_campaign_turn=Mock(),
                )
                outcome = RunOutcome(0.25, failed, False, MISFIRE if failed else None)
                with (
                    patch("ui.app.build_vehicle_from_garage_entry", return_value=vehicle),
                    patch("ui.app.messagebox.askyesno", return_value=True),
                    patch("ui.app.run_simulation", return_value=result),
                    patch("ui.app.resolve_run_failure", return_value=outcome),
                    patch("ui.app.append_run_log"),
                    patch("ui.app.save_campaign"),
                    patch("ui.app.create_record"),
                    patch("ui.app.save_record") as save_record,
                ):
                    BonnevilleApp.execute_run(app, object(), PUBLIC_ROADS)
                app.show_page.assert_called_once_with("Team Debrief")
                app.advance_campaign_turn.assert_not_called()
                self.assertEqual(app.campaign.tests_this_session, 1)
                self.assertEqual(app.last_report.completed, not failed)
                self.assertFalse(app.last_run_is_sandbox)
                self.assertEqual(save_record.call_count, 0 if failed else 1)
                self.assertIsNone(app.last_record_message)

    def test_facility_run_opens_debrief_without_changing_campaign(self):
        from ui.app import BonnevilleApp

        app = SimpleNamespace(
            last_report=None, show_page=Mock(), campaign=CampaignState(),
        )
        starting_cash = app.campaign.team.cash
        with patch("ui.app.run_simulation") as simulate, patch("ui.app.append_run_log"):
            simulate.return_value = SimpleNamespace(
                telemetry=[SimpleNamespace(brake_fade=False, gear=2)],
                wheelspin_event_count=0, average_acceleration_g=0.2,
                maximum_brake_temperature_c=100.0, peak_speed_mph=112.4,
                measured_mile_speed_mph=100.0,
            )
            BonnevilleApp.run_facility_test(app, AVAILABLE_CARS["1"](), PUBLIC_ROADS)
        app.show_page.assert_called_once_with("Team Debrief")
        self.assertTrue(app.last_run_is_sandbox)
        self.assertIsNotNone(app.last_report)
        self.assertEqual(app.campaign.team.cash, starting_cash)

    def _report(self, campaign=None, **kwargs):
        vehicle = AVAILABLE_CARS["1"]()
        result = SimpleNamespace(
            telemetry=[SimpleNamespace(brake_fade=False, gear=2)],
            wheelspin_event_count=0, average_acceleration_g=0.2,
            maximum_brake_temperature_c=100.0, peak_speed_mph=112.4,
            measured_mile_speed_mph=100.0,
        )
        return create_engineering_report(vehicle, PUBLIC_ROADS, result, campaign, **kwargs)

    def test_report_contains_evidence_and_feasible_opening_research(self):
        campaign = CampaignState()
        report = self._report(campaign)
        self.assertEqual(report.diagnosis.problem, "Aerodynamic drag")
        self.assertIn("112.4 mph", report.diagnosis.evidence)
        self.assertIn("Research Wind Deflector", report.recommendations[0])
        self.assertEqual(report.research_branch, "Aerodynamics")
        self.assertEqual(len(report.recommendations), 3)
        self.assertEqual(campaign.engineering_projects, [])

    def test_report_research_advice_tracks_project_and_resource_state(self):
        campaign = CampaignState()
        campaign.team.cash = 0
        self.assertIn("raise GBP", self._report(campaign).recommendations[0])
        campaign.team.cash = 100_000
        start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        self.assertIn("3 turn(s) remaining", self._report(campaign).recommendations[0])

    def test_report_handles_staffing_locked_and_completed_research(self):
        campaign = CampaignState()
        campaign.team.engineers = 0
        self.assertIn("free 1 engineer", self._report(campaign).recommendations[0])
        campaign.research.aerodynamics_technology = [
            node.technology_id for node in AERODYNAMICS_TECHNOLOGY_TREE[:3]
        ]
        self.assertIn("first research", self._report(campaign).recommendations[0])
        campaign.research.aerodynamics_technology = [
            node.technology_id for node in AERODYNAMICS_TECHNOLOGY_TREE
        ]
        self.assertIn("installation", self._report(campaign).recommendations[0])

    def test_failed_run_is_not_used_as_a_comparison_baseline(self):
        from reliability import MISFIRE, RunOutcome

        previous = self._report(outcome=RunOutcome(0.25, True, False, MISFIRE))
        self.assertIn("No comparable", self._report(previous_report=previous).comparison)

    def test_report_comparison_requires_same_vehicle_and_venue(self):
        previous = self._report()
        self.assertIn("+0.0 mph", self._report(previous_report=previous).comparison)
        from dataclasses import replace

        for other in (replace(previous, track_name="Other venue"), replace(previous, vehicle_name="Other car")):
            self.assertIn("No comparable", self._report(previous_report=other).comparison)

    def test_failed_report_overrides_performance_and_record_readiness(self):
        from reliability import GEAR_FAILURE, RunOutcome

        outcome = RunOutcome(0.25, True, False, GEAR_FAILURE)
        report = self._report(CampaignState(), outcome=outcome, previous_report=self._report())
        self.assertFalse(report.completed)
        self.assertEqual(report.diagnosis.problem, "Gear failure")
        self.assertEqual(report.research_branch, "Gearbox")
        self.assertIn("Workshop repair", report.diagnosis.evidence)
        self.assertIn("not a valid", report.comparison)
        self.assertIn("No record credited", report.target_assessment)

    def test_test_pace_does_not_claim_an_official_record(self):
        target = SimpleNamespace(year=1898, vehicle="Benchmark", speed_mph=90.0)
        test_report = self._report(CampaignState(), target=target)
        self.assertIn("Schedule an official", test_report.target_assessment)
        record_report = self._report(CampaignState(), target=target, is_record_attempt=True)
        self.assertIn("benchmark beaten", record_report.target_assessment)

    def _diagnose(self, vehicle, **result_values):
        result_data = {
            "telemetry": [],
            "wheelspin_event_count": 0,
            "average_acceleration_g": 0.2,
            "maximum_brake_temperature_c": 100.0,
            "peak_speed_mph": 100.0,
        }
        result_data.update(result_values)
        result = SimpleNamespace(**result_data)
        return diagnose_run(vehicle, result)

    def test_diagnosis_prioritises_brake_fade(self):
        vehicle = AVAILABLE_CARS["1"]()
        sample = SimpleNamespace(brake_fade=True, gear=1)
        diagnosis = self._diagnose(
            vehicle,
            telemetry=[sample],
            maximum_brake_temperature_c=300.0,
            wheelspin_event_count=1,
        )
        self.assertEqual(diagnosis.recommended_component, "brakes")

    def test_diagnosis_identifies_traction_loss(self):
        vehicle = AVAILABLE_CARS["1"]()
        diagnosis = self._diagnose(vehicle, wheelspin_event_count=2)
        self.assertEqual(diagnosis.research_branch, "tyre technology")

    def test_diagnosis_identifies_first_gear_limit(self):
        vehicle = AVAILABLE_CARS["1"]()
        diagnosis = self._diagnose(
            vehicle,
            telemetry=[SimpleNamespace(brake_fade=False, gear=1)],
        )
        self.assertEqual(diagnosis.recommended_component, "gearbox")

    def test_all_engines_torque_curve_across_rpm_range(self):
        for engine in ALL_ENGINES:
            for rpm in (0, engine.max_rpm // 2, engine.max_rpm, engine.max_rpm + 500):
                torque = engine.torque_at_rpm(rpm)
                self.assertGreaterEqual(torque, 0.0, engine.name)

    def test_chassis_and_gearbox_catalogs_are_well_formed(self):
        for chassis in CHASSIS_BY_ID.values():
            self.assertGreater(chassis.mass_kg, 0)
            self.assertGreater(chassis.wheel_radius_m, 0)
        for gearbox in PREBUILT_GEARBOXES + TRANSMISSION_CATALOG:
            self.assertGreater(gearbox.gear_count, 0)
            self.assertGreater(gearbox.final_drive, 0)


class HistoricalChallengeRegressionTests(unittest.TestCase):
    def test_all_historical_challenges_run_without_crashing(self):
        for challenge in CHALLENGES:
            _, result = simulate_challenge(challenge)
            self.assertLess(
                result.measured_mile_speed_mph, IMPLAUSIBLE_SPEED_MPH, challenge.name
            )

    def test_major_record_dataset_is_sequentially_available(self):
        self.assertEqual(len(HISTORICAL_TARGETS), 40)
        first_target = next_historical_target(1895, [])
        self.assertEqual(first_target.record_id, "jeantaud_1898")
        next_target = next_historical_target(1898, [first_target.record_id])
        self.assertEqual(next_target.record_id, "jenatzy_dogcart_1899")

    def test_campaign_run_completes_current_historical_target(self):
        campaign = CampaignState(current_year=1898)
        complete_run(
            campaign,
            0.0,
            HISTORICAL_TARGETS[0].speed_mph,
            is_record_attempt=True,
        )
        self.assertEqual(
            campaign.completed_historical_record_ids,
            ["jeantaud_1898"],
        )
        self.assertIn("RECORD BEATEN:", campaign.world.headlines[-1])
        self.assertEqual(campaign.team.reputation, 3.0)

    def test_fast_record_attempt_skips_all_targets_at_or_below_speed(self):
        campaign = CampaignState(current_year=1898)
        speed = HISTORICAL_TARGETS[5].speed_mph

        complete_run(campaign, 0.0, speed, is_record_attempt=True)

        self.assertEqual(
            campaign.completed_historical_record_ids,
            [
                target.record_id
                for target in HISTORICAL_TARGETS
                if target.speed_mph <= speed
            ],
        )
        self.assertEqual(
            campaign.team.reputation,
            2.0
            + len(campaign.completed_historical_record_ids),
        )
        next_target = next_historical_target(
            campaign.current_year, campaign.completed_historical_record_ids
        )
        self.assertGreater(next_target.speed_mph, speed)

    def test_early_campaign_catalogs_reflect_historical_limits(self):
        self.assertEqual(
            [track.name for track in available_tracks(1895).values()],
            ["Public Roads"],
        )
        self.assertEqual(
            [brake.name for brake in available_brakes(1895)],
            ["Wooden block brakes"],
        )
        self.assertEqual(PIONEER_SINGLE_CYLINDER.power_hp, 24.0)
        self.assertLess(PIONEER_SINGLE_CYLINDER.reliability, 0.5)

    def test_test_run_does_not_complete_historical_target(self):
        campaign = CampaignState(current_year=1898)
        complete_run(campaign, 0.0, HISTORICAL_TARGETS[0].speed_mph)
        self.assertEqual(campaign.completed_historical_record_ids, [])


class CampaignProgressionRegressionTests(unittest.TestCase):
    def test_aerodynamics_is_the_initial_research_path(self):
        campaign = CampaignState()
        available_aero = available_aerodynamics_technologies(
            campaign.research.aerodynamics_technology,
            campaign.research.chassis_technology,
        )
        self.assertEqual(available_aero[0].technology_id, "wind_deflector")
        self.assertEqual(
            available_chassis_technologies(
                campaign.research.chassis_technology,
                campaign.research.aerodynamics_technology,
            ),
            (),
        )
        self.assertEqual(
            available_engine_technologies(
                campaign.research.engine_technology,
                campaign.research.chassis_technology,
            ),
            (),
        )
        self.assertEqual(
            available_tyre_technologies(
                campaign.research.tyre_technology,
                campaign.research.chassis_technology,
            ),
            (),
        )
        self.assertEqual(
            available_brake_technologies(
                campaign.research.brake_technology,
                campaign.research.chassis_technology,
            ),
            (),
        )

    def test_runs_advance_days_without_moving_to_next_year(self):
        campaign = CampaignState(current_year=1895)
        advance_turn(campaign, days=7)
        self.assertEqual(campaign.current_year, 1895)
        self.assertEqual(campaign.current_day_of_year, 8)

    def test_planning_turn_rolls_year_and_updates_world(self):
        campaign = CampaignState(current_year=1926, current_day_of_year=360)
        advance_turn(campaign)
        self.assertEqual(campaign.current_year, 1927)
        self.assertEqual(campaign.current_day_of_year, 360)
        self.assertTrue(campaign.world.reactions)

    def test_world_progression_creates_events_rivals_and_reactions(self):
        campaign = CampaignState(current_year=1926)
        campaign.best_measured_mile_speed_mph = 180.0
        advance_turn(campaign)
        self.assertTrue(campaign.world.headlines)
        self.assertTrue(campaign.world.reactions)
        self.assertTrue(any(rival.best_speed_mph > 0 for rival in campaign.world.rivals))

    def test_full_research_tree_and_garage_vehicle_build(self):
        campaign = CampaignState()
        campaign.team.cash = 10_000_000.0
        campaign.team.engineers = 10

        for node in AERODYNAMICS_TECHNOLOGY_TREE[:3]:
            complete_engineering_project(campaign, "aerodynamics", node.technology_id)
        for node in CHASSIS_TECHNOLOGY_TREE:
            complete_engineering_project(campaign, "chassis", node.technology_id)
        while True:
            available_aero = available_aerodynamics_technologies(
                campaign.research.aerodynamics_technology,
                campaign.research.chassis_technology,
            )
            if not available_aero:
                break
            complete_engineering_project(
                campaign, "aerodynamics", available_aero[0].technology_id
            )
        for node in ENGINE_TECHNOLOGY_TREE:
            complete_engineering_project(campaign, "engine", node.technology_id)
        self.assertEqual(
            current_chassis_era(campaign.research.chassis_technology),
            "Modern and Future Speed",
        )

        chassis_id = campaign.research.chassis_technology[-1]
        engine = ALL_ENGINES[-1]
        gearbox = TRANSMISSION_CATALOG[0]
        brakes_name = "Carbon-carbon brakes"
        garage_entry = GarageVehicle(
            vehicle_name="Regression Car",
            chassis_id=chassis_id,
            engine_name=engine.name,
            gearbox_name=gearbox.name,
            brakes_name=brakes_name,
            aerodynamics_technology=tuple(
                campaign.research.aerodynamics_technology
            ),
            gearbox_ratios=tuple(gearbox.gears),
            gearbox_final_drive=gearbox.final_drive_ratio,
        )
        chassis = CHASSIS_BY_ID[chassis_id]
        brakes = BRAKE_BY_NAME[brakes_name]
        cost_gbp = round(
            chassis.cost_gbp
            + engine.purchase_cost_gbp
            + gearbox.cost_gbp
            + brakes.cost_gbp
        )
        build_vehicle(campaign, garage_entry, cost_gbp)
        self.assertEqual(len(campaign.garage.vehicles), 1)

        rebuilt = build_vehicle_from_garage_entry(garage_entry)
        self.assertEqual(rebuilt.name, "Regression Car")
        expected_mass = (
            chassis.mass_kg
            + rebuilt.engine.mass_kg
            + rebuilt.gearbox.mass_kg
            + brakes.mass_kg
        )
        self.assertEqual(rebuilt.mass, expected_mass)

        replacement_engine = ALL_ENGINES[1]
        mass_before_engine_change = rebuilt.mass
        rebuilt.engine = replacement_engine
        self.assertEqual(
            rebuilt.mass,
            mass_before_engine_change - engine.mass_kg + replacement_engine.mass_kg,
        )

        mass_before_gearbox_change = rebuilt.mass
        replacement_gearbox = TRANSMISSION_CATALOG[1]
        rebuilt.gearbox = replacement_gearbox
        self.assertEqual(
            rebuilt.mass,
            mass_before_gearbox_change
            - gearbox.mass_kg
            + replacement_gearbox.mass_kg,
        )

    def test_sponsorship_signing_and_duplicate_rejection(self):
        campaign = CampaignState()
        campaign.team.reputation = 20.0
        for sponsor in SPONSOR_CATALOG:
            sign_sponsor(campaign, sponsor.sponsor_id)
        self.assertEqual(
            len(campaign.sponsorship.active_sponsors), len(SPONSOR_CATALOG)
        )
        with self.assertRaises(ValueError):
            sign_sponsor(campaign, SPONSOR_CATALOG[0].sponsor_id)

    def test_campaign_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "campaign_state.json"
            campaign = CampaignState()
            hire_engineer(campaign)
            save_campaign(campaign, path)
            loaded = load_campaign(path)
            self.assertEqual(loaded.team.engineers, campaign.team.engineers)
            self.assertEqual(loaded.campaign_id, campaign.campaign_id)
            self.assertEqual(len(loaded.world.rivals), len(campaign.world.rivals))

    def test_retired_vehicle_moves_to_persistent_museum(self):
        campaign = CampaignState()
        vehicle = GarageVehicle(
            vehicle_name="Museum Test",
            chassis_id=CHASSIS_TECHNOLOGY_TREE[0].technology_id,
            engine_name=ALL_ENGINES[0].name,
            gearbox_name=TRANSMISSION_CATALOG[0].name,
            brakes_name="1890s steel shoes",
        )
        campaign.garage.vehicles.append(vehicle)

        retire_vehicle(campaign, vehicle)

        self.assertEqual(campaign.garage.vehicles, [])
        self.assertEqual(campaign.garage.museum, [vehicle])
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "campaign_state.json"
            save_campaign(campaign, path)
            loaded = load_campaign(path)
        self.assertEqual(loaded.garage.vehicles, [])
        self.assertEqual(len(loaded.garage.museum), 1)
        self.assertEqual(loaded.garage.museum[0].vehicle_name, vehicle.vehicle_name)

    def test_reset_campaign_clears_saved_state(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "campaign_state.json"
            campaign = CampaignState()
            save_campaign(campaign, path)
            new_campaign = reset_campaign(path)
            self.assertFalse(path.exists())
            self.assertNotEqual(new_campaign.campaign_id, campaign.campaign_id)

    def test_records_save_load_and_display_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            records_path = Path(tmp_dir) / "historical_records.json"
            with patch.object(records, "RECORDS_FILE", records_path):
                campaign = CampaignState()
                vehicle = AVAILABLE_CARS["1"]()
                track = BONNEVILLE_SALT_FLATS
                result = run_simulation(
                    vehicle,
                    track_miles=track.length_miles,
                    measured_mile_start=track.measured_mile_start,
                    track_friction_factor=track.friction_factor,
                    air_density_kg_m3=track.air_density_kg_m3,
                )
                record = records.create_record(vehicle, track, result, campaign)
                records.save_record(record)
                loaded = records.load_records()
                self.assertEqual(len(loaded), 1)
                records.display_records(loaded, campaign.campaign_id)


if __name__ == "__main__":
    unittest.main()
