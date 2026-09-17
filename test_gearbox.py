import unittest

from cars import create_blue_bird_1927
from cars import create_darracq_1905
from engines import NAPIER_LION_VARIANTS
from gearbox import GOLDEN_ARROW_3_SPEED, Gearbox
from tracks import BONNEVILLE_SALT_FLATS, DAYTONA_BEACH
from simulation import run_simulation


class GearboxShiftTests(unittest.TestCase):
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
        engine = NAPIER_LION_VARIANTS[3]
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
        engine = NAPIER_LION_VARIANTS[8]
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
