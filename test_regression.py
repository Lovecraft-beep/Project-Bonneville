"""Broader regression coverage across Project Bonneville's systems.

Complements test_gearbox.py (shift-logic edge cases) and test_compatibility.py
(full car/engine/gearbox/track simulation matrix) by exercising the
management, research, vehicle designer, sponsorship, save/load, historical
challenge, and encyclopedia systems that aren't covered elsewhere.
"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import records
from brakes import BRAKE_BY_NAME
from brakes import available_brakes
from cars import AVAILABLE_CARS
from chassis import CHASSIS_BY_ID
from diagnostics import diagnose_run
from encyclopedia import ENCYCLOPEDIA_SECTIONS
from engines import ALL_ENGINES, PIONEER_SINGLE_CYLINDER
from gearbox import PREBUILT_GEARBOXES, TRANSMISSION_CATALOG
from historical_challenges import CHALLENGES
from historical_records import HISTORICAL_TARGETS, next_historical_target
from management import (
    CampaignState,
    advance_turn,
    build_vehicle,
    complete_run,
    hire_engineer,
    load_campaign,
    research_chassis_technology,
    research_aerodynamics_technology,
    research_engine_technology,
    reset_campaign,
    save_campaign,
    sign_sponsor,
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
from simulation import run_simulation
from sponsors import SPONSOR_CATALOG
from tracks import BONNEVILLE_SALT_FLATS, available_tracks
from vehicle_designer import build_vehicle_from_garage_entry, design_vehicle

# A measured-mile speed above this is a sign of a bug (e.g. the "measured
# mile never reached" divide-by-zero regression), not a legitimately fast car.
IMPLAUSIBLE_SPEED_MPH = 2_000.0


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


class EngineeringDiagnosisTests(unittest.TestCase):
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
            vehicle = challenge.create_vehicle()
            track = challenge.track
            result = run_simulation(
                vehicle,
                track_miles=track.length_miles,
                measured_mile_start=track.measured_mile_start,
                track_friction_factor=track.friction_factor,
                air_density_kg_m3=track.air_density_kg_m3,
            )
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


class EncyclopediaRegressionTests(unittest.TestCase):
    def test_all_sections_print_without_crashing(self):
        for _, print_fn in ENCYCLOPEDIA_SECTIONS.values():
            print_fn()


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

    def test_full_research_tree_and_vehicle_build(self):
        campaign = CampaignState()
        campaign.team.cash = 10_000_000.0
        campaign.team.engineers = 10

        for node in AERODYNAMICS_TECHNOLOGY_TREE[:3]:
            research_aerodynamics_technology(campaign, node.technology_id)
        for node in CHASSIS_TECHNOLOGY_TREE:
            research_chassis_technology(campaign, node.technology_id)
        while True:
            available_aero = available_aerodynamics_technologies(
                campaign.research.aerodynamics_technology,
                campaign.research.chassis_technology,
            )
            if not available_aero:
                break
            research_aerodynamics_technology(campaign, available_aero[0].technology_id)
        for node in ENGINE_TECHNOLOGY_TREE:
            research_engine_technology(campaign, node.technology_id)
        self.assertEqual(
            current_chassis_era(campaign.research.chassis_technology),
            "Modern and Future Speed",
        )

        inputs = iter(["Regression Car", "1", "1", "1", "1", "yes"])
        with patch("builtins.input", lambda *a: next(inputs)):
            vehicle, cost_gbp, garage_entry = design_vehicle(campaign)
        self.assertIsNotNone(vehicle)

        build_vehicle(campaign, garage_entry, cost_gbp)
        self.assertEqual(len(campaign.garage.vehicles), 1)

        rebuilt = build_vehicle_from_garage_entry(garage_entry)
        self.assertEqual(rebuilt.name, "Regression Car")
        chassis = CHASSIS_BY_ID[garage_entry.chassis_id]
        expected_mass = (
            chassis.mass_kg
            + rebuilt.engine.mass_kg
            + rebuilt.gearbox.mass_kg
            + BRAKE_BY_NAME[garage_entry.brakes_name].mass_kg
        )
        self.assertEqual(vehicle.mass, expected_mass)
        self.assertEqual(rebuilt.mass, expected_mass)

        replacement_engine = ALL_ENGINES[1]
        rebuilt.engine = replacement_engine
        self.assertEqual(
            rebuilt.mass,
            expected_mass - vehicle.engine.mass_kg + replacement_engine.mass_kg,
        )

        mass_before_gearbox_change = rebuilt.mass
        replacement_gearbox = TRANSMISSION_CATALOG[1]
        rebuilt.gearbox = replacement_gearbox
        self.assertEqual(
            rebuilt.mass,
            mass_before_gearbox_change
            - vehicle.gearbox.mass_kg
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
