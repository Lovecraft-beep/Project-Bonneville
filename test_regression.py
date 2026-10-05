"""Broader regression coverage across Project Bonneville's systems.

Complements test_gearbox.py (shift-logic edge cases) and test_compatibility.py
(full car/engine/gearbox/track simulation matrix) by exercising the
management, research, garage reconstruction, sponsorship, save/load, and
historical challenge systems that aren't covered elsewhere.
"""

import math

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
    STANLEY_STEAM_ENGINE,
    WELCH_HEMI,
    available_engines,
    next_engine_tune_stage,
    tune_engine,
)
from gearbox import PREBUILT_GEARBOXES, TRANSMISSION_CATALOG
from historical_challenges import CHALLENGES, simulate_challenge
from historical_records import (
    HISTORICAL_TARGETS,
    next_historical_target,
    required_record_runs,
)
from management import (
    CampaignState,
    GarageVehicle,
    Team,
    CampaignRecordAttempt,
    CampaignState,
    GarageVehicle,
    Team,
    advance_turn,
    adjust_vehicle_ratio_trackside,
    apply_gear_ratios_trackside,
    build_vehicle,
    calculate_run_cost,
    calculate_session_run_cost,
    complete_run,
    lapse_record_attempt_if_out_of_runs,
    MAX_RECORD_RUNS_PER_SESSION,
    register_record_run,
    session_runs_remaining,
    fit_trackside_tyres,
    fit_trackside_brakes,
    MAX_TESTS_PER_SESSION,
    mark_session_venue_paid,
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
from reliability import (
    GEAR_FAILURE,
    MISFIRE,
    TYRE_BURST,
    calculate_failure_probability,
    resolve_run_failure,
)
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

    def test_venue_fee_is_charged_once_per_session(self):
        campaign = CampaignState()
        self.assertEqual(calculate_session_run_cost(campaign, PUBLIC_ROADS), 200)
        mark_session_venue_paid(campaign, PUBLIC_ROADS)
        self.assertEqual(calculate_session_run_cost(campaign, PUBLIC_ROADS), 0)

        advance_turn(campaign, days=0)

        self.assertEqual(calculate_session_run_cost(campaign, PUBLIC_ROADS), 200)


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

    def test_record_runs_use_a_separate_session_reset_by_end_turn(self):
        campaign = CampaignState(tests_this_session=MAX_TESTS_PER_SESSION)
        for expected_count in range(1, MAX_RECORD_RUNS_PER_SESSION + 1):
            self.assertEqual(register_record_run(campaign), expected_count)
        self.assertEqual(session_runs_remaining(campaign, record=True), 0)
        with self.assertRaisesRegex(ValueError, "record session is full"):
            register_record_run(campaign)

        advance_turn(campaign, days=0)

        self.assertEqual(campaign.record_runs_this_session, 0)
        self.assertEqual(campaign.tests_this_session, 0)

    def test_attempt_lapses_only_when_return_pass_cannot_fit(self):
        campaign = CampaignState(
            record_runs_this_session=MAX_RECORD_RUNS_PER_SESSION - 1,
            record_attempt=CampaignRecordAttempt(
                "target", "Car", "Track", 1924, 2, [200.0]
            ),
        )
        self.assertFalse(lapse_record_attempt_if_out_of_runs(campaign))
        self.assertIsNotNone(campaign.record_attempt)

        register_record_run(campaign)

        self.assertTrue(lapse_record_attempt_if_out_of_runs(campaign))
        self.assertIsNone(campaign.record_attempt)


class RecordChaseTests(unittest.TestCase):
    def test_world_record_is_latest_standing_record_for_year(self):
        from historical_records import current_world_record

        self.assertIsNone(current_world_record(1895))
        record_1908 = current_world_record(1908)
        self.assertLessEqual(record_1908.year, 1908)
        self.assertTrue(
            all(
                target.speed_mph <= record_1908.speed_mph
                for target in HISTORICAL_TARGETS
                if target.year <= 1908
            )
        )

    def test_standing_record_shows_team_once_it_holds_the_record(self):
        from management import standing_world_record

        campaign = CampaignState(current_year=1899)
        historical_speed, holder, _ = standing_world_record(campaign)
        self.assertNotEqual(holder, campaign.team.name)

        campaign.official_record_mph = historical_speed + 5.0
        speed, holder, year = standing_world_record(campaign)
        self.assertEqual((speed, holder, year), (historical_speed + 5.0, campaign.team.name, 1899))

        legacy = CampaignState(
            current_year=1899,
            completed_historical_record_ids=[HISTORICAL_TARGETS[3].record_id],
        )
        self.assertEqual(standing_world_record(legacy)[1], legacy.team.name)

    def test_gap_headline_reports_short_clear_and_complete(self):
        from ui.app import record_gap_headline

        target = HISTORICAL_TARGETS[0]
        self.assertEqual(
            record_gap_headline(target, target.speed_mph - 12.0), "12.0 mph short"
        )
        self.assertIn("clear", record_gap_headline(target, target.speed_mph + 3.0))
        self.assertEqual(record_gap_headline(None, 500.0), "All records beaten")


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
        # The Napier car is grip-limited, so measure on the power-limited starting engine.
        def pioneer_entry(stage):
            entry = self._garage_entry(stage=stage)
            entry.engine_name = PIONEER_SINGLE_CYLINDER.name
            return entry

        stock = build_vehicle_from_garage_entry(pioneer_entry(0))
        tuned = build_vehicle_from_garage_entry(pioneer_entry(3))
        track = PUBLIC_ROADS
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


class FailureRepairTests(unittest.TestCase):
    def _debrief_app(self, repaired, repair_complete=False):
        return SimpleNamespace(
            scroll_area=Mock(return_value=Mock()),
            page_title=Mock(),
            section=Mock(),
            action_button=Mock(),
            show_page=Mock(),
            repair_failed_run_trackside=Mock(),
            rerun_failed_test=Mock(),
            campaign=SimpleNamespace(tests_this_session=1, record_runs_this_session=0),
            last_report=SimpleNamespace(
                vehicle_name="Failure Test",
                track_name=PUBLIC_ROADS.name,
                run_status="ABORTED",
                completed=False,
                diagnosis=SimpleNamespace(
                    problem="Mechanical failure", evidence="Failure recorded."
                ),
                recommendations=(),
                comparison="",
                target_assessment="",
                research_branch="Engine",
            ),
            last_run_note="ABORTED: Mechanical failure.",
            last_record_message=None,
            last_run_is_sandbox=False,
            last_run_outcome=SimpleNamespace(failed=True, repaired=repaired),
            last_run_repaired=repair_complete,
            last_run_was_record_attempt=False,
            last_vehicle_entry=None,
            last_result=SimpleNamespace(
                peak_speed_mph=100.0,
                measured_mile_speed_mph=95.0,
                average_acceleration_g=0.1,
                average_deceleration_g=0.1,
                maximum_brake_temperature_c=100.0,
                wheelspin_event_count=0,
            ),
        )

    def test_minor_failure_can_be_repaired_trackside(self):
        engine = SimpleNamespace(reliability=0.0)
        gearbox = SimpleNamespace(reliability=1.0)

        outcome = resolve_run_failure(
            engine, 250.0, Team(), random_value=0.0, gearbox=gearbox
        )

        self.assertEqual(outcome.failure_type, MISFIRE)
        self.assertTrue(outcome.repaired)

    def test_gearbox_failure_requires_return_to_garage(self):
        engine = SimpleNamespace(reliability=1.0)
        gearbox = SimpleNamespace(reliability=0.0)

        outcome = resolve_run_failure(
            engine, 250.0, Team(), random_value=0.01, gearbox=gearbox
        )

        self.assertEqual(outcome.failure_type, GEAR_FAILURE)
        self.assertFalse(outcome.repaired)

    def test_tyre_burst_requires_return_to_garage(self):
        engine = SimpleNamespace(reliability=1.0)
        gearbox = SimpleNamespace(reliability=1.0)
        outcome = resolve_run_failure(
            engine, 250.0, Team(), random_value=0.005, gearbox=gearbox
        )

        self.assertEqual(outcome.failure_type, TYRE_BURST)
        self.assertFalse(outcome.repaired)

    def test_minor_fault_repair_unlocks_free_rerun(self):
        from ui.app import BonnevilleApp

        app = SimpleNamespace(
            last_run_outcome=SimpleNamespace(failed=True, repaired=True),
            last_run_repaired=False,
            last_run_note="ABORTED: Misfire.",
            last_vehicle_entry=object(),
            last_track=PUBLIC_ROADS,
            last_run_was_record_attempt=True,
            show_page=Mock(),
            execute_run=Mock(),
        )

        BonnevilleApp.repair_failed_run_trackside(app)
        self.assertTrue(app.last_run_repaired)
        BonnevilleApp.rerun_failed_test(app)

        app.execute_run.assert_called_once_with(
            app.last_vehicle_entry,
            PUBLIC_ROADS,
            record_attempt=True,
            waive_venue_fee=True,
        )

    def test_major_failure_blocks_campaign_run(self):
        from ui.app import BonnevilleApp

        app = SimpleNamespace(garage_return_required=True)
        with patch("ui.app.messagebox.showerror") as show_error:
            BonnevilleApp.execute_run(app, object(), PUBLIC_ROADS)
        show_error.assert_called_once()

    def test_debrief_shows_repair_then_rerun_or_forces_garage(self):
        from ui.app import BonnevilleApp

        scenarios = (
            (True, False, ["REPAIR MINOR ISSUE AT TRACKSIDE"]),
            (True, True, ["RERUN AT NO COST"]),
            (False, False, ["RETURN TO GARAGE"]),
        )
        with patch("ui.app.tk.Label"):
            for repaired, repair_complete, expected_labels in scenarios:
                with self.subTest(expected_labels=expected_labels):
                    app = self._debrief_app(repaired, repair_complete)
                    BonnevilleApp.render_team_debrief(app)
                    labels = [
                        call.args[1]
                        for call in app.action_button.call_args_list
                    ]
                    self.assertEqual(labels, expected_labels)

    def test_repaired_record_failure_keeps_service_and_free_retry_options(self):
        from ui.app import BonnevilleApp

        attempt = CampaignRecordAttempt(
            HISTORICAL_TARGETS[0].record_id,
            "Record Test",
            PUBLIC_ROADS.name,
            1924,
            2,
            [100.0],
        )
        app = self._debrief_app(repaired=True, repair_complete=True)
        app.campaign.record_attempt = attempt
        app.last_run_was_record_attempt = True

        with patch("ui.app.tk.Label"):
            BonnevilleApp.render_team_debrief(app)

        labels = [call.args[1] for call in app.action_button.call_args_list]
        self.assertEqual(
            labels,
            ["RERUN AT NO COST", "TRACKSIDE MODIFICATIONS"],
        )


class RecordAttemptTests(unittest.TestCase):
    def test_telemetry_footer_routes_record_pass_to_trackside_maintenance(self):
        from ui.app import BonnevilleApp

        for is_record_attempt, expected_label in (
            (True, "TRACKSIDE MAINTENANCE"),
            (False, "RUN ANOTHER TEST"),
        ):
            with self.subTest(is_record_attempt=is_record_attempt):
                app = SimpleNamespace(
                    scroll_area=Mock(return_value=Mock()),
                    last_result=SimpleNamespace(
                        measured_mile_speed_mph=100.0,
                        measured_mile_time_seconds=30.0,
                        peak_speed_mph=110.0,
                        total_time_seconds=60.0,
                        average_acceleration_g=0.2,
                        gear_change_count=2,
                        maximum_brake_temperature_c=100.0,
                        wheelspin_event_count=0,
                        telemetry=[],
                    ),
                    last_vehicle=SimpleNamespace(name="Record Test"),
                    last_track=SimpleNamespace(name="Public Roads", measured_mile_start=0.0),
                    last_run_note="Completed.",
                    last_record_message=None,
                    last_run_was_record_attempt=is_record_attempt,
                    last_run_is_sandbox=False,
                    last_run_outcome=SimpleNamespace(failed=False),
                    last_run_repaired=False,
                    garage_return_required=False,
                    last_vehicle_entry=object(),
                    campaign=SimpleNamespace(record_attempt=object() if is_record_attempt else None),
                    show_page=Mock(),
                    card=Mock(return_value=Mock()),
                    section=Mock(),
                    draw_graph=Mock(),
                    action_button=Mock(),
                    page_title=Mock(),
                )
                with patch("ui.app.tk.Frame"), patch("ui.app.tk.Label"):
                    BonnevilleApp.render_telemetry(app)

                labels = [call.args[1] for call in app.action_button.call_args_list]
                if is_record_attempt:
                    self.assertEqual(labels[-1], expected_label)
                else:
                    self.assertEqual(
                        labels[-2:],
                        ["TRACKSIDE MAINTENANCE", "RUN ANOTHER TEST"],
                    )


    def test_record_pass_rules_change_in_1924_and_remain_two_pass_after_1950(self):
        self.assertEqual(required_record_runs(1895), 1)
        self.assertEqual(required_record_runs(1923), 1)
        self.assertEqual(required_record_runs(1924), 2)
        self.assertEqual(required_record_runs(1950), 2)

    def test_1950_debrief_calls_out_one_hour_turnaround(self):
        from ui.app import BonnevilleApp

        target = HISTORICAL_TARGETS[0]
        entry = GarageVehicle(
            "Record Test",
            CHASSIS_TECHNOLOGY_TREE[0].technology_id,
            NAPIER_LION.name,
            TRANSMISSION_CATALOG[2].name,
            "1920s mechanical drum brakes",
        )
        app = SimpleNamespace(
            scroll_area=Mock(return_value=Mock()),
            page_title=Mock(),
            section=Mock(),
            action_button=Mock(),
            show_page=Mock(),
            resume_record_attempt=Mock(),
            campaign=CampaignState(
                current_year=1950,
                record_attempt=CampaignRecordAttempt(
                    target.record_id,
                    entry.vehicle_name,
                    PUBLIC_ROADS.name,
                    1950,
                    2,
                    [target.speed_mph],
                ),
            ),
            last_report=SimpleNamespace(
                vehicle_name=entry.vehicle_name,
                track_name=PUBLIC_ROADS.name,
                run_status="COMPLETED",
                completed=True,
                diagnosis=SimpleNamespace(problem="Test", evidence="Evidence."),
                recommendations=(),
                comparison="",
                target_assessment="",
                research_branch="Engine",
            ),
            last_run_note="Completed.",
            last_record_message="Outbound pass recorded.",
            last_run_is_sandbox=False,
            last_vehicle_entry=None,
            last_run_outcome=SimpleNamespace(failed=False, repaired=False),
            last_run_was_record_attempt=True,
            last_result=SimpleNamespace(
                peak_speed_mph=120.0,
                measured_mile_speed_mph=target.speed_mph,
                average_acceleration_g=0.2,
                average_deceleration_g=0.2,
                maximum_brake_temperature_c=100.0,
                wheelspin_event_count=0,
            ),
        )

        with patch("ui.app.tk.Label") as label:
            BonnevilleApp.render_team_debrief(app)

        displayed_text = [
            call.kwargs.get("text", "") for call in label.call_args_list
        ]
        self.assertTrue(
            any("one-hour test slot" in text for text in displayed_text)
        )
        action_labels = [call.args[1] for call in app.action_button.call_args_list]
        self.assertIn("START RETURN RUN / OPPOSITE DIRECTION", action_labels)

    def test_1924_attempt_requires_return_and_credits_only_the_average(self):
        from ui.app import BonnevilleApp

        target = HISTORICAL_TARGETS[0]
        campaign = CampaignState(current_year=1924)
        entry = GarageVehicle(
            "Record Test",
            CHASSIS_TECHNOLOGY_TREE[0].technology_id,
            NAPIER_LION.name,
            TRANSMISSION_CATALOG[2].name,
            "1920s mechanical drum brakes",
        )
        campaign.garage.vehicles.append(entry)
        vehicle = AVAILABLE_CARS["1"]()
        outcome = SimpleNamespace(failed=False, repaired=False)
        report = SimpleNamespace(
            vehicle_name=entry.vehicle_name,
            track_name=PUBLIC_ROADS.name,
            run_status="COMPLETED",
            completed=True,
            diagnosis=SimpleNamespace(problem="Test", evidence="Evidence."),
            recommendations=(),
            research_branch="Engine",
            comparison="",
            target_assessment="",
        )
        app = SimpleNamespace(
            campaign=campaign,
            garage_return_required=False,
            last_run_outcome=None,
            last_run_repaired=False,
            last_report=None,
            last_record_message=None,
            last_run_is_sandbox=False,
            last_vehicle_entry=None,
            last_trackside_ratio_adjusted=False,
            last_track=None,
            last_run_note="",
            last_result=None,
            last_vehicle=None,
            last_run_was_record_attempt=False,
            resume_record_attempt=Mock(),
            show_page=Mock(),
        )
        result = SimpleNamespace(
            peak_speed_mph=120.0,
            measured_mile_speed_mph=target.speed_mph + 20.0,
            average_acceleration_g=0.2,
            average_deceleration_g=0.2,
            maximum_brake_temperature_c=100.0,
            wheelspin_event_count=0,
            telemetry=[],
        )

        with (
            patch("ui.app.build_vehicle_from_garage_entry", return_value=vehicle),
            patch("ui.app.messagebox.askyesno", return_value=True),
            patch("ui.app.run_simulation", return_value=result),
            patch("ui.app.resolve_run_failure", return_value=outcome),
            patch("ui.app.append_run_log"),
            patch("ui.app.save_campaign"),
            patch("ui.app.create_record", return_value=object()),
            patch("ui.app.save_record"),
            patch("ui.app.create_engineering_report", return_value=report) as make_report,
        ):
            BonnevilleApp.execute_run(
                app,
                entry,
                PUBLIC_ROADS,
                record_attempt=True,
                record_target=target,
            )

        self.assertEqual(required_record_runs(1924), 2)
        self.assertEqual(campaign.completed_historical_record_ids, [])
        self.assertEqual(campaign.record_attempt.speeds_mph, [result.measured_mile_speed_mph])
        self.assertTrue(make_report.call_args.kwargs["record_attempt_in_progress"])
        self.assertTrue(app.last_run_was_record_attempt)
        with (
            patch("ui.app.messagebox.showerror") as show_error,
            patch("ui.app.run_simulation") as simulate,
        ):
            BonnevilleApp.execute_run(app, entry, PUBLIC_ROADS)
        show_error.assert_called_once()
        simulate.assert_not_called()

        app.last_report = report
        app.last_run_outcome = outcome
        app.last_vehicle_entry = None
        app.last_result = result
        app.section = Mock()
        app.action_button = Mock()
        app.scroll_area = Mock(return_value=Mock())
        app.page_title = Mock()
        with patch("ui.app.tk.Label"):
            BonnevilleApp.render_team_debrief(app)
        labels = [call.args[1] for call in app.action_button.call_args_list]
        self.assertIn("START RETURN RUN / OPPOSITE DIRECTION", labels)
        self.assertNotIn("PREPARE NEXT TEST", labels)

        result.measured_mile_speed_mph = target.speed_mph - 2.0
        with (
            patch("ui.app.build_vehicle_from_garage_entry", return_value=vehicle),
            patch("ui.app.messagebox.askyesno", return_value=True),
            patch("ui.app.run_simulation", return_value=result),
            patch("ui.app.resolve_run_failure", return_value=outcome),
            patch("ui.app.append_run_log"),
            patch("ui.app.save_campaign"),
            patch("ui.app.create_record", return_value=object()),
            patch("ui.app.save_record"),
            patch("ui.app.create_engineering_report", return_value=report) as make_report,
        ):
            BonnevilleApp.execute_run(
                app,
                entry,
                PUBLIC_ROADS,
                record_attempt=True,
                record_target=target,
            )

        self.assertIsNone(campaign.record_attempt)
        self.assertIn(target.record_id, campaign.completed_historical_record_ids)
        self.assertIn("Official average", app.last_record_message)
        self.assertAlmostEqual(
            make_report.call_args.kwargs["record_attempt_average_mph"],
            target.speed_mph + 9.0,
        )

    def test_paired_attempt_cannot_start_with_only_one_slot_left(self):
        from ui.app import BonnevilleApp

        campaign = CampaignState(current_year=1924)
        campaign.record_runs_this_session = MAX_RECORD_RUNS_PER_SESSION - 1
        app = SimpleNamespace(
            campaign=campaign,
            garage_return_required=False,
            last_run_outcome=None,
            last_run_repaired=False,
        )
        entry = GarageVehicle(
            "Record Test",
            CHASSIS_TECHNOLOGY_TREE[0].technology_id,
            NAPIER_LION.name,
            TRANSMISSION_CATALOG[2].name,
            "1920s mechanical drum brakes",
        )

        with patch("ui.app.messagebox.showerror") as show_error, patch(
            "ui.app.run_simulation"
        ) as simulate:
            BonnevilleApp.execute_run(
                app,
                entry,
                PUBLIC_ROADS,
                record_attempt=True,
                record_target=HISTORICAL_TARGETS[0],
            )

        show_error.assert_called_once()
        simulate.assert_not_called()

    def test_record_attempt_garage_view_only_offers_service_routes(self):
        from ui.app import BonnevilleApp

        campaign = CampaignState(current_year=1950)
        entry = GarageVehicle(
            "Record Test",
            CHASSIS_TECHNOLOGY_TREE[0].technology_id,
            NAPIER_LION.name,
            TRANSMISSION_CATALOG[2].name,
            "1920s mechanical drum brakes",
        )
        campaign.garage.vehicles.append(entry)
        campaign.record_attempt = CampaignRecordAttempt(
            HISTORICAL_TARGETS[0].record_id,
            entry.vehicle_name,
            PUBLIC_ROADS.name,
            1950,
            2,
            [100.0],
        )
        app = BonnevilleApp.__new__(BonnevilleApp)
        app.campaign = campaign
        app.show_page = Mock()
        app.body = Mock()
        app.page_title = Mock()
        app.card = Mock(return_value=Mock())
        app.section = Mock()
        app.action_button = Mock()
        scroll_area = Mock()
        container = Mock()
        page = Mock()
        app.body.winfo_children.return_value = [scroll_area]
        scroll_area.winfo_children.return_value = [container]
        container.winfo_children.return_value = [page]

        with patch("ui.app.tk.Frame"), patch("ui.app.tk.Label"):
            BonnevilleApp.open_garage_vehicle(app, entry)

        labels = [call.args[1] for call in app.action_button.call_args_list]
        self.assertEqual(
            labels,
            ["OPEN TRACKSIDE SERVICE", "RETURN TO RECORD ATTEMPT"],
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

    def test_trackside_brake_service_costs_five_and_updates_vehicle(self):
        campaign = CampaignState()
        entry = self._garage_entry()
        campaign.garage.vehicles.append(entry)
        starting_cash = campaign.team.cash
        fit_trackside_brakes(
            campaign, entry, "Hydraulic disc brakes", current_year=1950
        )

        self.assertEqual(entry.brakes_name, "Hydraulic disc brakes")
        self.assertEqual(campaign.team.cash, starting_cash - 5.0)

    def test_mechanic_suggests_lengthening_final_drive_on_rev_limiter(self):
        vehicle = AVAILABLE_CARS["1"]()
        vehicle.gearbox.gears = (3.0, 2.0)
        redline_rpm = vehicle.engine.max_rpm * 0.95
        overall = 2.0 * vehicle.gearbox.final_drive_ratio
        speed_mph = (
            redline_rpm / 60 / overall * 2 * math.pi * vehicle.wheel_radius_m * 2.23694
        )
        result = SimpleNamespace(
            telemetry=[
                SimpleNamespace(
                    speed_mph=speed_mph,
                    engine_rpm=int(redline_rpm),
                    gear=2,
                    wheelspin=False,
                    acceleration_g=0.0,
                    phase="measured mile",
                )
            ],
            average_acceleration_g=0.2,
            wheelspin_event_count=0,
        )

        suggestion = suggest_gear_ratio_adjustment(vehicle, result)

        self.assertTrue(suggestion.changes_needed)
        self.assertEqual(len(suggestion.gears), 2)
        self.assertLess(
            suggestion.gears[-1] * suggestion.final_drive,
            vehicle.gearbox.gears[-1] * vehicle.gearbox.final_drive_ratio,
        )
        self.assertGreater(suggestion.gears[0], suggestion.gears[1])
        self.assertIn("rev limit", suggestion.description)

    def test_mechanic_suggestion_improves_measured_mile(self):
        vehicle = AVAILABLE_CARS["1"]()
        track = PUBLIC_ROADS

        def run(car):
            return run_simulation(
                car,
                track_miles=track.length_miles,
                measured_mile_start=track.measured_mile_start,
                track_friction_factor=track.friction_factor,
                air_density_kg_m3=track.air_density_kg_m3,
            )

        before = run(vehicle)
        suggestion = suggest_gear_ratio_adjustment(
            vehicle, before, track.friction_factor
        )
        vehicle.gearbox.gears = suggestion.gears
        vehicle.gearbox.final_drive = suggestion.final_drive

        self.assertGreater(
            run(vehicle).measured_mile_speed_mph,
            before.measured_mile_speed_mph,
        )

    def test_full_ratio_set_applies_for_one_trackside_charge(self):
        campaign = CampaignState()
        entry = self._garage_entry()
        campaign.garage.vehicles.append(entry)
        starting_cash = campaign.team.cash
        gear_count = build_vehicle_from_garage_entry(entry).gearbox.gear_count
        gears = tuple(round(2.0 - index * 0.3, 2) for index in range(gear_count))

        apply_gear_ratios_trackside(campaign, entry, gears, 1.25)

        rebuilt = build_vehicle_from_garage_entry(entry)
        self.assertEqual(rebuilt.gearbox.gears, gears)
        self.assertEqual(rebuilt.gearbox.final_drive_ratio, 1.25)
        self.assertEqual(campaign.team.cash, starting_cash - 5.0)

    def test_trackside_screen_offers_ratio_steps_and_another_test(self):
        from ui.app import BonnevilleApp

        entry = self._garage_entry()
        vehicle = build_vehicle_from_garage_entry(entry)
        app = BonnevilleApp.__new__(BonnevilleApp)
        app.campaign = CampaignState()
        app.last_run_is_sandbox = False
        app.last_run_was_record_attempt = False
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


class EngineAvailabilityTests(unittest.TestCase):
    def test_welch_hemi_unlocks_before_stanley_steam_engine(self):
        pioneer_engines = available_engines(["pioneer_engines"])
        edwardian_engines = available_engines(
            ["pioneer_engines", "edwardian_giants"]
        )

        self.assertIn(WELCH_HEMI, pioneer_engines)
        self.assertNotIn(STANLEY_STEAM_ENGINE, pioneer_engines)
        self.assertIn(STANLEY_STEAM_ENGINE, edwardian_engines)
        self.assertLess(WELCH_HEMI.power_hp, STANLEY_STEAM_ENGINE.power_hp)


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

    def test_first_engine_upgrade_opens_after_wind_deflector(self):
        campaign = CampaignState()
        app = self._research_app(campaign)
        self.assertFalse(app._research_branch_available("Engine"))
        complete_engineering_project(campaign, "aerodynamics", "wind_deflector")
        self.assertTrue(app._research_branch_available("Engine"))
        self.assertFalse(app._research_branch_available("Chassis"))
        complete_engineering_project(campaign, "engine", "pioneer_engines")
        self.assertIn(WELCH_HEMI, available_engines(campaign.research.engine_technology))

    def test_research_tabs_follow_completed_prerequisites(self):
        campaign = self._pioneer_aero_campaign()
        app = self._research_app(campaign)
        self.assertTrue(app._research_branch_available("Chassis"))
        self.assertTrue(app._research_branch_available("Engine"))
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
                    garage_return_required=False,
                    last_run_outcome=None,
                    last_run_repaired=False,
                    show_page=Mock(), advance_campaign_turn=Mock(),
                    offer_end_turn_after_failure=Mock(),
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
                self.assertEqual(
                    app.campaign.venues_paid_this_session, [PUBLIC_ROADS.name]
                )
                self.assertEqual(app.last_report.completed, not failed)
                self.assertFalse(app.last_run_is_sandbox)
                self.assertEqual(save_record.call_count, 0 if failed else 1)
                self.assertIsNone(app.last_record_message)
                self.assertEqual(app.campaign.workshop_repair_pending, failed)
                self.assertEqual(
                    app.offer_end_turn_after_failure.call_count, 1 if failed else 0
                )

    def test_workshop_repair_blocks_testing_until_turn_ends(self):
        from ui.app import BonnevilleApp

        campaign = CampaignState(workshop_repair_pending=True)
        app = SimpleNamespace(campaign=campaign, garage_return_required=False)
        with patch("ui.app.messagebox.showerror") as show_error, patch(
            "ui.app.run_simulation"
        ) as simulate:
            BonnevilleApp.execute_run(app, object(), PUBLIC_ROADS)
        show_error.assert_called_once()
        simulate.assert_not_called()

        advance_turn(campaign, days=0)

        self.assertFalse(campaign.workshop_repair_pending)

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

    def test_speed_objective_tracks_world_record_and_pays_out(self):
        from historical_records import current_world_record

        campaign = CampaignState(current_year=1908)
        objective = sign_sponsor(campaign, "local_investor")
        record = current_world_record(1908)
        self.assertAlmostEqual(objective.target, round(record.speed_mph * 0.8, 1))
        cash_before = campaign.team.cash

        messages = complete_run(campaign, 0, objective.target - 1.0)
        self.assertEqual(messages, [])
        messages = complete_run(campaign, 0, objective.target + 0.5)

        self.assertEqual(len(messages), 1)
        self.assertEqual(campaign.team.cash, cash_before + objective.reward_gbp)
        renewed = campaign.sponsorship.objective_for("local_investor")
        self.assertIsNot(renewed, objective)
        self.assertEqual(renewed.turns_remaining, 3)

    def test_runs_objective_counts_runs_since_issue(self):
        campaign = CampaignState(completed_runs=4)
        objective = sign_sponsor(campaign, "castrol")
        for _ in range(2):
            self.assertEqual(complete_run(campaign, 0, 10.0), [])
        self.assertEqual(len(complete_run(campaign, 0, 10.0)), 1)
        self.assertEqual(objective.runs_at_issue, 4)

    def test_missed_deadline_sponsor_withdraws_for_good(self):
        campaign = CampaignState(current_year=1908)
        campaign.team.reputation = 10.0
        sign_sponsor(campaign, "shell")
        for _ in range(2):
            advance_turn(campaign, days=0)
            self.assertIn("shell", campaign.sponsorship.active_sponsors)
        advance_turn(campaign, days=0)

        self.assertNotIn("shell", campaign.sponsorship.active_sponsors)
        self.assertIn("shell", campaign.sponsorship.departed_sponsors)
        self.assertEqual(campaign.sponsorship.recent_departures, ["Shell"])
        self.assertEqual(campaign.team.reputation, 9.0)
        self.assertEqual(campaign.sponsorship.income_per_turn_gbp, 0)
        with self.assertRaisesRegex(ValueError, "withdrawn"):
            sign_sponsor(campaign, "shell")

    def test_sponsor_objectives_survive_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "campaign_state.json"
            campaign = CampaignState()
            sign_sponsor(campaign, "castrol")
            save_campaign(campaign, path)
            loaded = load_campaign(path)
        objective = loaded.sponsorship.objective_for("castrol")
        self.assertEqual(objective.target, 3)
        self.assertEqual(objective.turns_remaining, 3)

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

    def test_clear_diagnostic_log_removes_file_and_tolerates_missing(self):
        from diagnostics import clear_diagnostic_log

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = Path(tmp_dir) / "test_vehicle_diagnostics.log"
            log_path.write_text("old runs", encoding="utf-8")
            clear_diagnostic_log(log_path)
            self.assertFalse(log_path.exists())
            clear_diagnostic_log(log_path)

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
