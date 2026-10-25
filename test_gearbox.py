import unittest
from math import pi
from types import SimpleNamespace

from cars import create_blue_bird_1927, create_darracq_1905
from engines import (
    J47_TURBOJET,
    LIBERTY_V12,
    NAPIER_LION,
    PIONEER_SINGLE_CYLINDER,
    ROLLS_ROYCE_R,
)
from gearbox import (
    DIRECT_DRIVE,
    FIVE_SPEED_TRANSMISSION,
    FOUR_SPEED_TRANSMISSION,
    GOLDEN_ARROW_3_SPEED,
    THREE_SPEED_TRANSMISSION,
    TWO_SPEED_TRANSMISSION,
    Gearbox,
    adjust_gearbox_ratio,
    available_transmissions,
    effective_gearbox_reliability,
    gearbox_overload_fraction,
    recommended_transmission,
)
from reliability import GEAR_FAILURE, resolve_run_failure
from research import (
    CHASSIS_TECHNOLOGY_BY_ID,
    GEARBOX_TECHNOLOGY_BY_ID,
    GEARBOX_TECHNOLOGY_TREE,
    gearbox_rating_multiplier,
)
from simulation import run_simulation
from tracks import BONNEVILLE_SALT_FLATS, DAYTONA_BEACH


class GearboxDevelopmentTests(unittest.TestCase):
    def test_only_two_speed_is_available_before_gearbox_research(self):
        self.assertEqual(
            available_transmissions(PIONEER_SINGLE_CYLINDER, ()),
            (TWO_SPEED_TRANSMISSION,),
        )

    def test_researched_gearboxes_become_available(self):
        choices = available_transmissions(
            NAPIER_LION,
            ("three_speed_sliding_mesh_gearbox", "four_speed_racing_gearbox"),
        )
        self.assertEqual(
            choices,
            (TWO_SPEED_TRANSMISSION, THREE_SPEED_TRANSMISSION, FOUR_SPEED_TRANSMISSION),
        )

    def test_thrust_engines_only_use_direct_drive(self):
        self.assertEqual(available_transmissions(J47_TURBOJET, ()), (DIRECT_DRIVE,))

    def test_gearbox_technology_prerequisites_exist(self):
        known = set(CHASSIS_TECHNOLOGY_BY_ID) | set(GEARBOX_TECHNOLOGY_BY_ID)
        for node in GEARBOX_TECHNOLOGY_TREE:
            self.assertTrue(set(node.prerequisites) <= known, node.technology_id)
        for gearbox in (THREE_SPEED_TRANSMISSION, FOUR_SPEED_TRANSMISSION, FIVE_SPEED_TRANSMISSION):
            self.assertIn(gearbox.required_technology, GEARBOX_TECHNOLOGY_BY_ID)

    def test_rating_improvements_stack(self):
        self.assertEqual(gearbox_rating_multiplier(()), 1.0)
        self.assertEqual(
            gearbox_rating_multiplier(("case_hardened_gears", "alloy_steel_gear_sets")),
            1.5,
        )

    def test_recommended_transmission_respects_research_and_rating(self):
        self.assertEqual(
            recommended_transmission(LIBERTY_V12, ("three_speed_sliding_mesh_gearbox",)),
            THREE_SPEED_TRANSMISSION,
        )
        self.assertEqual(recommended_transmission(LIBERTY_V12, ()), TWO_SPEED_TRANSMISSION)
        self.assertEqual(recommended_transmission(ROLLS_ROYCE_R), FIVE_SPEED_TRANSMISSION)


class GearboxOverloadTests(unittest.TestCase):
    def test_engine_within_rating_has_no_penalty(self):
        self.assertEqual(
            effective_gearbox_reliability(TWO_SPEED_TRANSMISSION, PIONEER_SINGLE_CYLINDER),
            TWO_SPEED_TRANSMISSION.reliability,
        )

    def test_overload_reduces_reliability(self):
        engine = SimpleNamespace(power_hp=150.0, torque_curve_type="early_piston")
        self.assertAlmostEqual(
            gearbox_overload_fraction(TWO_SPEED_TRANSMISSION, engine), 0.25
        )
        self.assertAlmostEqual(
            effective_gearbox_reliability(TWO_SPEED_TRANSMISSION, engine),
            TWO_SPEED_TRANSMISSION.reliability - 0.125,
        )

    def test_extreme_overload_is_floored(self):
        self.assertEqual(
            effective_gearbox_reliability(TWO_SPEED_TRANSMISSION, ROLLS_ROYCE_R), 0.05
        )

    def test_rating_multiplier_removes_overload(self):
        engine = SimpleNamespace(power_hp=150.0, torque_curve_type="early_piston")
        self.assertEqual(
            gearbox_overload_fraction(TWO_SPEED_TRANSMISSION, engine, 1.25), 0.0
        )

    def test_thrust_engines_never_overload_gearbox(self):
        self.assertEqual(gearbox_overload_fraction(DIRECT_DRIVE, J47_TURBOJET), 0.0)

    def test_overload_raises_gear_failure_probability(self):
        team = SimpleNamespace(engineers=1, mechanics=2)
        perfect_engine = SimpleNamespace(
            reliability=1.0, power_hp=100.0, torque_curve_type="early_piston"
        )
        overloaded_engine = SimpleNamespace(
            reliability=1.0, power_hp=240.0, torque_curve_type="early_piston"
        )
        within = resolve_run_failure(
            perfect_engine, 100.0, team, random_value=0.99, gearbox=TWO_SPEED_TRANSMISSION
        )
        overloaded = resolve_run_failure(
            overloaded_engine, 100.0, team, random_value=0.99, gearbox=TWO_SPEED_TRANSMISSION
        )
        improved = resolve_run_failure(
            overloaded_engine, 100.0, team, random_value=0.99,
            gearbox=TWO_SPEED_TRANSMISSION, gearbox_rating_multiplier=2.0,
        )
        self.assertGreater(overloaded.failure_probability, within.failure_probability)
        self.assertAlmostEqual(improved.failure_probability, within.failure_probability)

    def test_overloaded_gearbox_failure_is_gear_failure(self):
        engine = SimpleNamespace(reliability=1.0, power_hp=2_000.0, torque_curve_type="early_piston")
        team = SimpleNamespace(engineers=0, mechanics=0)
        outcome = resolve_run_failure(
            engine, 250.0, team, random_value=0.5, gearbox=TWO_SPEED_TRANSMISSION
        )
        self.assertEqual(outcome.failure_type, GEAR_FAILURE)


class GearboxShiftTests(unittest.TestCase):
    def test_final_drive_adjustment_updates_existing_gearbox(self):
        vehicle = create_blue_bird_1927(engine=NAPIER_LION)
        changed = adjust_gearbox_ratio(vehicle.gearbox, None, -0.25)

        self.assertTrue(changed)
        self.assertEqual(vehicle.gearbox.final_drive_ratio, 0.85)

    def test_gear_adjustment_updates_selected_ratio(self):
        vehicle = create_blue_bird_1927(engine=NAPIER_LION)
        changed = adjust_gearbox_ratio(vehicle.gearbox, 1, -0.15)

        self.assertTrue(changed)
        self.assertEqual(vehicle.gearbox.gears[1], 1.45)

    def test_gear_adjustment_rejects_invalid_ratio(self):
        vehicle = create_blue_bird_1927(engine=NAPIER_LION)
        original_ratios = vehicle.gearbox.gears
        changed = adjust_gearbox_ratio(vehicle.gearbox, 1, 20.0)

        self.assertFalse(changed)
        self.assertEqual(vehicle.gearbox.gears, original_ratios)

    def test_preset_vehicle_mass_tracks_component_weight_changes(self):
        vehicle = create_blue_bird_1927(engine=NAPIER_LION)
        original_mass = vehicle.mass

        vehicle.engine = ROLLS_ROYCE_R

        self.assertEqual(
            vehicle.mass,
            original_mass - NAPIER_LION.mass_kg + ROLLS_ROYCE_R.mass_kg,
        )

    def test_measured_mile_starting_at_zero_includes_initial_timestep(self):
        vehicle = create_blue_bird_1927(engine=NAPIER_LION)

        result = run_simulation(
            vehicle,
            track_miles=1.0,
            measured_mile_start=0.0,
            measured_mile_length=0.5,
            time_step=0.1,
        )

        self.assertGreater(result.measured_mile_time_seconds, 0.0)
        self.assertLess(
            result.measured_mile_time_seconds,
            result.total_time_seconds,
        )

    def test_telemetry_rpm_matches_recorded_gear(self):
        vehicle = create_blue_bird_1927(engine=NAPIER_LION)

        result = run_simulation(
            vehicle,
            track_miles=10.0,
            measured_mile_start=4.0,
            measured_mile_length=1.0,
        )

        for sample in result.telemetry:
            wheel_revolutions_per_second = (
                sample.speed_mph / 2.23694/ (2 * pi * vehicle.wheel_radius_m)
            )
            expected_rpm = (
                wheel_revolutions_per_second
                * 60
                * vehicle.gearbox.gears[sample.gear - 1]
                * vehicle.gearbox.final_drive_ratio
            )
            self.assertAlmostEqual(sample.engine_rpm, expected_rpm, delta=25)

    def test_shift_occurs_before_engine_redline(self):
        gearbox = Gearbox(
            name="Test 3-Speed",
            gears=(2.4, 1.6, 1.0),
            shift_up_rpm=2600,
            shift_down_rpm=1200,
            final_drive=1.1,
        )

        gearbox.shift_if_needed(2250, rpm_limit=2200)
        self.assertIsNotNone(gearbox.pending_gear)
        self.assertEqual(gearbox.current_gear, 1)

        gearbox.advance_shift(1.0)
        self.assertEqual(gearbox.current_gear, 2)

    def test_run_shifts_before_engine_redline_when_gearbox_threshold_is_higher(self):
        engine = NAPIER_LION
        vehicle = create_blue_bird_1927(engine=engine)

        result = run_simulation(
            vehicle,
            track_miles=DAYTONA_BEACH.length_miles,
            measured_mile_start=DAYTONA_BEACH.measured_mile_start,
            track_friction_factor=DAYTONA_BEACH.friction_factor,
            air_density_kg_m3=DAYTONA_BEACH.air_density_kg_m3,
        )

        self.assertGreater(result.gear_change_count, 0)
        self.assertIn(2, {sample.gear for sample in result.telemetry})

    def test_high_output_engine_shifts_before_it_stalls_below_redline(self):
        engine = ROLLS_ROYCE_R
        vehicle = create_darracq_1905()
        vehicle.engine = engine
        vehicle.power = engine.power_hp
        vehicle.peak_torque_nm = engine.torque_nm
        vehicle.gearbox = GOLDEN_ARROW_3_SPEED

        result = run_simulation(
            vehicle,
            track_miles=BONNEVILLE_SALT_FLATS.length_miles,
            measured_mile_start=BONNEVILLE_SALT_FLATS.measured_mile_start,
            track_friction_factor=BONNEVILLE_SALT_FLATS.friction_factor,
            air_density_kg_m3=BONNEVILLE_SALT_FLATS.air_density_kg_m3,
        )

        self.assertGreater(result.gear_change_count, 0)
        self.assertIn(2, {sample.gear for sample in result.telemetry})


if __name__ == "__main__":
    unittest.main()
