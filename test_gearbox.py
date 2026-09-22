import unittest
from math import pi

from cars import create_blue_bird_1927, create_darracq_1905
from engines import NAPIER_LION, ROLLS_ROYCE_R
from gearbox import GOLDEN_ARROW_3_SPEED, Gearbox
from simulation import run_simulation
from tracks import BONNEVILLE_SALT_FLATS, DAYTONA_BEACH


class GearboxShiftTests(unittest.TestCase):
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
                sample.speed_mph / 2.23694
                / (2 * pi * vehicle.wheel_radius_m)
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
