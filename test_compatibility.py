import unittest
from copy import deepcopy

from cars import AVAILABLE_CARS
from engines import (
    DARRACQ_V8_25_LITRE,
    NAPIER_LION_VARIANTS,
    STANLEY_STEAM_ENGINE,
    WELCH_HEMI,
)
from gearbox import PREBUILT_GEARBOXES
from simulation import run_simulation
from tracks import AVAILABLE_TRACKS


class CombinationCompatibilityTests(unittest.TestCase):
    def test_all_car_engine_gearbox_track_combinations_run(self):
        engines = [
            *NAPIER_LION_VARIANTS,
            WELCH_HEMI,
            STANLEY_STEAM_ENGINE,
            DARRACQ_V8_25_LITRE,
        ]
        failures = []
        stuck_cases = []

        for car_key, factory in AVAILABLE_CARS.items():
            for engine in engines:
                for gearbox in PREBUILT_GEARBOXES:
                    for track in AVAILABLE_TRACKS.values():
                        vehicle = factory()
                        vehicle.engine = engine
                        vehicle.power = engine.power_hp
                        vehicle.peak_torque_nm = engine.torque_nm
                        vehicle.gearbox = deepcopy(gearbox)
                        try:
                            result = run_simulation(
                                vehicle,
                                track_miles=track.length_miles,
                                measured_mile_start=track.measured_mile_start,
                                track_friction_factor=track.friction_factor,
                                air_density_kg_m3=track.air_density_kg_m3,
                            )
                        except Exception as exc:  # pragma: no cover - diagnostic detail
                            failures.append(
                                f"{car_key}/{engine.name}/{gearbox.name}/{track.name}: {exc}"
                            )
                            continue

                        gears = {sample.gear for sample in result.telemetry}
                        if gearbox.gear_count > 1 and result.peak_speed_mph > 20 and gears == {1}:
                            stuck_cases.append(
                                f"{car_key}/{engine.name}/{gearbox.name}/{track.name}"
                            )

        self.assertFalse(failures, "Combination failures: " + "; ".join(failures[:5]))
        self.assertFalse(stuck_cases, "Stuck in first gear: " + "; ".join(stuck_cases))


if __name__ == "__main__":
    unittest.main()
