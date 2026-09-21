"""Broader regression coverage across Project Bonneville's systems.

Complements test_gearbox.py (shift-logic edge cases) and test_compatibility.py
(full car/engine/gearbox/track simulation matrix) by exercising the
management, research, vehicle designer, sponsorship, save/load, historical
challenge, and encyclopedia systems that aren't covered elsewhere.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import records
from cars import AVAILABLE_CARS
from chassis import CHASSIS_BY_ID
from encyclopedia import ENCYCLOPEDIA_SECTIONS
from engines import ALL_ENGINES
from gearbox import PREBUILT_GEARBOXES, TRANSMISSION_CATALOG
from historical_challenges import CHALLENGES
from management import (
    CampaignState,
    build_vehicle,
    hire_engineer,
    load_campaign,
    reset_campaign,
    research_chassis_technology,
    research_engine_technology,
    save_campaign,
    sign_sponsor,
)
from research import CHASSIS_TECHNOLOGY_TREE, ENGINE_TECHNOLOGY_TREE, current_chassis_era
from simulation import run_simulation
from sponsors import SPONSOR_CATALOG
from tracks import BONNEVILLE_SALT_FLATS
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


class EncyclopediaRegressionTests(unittest.TestCase):
    def test_all_sections_print_without_crashing(self):
        for _, print_fn in ENCYCLOPEDIA_SECTIONS.values():
            print_fn()


class CampaignProgressionRegressionTests(unittest.TestCase):
    def test_full_research_tree_and_vehicle_build(self):
        campaign = CampaignState()
        campaign.team.cash = 10_000_000.0
        campaign.team.engineers = 10

        for node in CHASSIS_TECHNOLOGY_TREE:
            research_chassis_technology(campaign, node.technology_id)
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
