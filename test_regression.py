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
    development_failure_risk_multiplier,
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
    select_development_program,
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
    if campaign.current_era not in campaign.development_programs:
        program_for_branch = {
            "aerodynamics": "aerodynamic_pioneer",
            "engine": "power_gambler",
            "chassis": "engineering_perfectionist",
            "gearbox": "engineering_perfectionist",
            "tyre": "engineering_perfectionist",
            "brake": "engineering_perfectionist",
        }
        select_development_program(campaign, program_for_branch[branch])
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
    def test_header_gap_uses_the_closest_rival_not_the_world_record(self):
        from types import SimpleNamespace
        from ui.app import closest_rival_gap_headline

        rivals = [
            SimpleNamespace(name="Fast Leader", best_speed_mph=250.0),
            SimpleNamespace(name="Nearest Rival", best_speed_mph=104.0),
            SimpleNamespace(name="Slow Rival", best_speed_mph=80.0),
        ]
        self.assertEqual(
            closest_rival_gap_headline(rivals, 100.0),
            "4.0 mph behind Nearest Rival",
        )
        self.assertEqual(
            closest_rival_gap_headline(rivals, 106.0),
            "2.0 mph ahead of Nearest Rival",
        )
        self.assertEqual(closest_rival_gap_headline([], 100.0), "No rival speeds yet")

    def test_campaign_header_displays_nearest_rival_gap(self):
        from types import SimpleNamespace
        from ui.app import BonnevilleApp

        campaign = CampaignState()
        campaign.best_measured_mile_speed_mph = 100.0
        campaign.world.rivals = [
            SimpleNamespace(name="Fast Leader", best_speed_mph=250.0),
            SimpleNamespace(name="Nearest Rival", best_speed_mph=104.0),
        ]
        app = SimpleNamespace(campaign=campaign, header_status=Mock())

        BonnevilleApp._refresh_header(app)

        banner = app.header_status.configure.call_args.kwargs["text"]
        self.assertIn("4.0 MPH BEHIND NEAREST RIVAL", banner)
        self.assertNotIn("150.0 MPH SHORT", banner)

    def test_inaugural_attempt_runs_through_the_ui_without_a_rival_record(self):
        from ui.app import BonnevilleApp

        for speed in (0.0, 20.0):
            with self.subTest(speed=speed):
                campaign = CampaignState()
                entry = GarageVehicle(
                    "First Car", "improvised_chassis", PIONEER_SINGLE_CYLINDER.name,
                    "2-Speed Transmission", "Wooden block brakes",
                )
                campaign.garage.vehicles.append(entry)
                app = SimpleNamespace(
                    campaign=campaign, garage_return_required=False,
                    last_run_outcome=None, last_run_repaired=False,
                    last_report=None, show_page=Mock(),
                    _render_record_vehicle_choices=Mock(),
                )
                BonnevilleApp.start_record_attempt(app)
                target = app._render_record_vehicle_choices.call_args.args[0]
                self.assertEqual(target.record_id, "inaugural_record")
                result = SimpleNamespace(
                    peak_speed_mph=speed, measured_mile_speed_mph=speed, telemetry=[],
                )
                with (
                    patch("ui.app.build_vehicle_from_garage_entry", return_value=AVAILABLE_CARS["1"]()),
                    patch("ui.app.messagebox.askyesno", return_value=True),
                    patch("ui.app.run_simulation", return_value=result),
                    patch("ui.app.resolve_run_failure", return_value=SimpleNamespace(failed=False, repaired=False)),
                    patch("ui.app.append_run_log"),
                    patch("ui.app.save_campaign"),
                    patch("ui.app.create_record") as make_record,
                    patch("ui.app.save_record"),
                    patch("ui.app.create_engineering_report"),
                ):
                    BonnevilleApp.execute_run(app, entry, PUBLIC_ROADS, record_attempt=True)
                self.assertIsNone(campaign.record_attempt)
                self.assertEqual(campaign.record_runs_this_session, 1)
                self.assertEqual(campaign.official_record_mph, speed)
                self.assertEqual(make_record.call_args.kwargs["official_average_mph"], speed)
                self.assertEqual(make_record.call_args.kwargs["world_record_set"], speed > 0)
                if speed > 0:
                    self.assertEqual(campaign.official_record_vehicle_name, entry.vehicle_name)
                self.assertIn(
                    "inaugural land-speed record has been established" if speed > 0
                    else "No inaugural record credited",
                    app.last_record_message,
                )

    def test_fresh_career_can_target_and_set_the_inaugural_record(self):
        from management import record_chase_target, standing_world_record

        campaign = CampaignState()
        self.assertIsNone(standing_world_record(campaign))
        target = record_chase_target(campaign)
        self.assertEqual(target.record_id, "inaugural_record")
        self.assertEqual(target.speed_mph, 0.0)
        from historical_records import target_completed
        from ui.app import record_gap_headline

        self.assertFalse(target_completed(target, 0.0))
        self.assertTrue(target_completed(target, 20.0))
        self.assertEqual(record_gap_headline(target, 20.0), "Set inaugural record")
        complete_run(campaign, 0.0, 20.0, is_record_attempt=True)
        self.assertEqual(standing_world_record(campaign), (20.0, campaign.team.name, 1895))
        self.assertEqual(record_chase_target(campaign).record_id, "team_record")

    def test_practice_or_zero_speed_does_not_establish_an_inaugural_record(self):
        from management import record_chase_target, standing_world_record

        campaign = CampaignState()
        complete_run(campaign, 0.0, 20.0)
        complete_run(campaign, 0.0, 0.0, is_record_attempt=True)
        self.assertIsNone(standing_world_record(campaign))
        self.assertEqual(record_chase_target(campaign).record_id, "inaugural_record")
        self.assertFalse(any("WORLD RECORD:" in item for item in campaign.world.headlines))

    def test_saved_inaugural_attempt_restores_its_target(self):
        from management import record_attempt_target

        campaign = CampaignState()
        campaign.record_attempt = CampaignRecordAttempt(
            "inaugural_record", "First Car", "Public Roads", 1895, 1,
            target_year=1895, target_speed_mph=0.0,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "campaign.json"
            save_campaign(campaign, path)
            restored = load_campaign(path)
        target = record_attempt_target(restored, restored.record_attempt)
        self.assertEqual(target.record_id, "inaugural_record")
        self.assertEqual(target.speed_mph, 0.0)

    def test_team_record_becomes_a_target_to_extend(self):
        from management import record_chase_target

        campaign = CampaignState(current_year=1899, current_day_of_year=365)
        campaign.official_record_mph = 70.0
        target = record_chase_target(campaign)
        self.assertEqual(target.record_id, "team_record")
        self.assertEqual(target.speed_mph, 70.0)
        self.assertIn("beyond 70.0 mph", target.milestone)

    def test_team_can_extend_its_official_record(self):
        campaign = CampaignState(current_year=1899, current_day_of_year=365)
        campaign.official_record_mph = 70.0

        complete_run(campaign, 0.0, 70.1, is_record_attempt=True)

        self.assertEqual(campaign.official_record_mph, 70.1)
        self.assertTrue(
            any(
                "extends its record to 70.10 mph" in headline
                for headline in campaign.world.headlines
            )
        )

    def test_saved_team_record_attempt_keeps_its_original_benchmark(self):
        from management import (
            CampaignRecordAttempt,
            record_attempt_target,
        )

        campaign = CampaignState(current_year=1900)
        campaign.official_record_mph = 75.0
        attempt = CampaignRecordAttempt(
            target_id="team_record",
            vehicle_name="Record Chaser",
            track_name="Public Roads",
            started_year=1899,
            required_runs=2,
            target_year=1899,
            target_vehicle="Bonneville Team official record",
            target_speed_mph=70.0,
        )

        target = record_attempt_target(campaign, attempt)

        self.assertEqual(target.speed_mph, 70.0)
        self.assertEqual(target.year, 1899)

    def test_rival_record_becomes_chase_target_once_faster(self):
        from campaign_world import advance_world
        from management import record_chase_target

        campaign = CampaignState(current_year=1899, current_day_of_year=365)
        campaign.official_record_mph = 60.0
        advance_world(campaign)

        self.assertEqual(
            record_chase_target(campaign).record_id,
            "jamais_contente_1899",
        )

    def test_first_upgraded_car_can_reach_the_1899_standing_record(self):
        from historical_records import current_world_record
        from simulation import run_simulation
        from tracks import PUBLIC_ROADS
        from vehicle_designer import build_vehicle_from_garage_entry

        entry = GarageVehicle(
            "Record Chaser",
            "carriage_frame",
            WELCH_HEMI.name,
            "2-Speed Transmission",
            "Wooden block brakes",
            ("wind_deflector", "wheel_fairings_/_spats", "basic_streamlining"),
            (3.0, 2.5),
            1.5,
            3,
        )
        vehicle = build_vehicle_from_garage_entry(entry)
        result = run_simulation(
            vehicle,
            PUBLIC_ROADS.length_miles,
            PUBLIC_ROADS.measured_mile_start,
            track_friction_factor=PUBLIC_ROADS.friction_factor,
            air_density_kg_m3=PUBLIC_ROADS.air_density_kg_m3,
        )

        self.assertGreaterEqual(
            result.measured_mile_speed_mph,
            current_world_record(1899).speed_mph,
        )

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
        self.assertEqual(record_gap_headline(None, 500.0), "No rival record to chase")


class MuseumHistoryTests(unittest.TestCase):
    def test_museum_status_changes_when_the_retired_cars_record_is_beaten(self):
        from ui.app import BonnevilleApp

        campaign = CampaignState()
        campaign.official_record_mph = 80
        campaign.official_record_vehicle_name = "Museum Car"
        campaign.garage.museum.append(GarageVehicle(
            "Museum Car", "improvised_chassis", PIONEER_SINGLE_CYLINDER.name,
            "2-Speed Transmission", "Wooden block brakes",
        ))
        runs = [dict(
            campaign_id=campaign.campaign_id, car_name="Museum Car",
            peak_speed_mph=90, measured_mile_speed_mph=85, official_average_mph=80,
            world_record_set=True, campaign_year=1895, campaign_season="Summer",
            track_name="Public Roads",
        )]
        app = SimpleNamespace(campaign=campaign, scroll_area=Mock(), page_title=Mock(), section=Mock())
        for rival_speed, status in ((0, "Current"), (81, "Former")):
            with self.subTest(rival_speed=rival_speed):
                campaign.world.record_speed_mph = rival_speed
                campaign.world.record_holder = "Rival Team"
                with patch("ui.app.load_records", return_value=runs), patch("ui.app.tk.Frame"), patch("ui.app.tk.Label") as labels:
                    BonnevilleApp.render_museum(app)
                text = "\n".join(call.kwargs.get("text", "") for call in labels.call_args_list)
                self.assertIn(f"{status} world-record holder", text)
                self.assertIn("Peak speed: 90.0 mph", text)
                self.assertIn("Best official average: 80.00 mph", text)
                self.assertIn("Summer 1895: 80.00 mph", text)
                self.assertIn("World records set: 1", text)

    def test_official_achievement_metadata_survives_record_file_roundtrip(self):
        campaign = CampaignState()
        vehicle = AVAILABLE_CARS["1"]()
        result = SimpleNamespace(
            peak_speed_mph=30, measured_mile_speed_mph=25,
            average_acceleration_g=0.1, average_deceleration_g=0.1,
            full_throttle_seconds=50,
        )
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(records, "RECORDS_FILE", Path(directory) / "records.json"):
                records.save_record(records.create_record(
                    vehicle, PUBLIC_ROADS, result, campaign,
                    official_average_mph=22.5, world_record_set=True,
                ))
                history = records.vehicle_history(records.load_records(), campaign.campaign_id, vehicle.name)
        self.assertEqual(history.official_best_mph, 22.5)
        self.assertEqual(history.world_records[0]["campaign_year"], 1895)
        self.assertEqual(history.world_records[0]["campaign_season"], "Spring")

    def test_history_separates_peak_practice_and_official_results_by_car_and_career(self):
        runs = [
            dict(campaign_id="career", car_name="Retired Car", peak_speed_mph=110, measured_mile_speed_mph=100),
            dict(campaign_id="career", car_name="Retired Car", peak_speed_mph=90, measured_mile_speed_mph=85,
                 official_average_mph=80, world_record_set=True, campaign_year=1895, campaign_season="Summer"),
            dict(campaign_id="other", car_name="Retired Car", peak_speed_mph=999, measured_mile_speed_mph=999,
                 official_average_mph=999, world_record_set=True),
            dict(campaign_id="career", car_name="Another Car", peak_speed_mph=888, measured_mile_speed_mph=888),
        ]
        history = records.vehicle_history(runs, "career", "Retired Car")
        self.assertEqual(history.peak_speed_mph, 110)
        self.assertEqual(history.best_measured_mile_mph, 100)
        self.assertEqual(history.official_best_mph, 80)
        self.assertEqual(len(history.world_records), 1)

    def test_legacy_runs_and_unrun_cars_do_not_gain_invented_record_credits(self):
        legacy = dict(campaign_id="career", car_name="Old Car", peak_speed_mph=100, measured_mile_speed_mph=95)
        history = records.vehicle_history([legacy], "career", "Old Car")
        self.assertEqual(history.peak_speed_mph, 100)
        self.assertIsNone(history.official_best_mph)
        self.assertEqual(history.world_records, [])
        empty = records.vehicle_history([], "career", "Unrun Car")
        self.assertIsNone(empty.peak_speed_mph)
        self.assertIsNone(empty.official_best_mph)

    def test_official_best_retains_vehicle_attribution_until_another_car_improves_it(self):
        campaign = CampaignState()
        complete_run(campaign, 0, 20, is_record_attempt=True, vehicle_name="First Car")
        self.assertEqual(campaign.official_record_vehicle_name, "First Car")
        complete_run(campaign, 0, 25)
        complete_run(campaign, 0, 19, is_record_attempt=True, vehicle_name="Second Car")
        self.assertEqual(campaign.official_record_vehicle_name, "First Car")
        complete_run(campaign, 0, 21, is_record_attempt=True, vehicle_name="Second Car")
        self.assertEqual(campaign.official_record_vehicle_name, "Second Car")


class VehicleNamingTests(unittest.TestCase):
    def test_new_design_inherits_engine_tune_and_matching_gearbox_ratios(self):
        from ui.app import BonnevilleApp

        campaign = CampaignState()
        donor = GarageVehicle(
            "Existing Build",
            "improvised_chassis",
            PIONEER_SINGLE_CYLINDER.name,
            TRANSMISSION_CATALOG[1].name,
            "Wooden block brakes",
            gearbox_ratios=(3.6, 2.2),
            gearbox_final_drive=1.8,
            engine_tune_stage=2,
        )
        campaign.garage.vehicles.append(donor)
        app = SimpleNamespace(
            campaign=campaign,
            builder={},
            render_builder=Mock(),
            show_page=Mock(),
        )
        app._inherited_engine_tune_stage = lambda engine_name: (
            BonnevilleApp._inherited_engine_tune_stage(app, engine_name)
        )
        app._gearbox_with_saved_ratios = lambda gearbox, exclude_entry=None: (
            BonnevilleApp._gearbox_with_saved_ratios(app, gearbox, exclude_entry)
        )
        app._aerodynamics_summary = lambda technology_ids=None: "None researched\nCumulative drag reduction: 0%"

        BonnevilleApp.builder_select(app, "engine", PIONEER_SINGLE_CYLINDER, reuse_engine_tune=True)
        BonnevilleApp.builder_select(app, "gearbox", TRANSMISSION_CATALOG[1])
        self.assertEqual(app.builder["engine_tune_stage"], 2)
        self.assertEqual(app.builder["gearbox"].gears, (3.6, 2.2))
        self.assertEqual(app.builder["gearbox"].final_drive_ratio, 1.8)

        app.builder.update(
            {
                "chassis": CHASSIS_BY_ID["improvised_chassis"],
                "brakes": BRAKE_BY_NAME["Wooden block brakes"],
            }
        )
        with (
            patch("ui.app.messagebox.askyesno", return_value=True) as confirm,
            patch("ui.app.build_vehicle") as build,
            patch("ui.app.save_campaign"),
        ):
            BonnevilleApp.finish_vehicle_build(app, "Inherited Build")

        confirmation_text = confirm.call_args.args[1]
        self.assertIn("Engine tune: Stage 2", confirmation_text)
        self.assertIn("Complexity: 1/5  /  Build time: 1 turn(s)", confirmation_text)
        self.assertIn("2-Speed Transmission ratios: 3.60 / 2.20", confirmation_text)
        self.assertIn("Final drive: 1.80", confirmation_text)
        entry = build.call_args.args[1]
        vehicle = build.call_args.kwargs["vehicle"]
        self.assertEqual(entry.engine_tune_stage, 2)
        self.assertEqual(entry.gearbox_ratios, (3.6, 2.2))
        self.assertEqual(entry.gearbox_final_drive, 1.8)
        self.assertEqual(vehicle.engine.power_hp, tune_engine(PIONEER_SINGLE_CYLINDER, 2).power_hp)

    def test_new_vehicle_confirmation_lists_prefitted_aerodynamics(self):
        from ui.app import BonnevilleApp

        campaign = CampaignState()
        campaign.research.aerodynamics_technology = [
            "wind_deflector",
            "wheel_fairings_/_spats",
            "basic_streamlining",
        ]
        app = SimpleNamespace(
            campaign=campaign,
            builder={
                "chassis": CHASSIS_BY_ID["improvised_chassis"],
                "engine": PIONEER_SINGLE_CYLINDER,
                "gearbox": TRANSMISSION_CATALOG[1],
                "brakes": BRAKE_BY_NAME["Wooden block brakes"],
            },
            show_page=Mock(),
        )
        app._aerodynamics_summary = lambda technology_ids=None: (
            BonnevilleApp._aerodynamics_summary(app, technology_ids)
        )

        with patch("ui.app.messagebox.askyesno", return_value=False) as confirm:
            BonnevilleApp.finish_vehicle_build(app, "Aero Test")

        confirmation_text = confirm.call_args.args[1]
        self.assertIn("Wind Deflector", confirmation_text)
        self.assertIn("Wheel Fairings / Spats", confirmation_text)
        self.assertIn("Basic Streamlining", confirmation_text)
        self.assertIn("Cumulative drag reduction: 7%", confirmation_text)

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
    def test_tuning_records_the_setup_for_only_the_installed_model(self):
        from ui.app import BonnevilleApp

        campaign = CampaignState()
        entry = self._garage_entry(stage=1)
        campaign.garage.vehicles.append(entry)
        app = SimpleNamespace(campaign=campaign, open_garage_vehicle=Mock())
        with patch("ui.app.save_campaign"):
            BonnevilleApp.set_engine_tune(app, entry, 2)
        self.assertEqual(campaign.engine_tune_stages, {entry.engine_name: 2})
        self.assertEqual(entry.engine_tune_stage, 2)

    def test_tune_confirmation_quotes_price_and_reliability_tradeoff(self):
        from ui.app import BonnevilleApp

        app = SimpleNamespace(set_engine_tune=Mock())
        entry = self._garage_entry()
        with patch("ui.app.messagebox.askyesno", return_value=True) as confirm:
            BonnevilleApp.confirm_engine_tune(app, entry, 1, 500)
        text = confirm.call_args.args[1]
        self.assertIn("GBP 500", text)
        self.assertIn("Reliability penalty: -3%", text)
        app.set_engine_tune.assert_called_once_with(entry, 1)

    def test_engine_tune_costs_cash_once_per_turn_and_turn_resets_limit(self):
        from management import apply_engine_tune, engine_tune_cost

        campaign = CampaignState()
        first = self._garage_entry()
        second = self._garage_entry()
        second.vehicle_name = "Another Tune Test"
        campaign.garage.vehicles.extend((first, second))
        cash = campaign.team.cash
        cost = engine_tune_cost(first.engine_name, 1)
        self.assertGreater(cost, 0)
        self.assertEqual(apply_engine_tune(campaign, first, 1), cost)
        self.assertEqual(campaign.team.cash, cash - cost)
        self.assertEqual(campaign.engine_tunes_this_turn, 1)
        with self.assertRaisesRegex(ValueError, "one engine tune"):
            apply_engine_tune(campaign, second, 1)
        self.assertEqual(second.engine_tune_stage, 0)
        self.assertEqual(campaign.team.cash, cash - cost)
        advance_turn(campaign, days=0)
        self.assertEqual(campaign.engine_tunes_this_turn, 0)
        next_cost = engine_tune_cost(second.engine_name, 1)
        apply_engine_tune(campaign, second, 1)
        self.assertEqual(campaign.team.cash, cash - cost - next_cost - 450)

    def test_builder_requires_explicit_reuse_and_keeps_engine_models_separate(self):
        from ui.app import BonnevilleApp

        campaign = CampaignState()
        campaign.engine_tune_stages[PIONEER_SINGLE_CYLINDER.name] = 3
        app = SimpleNamespace(campaign=campaign, builder={}, render_builder=Mock())
        app._inherited_engine_tune_stage = lambda name: BonnevilleApp._inherited_engine_tune_stage(app, name)
        BonnevilleApp.builder_select(app, "engine", PIONEER_SINGLE_CYLINDER)
        self.assertEqual(app.builder["engine_tune_stage"], 0)
        BonnevilleApp.builder_select(app, "engine", PIONEER_SINGLE_CYLINDER, reuse_engine_tune=True)
        self.assertEqual(app.builder["engine_tune_stage"], 3)
        BonnevilleApp.builder_select(app, "engine", WELCH_HEMI, reuse_engine_tune=True)
        self.assertEqual(app.builder["engine_tune_stage"], 0)

    def test_new_stock_and_reused_model_tunes_are_distinct_during_swaps(self):
        from ui.app import BonnevilleApp

        for reuse, expected in ((False, 0), (True, 2)):
            with self.subTest(reuse=reuse):
                campaign = CampaignState()
                entry = GarageVehicle(
                    "Swap Car", "improvised_chassis", PIONEER_SINGLE_CYLINDER.name,
                    TRANSMISSION_CATALOG[1].name, "Wooden block brakes", engine_tune_stage=3,
                )
                campaign.garage.vehicles.append(entry)
                campaign.engine_tune_stages[WELCH_HEMI.name] = 2
                app = SimpleNamespace(campaign=campaign, open_garage_vehicle=Mock())
                app._inherited_engine_tune_stage = lambda name: BonnevilleApp._inherited_engine_tune_stage(app, name)
                app._gearbox_with_saved_ratios = lambda gearbox, exclude_entry=None: (gearbox, False)
                with patch("ui.app.save_campaign"):
                    BonnevilleApp.apply_component(app, entry, "engine", WELCH_HEMI, Mock(), reuse_engine_tune=reuse)
                self.assertEqual(entry.engine_tune_stage, expected)
                self.assertEqual(campaign.engine_tune_stages[PIONEER_SINGLE_CYLINDER.name], 3)
                self.assertEqual(campaign.engine_tune_stages[WELCH_HEMI.name], 2)
                self.assertEqual(app._inherited_engine_tune_stage(WELCH_HEMI.name), 2)

    def test_removed_engine_model_tune_survives_save_load_and_can_be_refitted(self):
        from ui.app import BonnevilleApp

        campaign = CampaignState()
        entry = GarageVehicle(
            "Swap Car", "improvised_chassis", PIONEER_SINGLE_CYLINDER.name,
            TRANSMISSION_CATALOG[1].name, "Wooden block brakes", engine_tune_stage=3,
        )
        campaign.garage.vehicles.append(entry)
        app = SimpleNamespace(campaign=campaign, open_garage_vehicle=Mock())
        app._inherited_engine_tune_stage = lambda name: BonnevilleApp._inherited_engine_tune_stage(app, name)
        app._gearbox_with_saved_ratios = lambda gearbox, exclude_entry=None: (gearbox, False)
        with patch("ui.app.save_campaign"):
            BonnevilleApp.apply_component(app, entry, "engine", WELCH_HEMI, Mock())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "campaign.json"
            save_campaign(campaign, path)
            app.campaign = load_campaign(path)
        restored = app.campaign.garage.vehicles[0]
        with patch("ui.app.save_campaign"):
            BonnevilleApp.apply_component(app, restored, "engine", PIONEER_SINGLE_CYLINDER, Mock(), reuse_engine_tune=True)
        self.assertEqual(restored.engine_tune_stage, 3)

    def test_swapping_to_an_untuned_engine_model_does_not_inherit_chassis_tune(self):
        from ui.app import BonnevilleApp

        campaign = CampaignState()
        entry = GarageVehicle(
            "Engine Swap", "improvised_chassis", PIONEER_SINGLE_CYLINDER.name,
            TRANSMISSION_CATALOG[1].name, "Wooden block brakes", engine_tune_stage=3,
        )
        campaign.garage.vehicles.append(entry)
        app = SimpleNamespace(campaign=campaign, open_garage_vehicle=Mock())
        app._inherited_engine_tune_stage = lambda name: BonnevilleApp._inherited_engine_tune_stage(app, name)
        app._gearbox_with_saved_ratios = lambda gearbox, exclude_entry=None: (gearbox, False)
        with patch("ui.app.save_campaign"):
            BonnevilleApp.apply_component(app, entry, "engine", WELCH_HEMI, Mock())
        self.assertEqual(entry.engine_name, WELCH_HEMI.name)
        self.assertEqual(entry.engine_tune_stage, 0)

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
        app._aerodynamics_summary = lambda technology_ids=None: (
            BonnevilleApp._aerodynamics_summary(app, technology_ids)
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

        campaign = CampaignState(current_year=1924)
        target = next_historical_target(
            1924, [], campaign.current_day_of_year
        )
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
        with self.assertRaisesRegex(ValueError, "must be researched first"):
            fit_trackside_tyres(campaign, entry)
        campaign.research.tyre_technology.append("pneumatic_racing_tyres")
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

    def test_researched_early_brakes_can_be_fitted_trackside(self):
        campaign = CampaignState(current_year=1895)
        entry = self._garage_entry()
        campaign.garage.vehicles.append(entry)
        campaign.research.brake_technology.append("mechanical_drum_brakes")

        fit_trackside_brakes(
            campaign,
            entry,
            "Early mechanical drum brakes",
            current_year=campaign.current_year,
        )

        self.assertEqual(entry.brakes_name, "Early mechanical drum brakes")

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

    def test_manual_ratio_fields_accept_and_persist_mechanic_precision(self):
        from ui.app import BonnevilleApp

        campaign = CampaignState()
        entry = self._garage_entry()
        campaign.garage.vehicles.append(entry)
        app = BonnevilleApp.__new__(BonnevilleApp)
        app.campaign = campaign
        app.tune_vehicle_gearbox = Mock()

        with patch("ui.app.save_campaign"):
            app.set_gearbox_ratio(entry, 0, "3.05")

        self.assertEqual(entry.gearbox_ratios[0], 3.05)

        starting_cash = campaign.team.cash
        app.last_trackside_ratio_adjusted = False
        app.last_vehicle = None
        app.show_page = Mock()
        with patch("ui.app.save_campaign"):
            app.set_trackside_ratio(entry, None, "1.25")

        self.assertEqual(entry.gearbox_final_drive, 1.25)
        self.assertEqual(campaign.team.cash, starting_cash - 5.0)
        self.assertTrue(app.last_trackside_ratio_adjusted)

    def test_manual_ratio_input_rejects_out_of_range_values(self):
        from ui.app import BonnevilleApp

        app = BonnevilleApp.__new__(BonnevilleApp)
        with patch("ui.app.messagebox.showerror") as show_error:
            self.assertIsNone(app._parse_gear_ratio_input("6.01", None))
            self.assertIsNone(app._parse_gear_ratio_input("1.2345", 0))
        self.assertEqual(show_error.call_count, 2)

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
            patch("ui.app.tk.Entry"),
            patch("ui.app.tk.Button") as button,
        ):
            BonnevilleApp.render_trackside_modifications(app)

        action_labels = [call.args[1] for call in app.action_button.call_args_list]
        self.assertTrue(any("RUN ANOTHER TEST HERE" in label for label in action_labels))
        self.assertTrue(any("APPLY SUGGESTION" in label for label in action_labels))
        ratio_steps = {call.kwargs["text"] for call in button.call_args_list}
        self.assertTrue({"-0.05", "+0.05"}.issubset(ratio_steps))


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
        select_development_program(campaign, "aerodynamic_pioneer")
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
    def test_brooklands_debrief_recommends_longer_course_if_car_is_still_accelerating(self):
        from diagnostics import create_engineering_report, longer_track_recommendation
        from tracks import BROOKLANDS, PENDINE_SANDS

        vehicle = AVAILABLE_CARS["1"]()
        result = SimpleNamespace(
            completed=True,
            wheelspin_event_count=0,
            average_acceleration_g=0.12,
            maximum_brake_temperature_c=100.0,
            peak_speed_mph=100.0,
            measured_mile_speed_mph=98.0,
            telemetry=[SimpleNamespace(
                time_seconds=80, phase="measured mile",
                acceleration_g=0.08, speed_mph=100.0, brake_fade=False, gear=2,
            )],
        )
        campaign = CampaignState(current_year=1908)
        recommendation = longer_track_recommendation(vehicle, BROOKLANDS, result, campaign)
        self.assertIn("still accelerating", recommendation)
        report = create_engineering_report(vehicle, BROOKLANDS, result, campaign)
        self.assertIn(PENDINE_SANDS.name, report.recommendations[-1])

    def test_longer_course_advice_does_not_appear_after_terminal_speed(self):
        from diagnostics import longer_track_recommendation
        from gearbox import estimate_gear_limited_speed_mph, estimate_power_limited_speed_mph
        from tracks import BROOKLANDS

        vehicle = AVAILABLE_CARS["1"]()
        terminal_speed = min(
            estimate_gear_limited_speed_mph(vehicle),
            estimate_power_limited_speed_mph(vehicle, vehicle.engine),
        )
        result = SimpleNamespace(
            completed=True,
            telemetry=[SimpleNamespace(
                time_seconds=80, phase="measured mile",
                acceleration_g=0.01, speed_mph=terminal_speed * 0.96,
            )],
        )
        self.assertIsNone(
            longer_track_recommendation(
                vehicle, BROOKLANDS, result, CampaignState(current_year=1908)
            )
        )

    def test_successful_official_debrief_does_not_repeat_practice_record_prompt(self):
        from ui.app import BonnevilleApp

        campaign = CampaignState()
        campaign.official_record_mph = 30
        report = SimpleNamespace(
            vehicle_name="Record Car", track_name="Public Roads", run_status="COMPLETED",
            completed=True, diagnosis=SimpleNamespace(problem="Review", evidence="Telemetry"),
            recommendations=(), comparison="", target_assessment="Official record established.",
            research_branch="Engine",
        )
        app = SimpleNamespace(
            campaign=campaign, scroll_area=Mock(), page_title=Mock(), section=Mock(),
            action_button=Mock(), show_page=Mock(), _offer_another_record_attempt=Mock(),
            last_report=report, last_run_note="Completed.", last_run_is_sandbox=False,
            last_vehicle_entry=None, last_run_outcome=None,
            last_record_message="Official average: 30.0 mph. Record established.",
            last_result=SimpleNamespace(
                peak_speed_mph=35, measured_mile_speed_mph=30,
                average_acceleration_g=0.1, average_deceleration_g=0.1,
                maximum_brake_temperature_c=30, wheelspin_event_count=0,
            ),
        )
        for official in (False, True):
            with self.subTest(official=official):
                app.last_run_was_record_attempt = official
                with patch("ui.app.tk.Label") as labels:
                    BonnevilleApp.render_team_debrief(app)
                text = "\n".join(call.kwargs.get("text", "") for call in labels.call_args_list)
                self.assertEqual("Make it official with a record attempt" in text, not official)
                if official:
                    self.assertIn("Official average: 30.0 mph", text)

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
                entry = GarageVehicle(
                    vehicle.name, "improvised_chassis", PIONEER_SINGLE_CYLINDER.name,
                    "2-Speed Transmission", "Wooden block brakes",
                )
                app.campaign.garage.vehicles.append(entry)
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
                    BonnevilleApp.execute_run(app, entry, PUBLIC_ROADS)
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
        select_development_program(campaign, "aerodynamic_pioneer")
        start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        self.assertIn("2 turn(s) remaining", self._report(campaign).recommendations[0])

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
        self.assertIn("faster official mark", record_report.recommendations[-1])

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

    def test_campaign_target_matches_current_standing_historical_record(self):
        target = next_historical_target(
            1899,
            ["jeantaud_1898", "jenatzy_dogcart_1899", "jeantaud_profilee_1899"],
            183,
        )
        self.assertEqual(target.record_id, "jamais_contente_1899")

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
        self.assertEqual(
            [
                brake.name
                for brake in available_brakes(1895, ("mechanical_drum_brakes",))
            ],
            ["Wooden block brakes", "Early mechanical drum brakes"],
        )
        self.assertEqual(PIONEER_SINGLE_CYLINDER.power_hp, 30.0)
        self.assertLess(PIONEER_SINGLE_CYLINDER.reliability, 0.5)

    def test_test_run_does_not_complete_historical_target(self):
        campaign = CampaignState(current_year=1898)
        complete_run(campaign, 0.0, HISTORICAL_TARGETS[0].speed_mph)
        self.assertEqual(campaign.completed_historical_record_ids, [])


class CampaignProgressionRegressionTests(unittest.TestCase):
    def test_end_turn_returns_to_dashboard_from_any_page(self):
        from ui.app import BonnevilleApp

        app = SimpleNamespace(
            campaign=CampaignState(),
            page="Trackside Modifications",
            advance_campaign_turn=Mock(),
            show_page=Mock(),
        )

        with (
            patch("ui.app.messagebox.askyesno", return_value=True),
            patch("ui.app.save_campaign"),
        ):
            BonnevilleApp.end_turn(app)

        app.advance_campaign_turn.assert_called_once_with()
        app.show_page.assert_called_once_with("Dashboard")

    def test_news_reports_close_rival_and_future_capable_challenger(self):
        from campaign_world import advance_world

        close_rival = CampaignState(current_year=1899, current_day_of_year=365)
        close_rival.official_record_mph = 70.0
        advance_world(close_rival)
        self.assertTrue(
            any("CHALLENGE WATCH" in item for item in close_rival.world.headlines)
        )

        future_rival = CampaignState(current_year=1895)
        future_rival.official_record_mph = 38.0
        advance_world(future_rival)
        self.assertTrue(
            any("DEVELOPMENT WATCH" in item for item in future_rival.world.headlines)
        )

    def test_rivals_progress_during_research_and_survive_save_load(self):
        from management import standing_world_record, start_engineering_project

        campaign = CampaignState(current_year=1899)
        select_development_program(campaign, "engineering_perfectionist")
        start_engineering_project(campaign, "aerodynamics", "wind_deflector")
        advance_turn(campaign)
        advance_turn(campaign)
        self.assertEqual(campaign.engineering_projects[0].turns_remaining, 2)
        self.assertEqual(standing_world_record(campaign)[1], "Camille Jenatzy Team")

        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "campaign.json"
            save_campaign(campaign, path)
            restored = load_campaign(path)
        self.assertEqual(restored.world, campaign.world)
        self.assertEqual(standing_world_record(restored), standing_world_record(campaign))

    def test_rival_attempt_occurs_on_date_without_waiting_for_new_year(self):
        from management import standing_world_record

        campaign = CampaignState(current_year=1899)
        advance_turn(campaign, days=15)
        self.assertNotIn("jenatzy_dogcart_1899", campaign.world.historical_attempts_seen)
        advance_turn(campaign, days=1)
        self.assertIn("jenatzy_dogcart_1899", campaign.world.historical_attempts_seen)
        self.assertEqual(standing_world_record(campaign)[1], "Camille Jenatzy Team")

    def test_player_reclaims_record_without_new_historical_milestone(self):
        from management import standing_world_record

        campaign = CampaignState(current_year=1908)
        campaign.completed_historical_record_ids = [
            target.record_id for target in HISTORICAL_TARGETS if target.speed_mph <= 130.0
        ]
        campaign.world.record_speed_mph = 130.0
        campaign.world.record_holder = "Rival Team"
        campaign.world.record_year = 1908
        completed_ids = list(campaign.completed_historical_record_ids)
        complete_run(campaign, 0, 130.01, is_record_attempt=True)
        self.assertEqual(campaign.completed_historical_record_ids, completed_ids)
        self.assertEqual(campaign.official_record_mph, 130.01)
        self.assertEqual(standing_world_record(campaign)[1], campaign.team.name)
        self.assertIn("WORLD RECORD:", campaign.world.headlines[-1])

    def test_historical_rivals_take_record_but_cannot_beat_faster_player(self):
        from campaign_world import advance_world

        campaign = CampaignState(current_year=1899, current_day_of_year=365)
        advance_world(campaign)
        self.assertEqual(campaign.world.record_holder, "Camille Jenatzy Team")
        self.assertEqual(campaign.world.record_speed_mph, 65.79)
        self.assertTrue(any("WORLD RECORD:" in item for item in campaign.world.headlines))

        player_campaign = CampaignState(current_year=1899, current_day_of_year=365)
        player_campaign.official_record_mph = 100.0
        advance_world(player_campaign)
        self.assertEqual(player_campaign.world.record_speed_mph, 0.0)
        self.assertFalse(any("WORLD RECORD:" in item for item in player_campaign.world.headlines))

    def test_historical_attempts_are_not_repeated_and_skipped_years_are_replayed(self):
        from campaign_world import advance_world

        campaign = CampaignState(current_year=1905, current_day_of_year=365)
        advance_world(campaign)
        expected = [target.record_id for target in HISTORICAL_TARGETS if target.year <= 1905]
        self.assertEqual(campaign.world.historical_attempts_seen, expected)
        advance_world(campaign)
        self.assertEqual(campaign.world.historical_attempts_seen, expected)
        self.assertFalse(any("WORLD RECORD:" in item for item in campaign.world.headlines))

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
        self.assertEqual(campaign.current_day_of_year, 1)
        self.assertEqual(campaign.current_season, "Spring")
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
        self.assertEqual(len(campaign.garage.vehicles), 0)
        for _ in range(campaign.vehicle_construction[0].turns_total):
            advance_turn(campaign)
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

    def test_technical_sponsor_does_not_require_repetitive_runs(self):
        campaign = CampaignState(completed_runs=4)
        objective = sign_sponsor(campaign, "castrol")
        for _ in range(6):
            self.assertEqual(complete_run(campaign, 0, 10.0), [])
        self.assertEqual(objective.kind, "development")
        self.assertIsNone(objective.turns_remaining)

    def test_missed_deadline_sponsor_can_return_after_one_turn(self):
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
        advance_turn(campaign, days=0)
        self.assertNotIn("shell", campaign.sponsorship.departed_sponsors)
        self.assertEqual(campaign.sponsorship.recent_departures, [])
        from sponsors import available_sponsors, SPONSOR_BY_ID

        self.assertIn(SPONSOR_BY_ID["shell"], available_sponsors(
            campaign.team.reputation, campaign.sponsorship.active_sponsors,
            campaign.sponsorship.departed_sponsors,
        ))
        sign_sponsor(campaign, "shell")
        self.assertIn("shell", campaign.sponsorship.active_sponsors)
        self.assertEqual(campaign.sponsorship.objective_for("shell").turns_remaining, 3)

    def test_sponsor_objectives_survive_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "campaign_state.json"
            campaign = CampaignState()
            sign_sponsor(campaign, "castrol")
            save_campaign(campaign, path)
            loaded = load_campaign(path)
        objective = loaded.sponsorship.objective_for("castrol")
        self.assertEqual(objective.target, 1)
        self.assertEqual(objective.kind, "development")
        self.assertIsNone(objective.turns_remaining)

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
