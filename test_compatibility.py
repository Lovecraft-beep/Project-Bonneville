import unittest
from copy import deepcopy

from cars import AVAILABLE_CARS
from engines import ALL_ENGINES
from gearbox import PREBUILT_GEARBOXES
from simulation import run_simulation
from tracks import AVAILABLE_TRACKS


class CombinationCompatibilityTests(unittest.TestCase):
    def test_all_car_engine_gearbox_track_combinations_run(self):
        engines = list(ALL_ENGINES)
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
                        # Turbojet/rocket engines are intended for direct-drive
                        # cars, not period multi-speed gearboxes, so pairing
                        # them here can legitimately stay in first gear. Some
                        # underpowered pairings also legitimately plateau
                        # (power-limited) below the shift RPM rather than
                        # failing to shift due to a logic bug: shift_if_needed
                        # shifts deterministically as soon as engine_rpm meets
                        # its threshold, so only flag cases that actually
                        # reached that exact threshold without shifting.
                        max_engine_rpm_seen = max(
                            (sample.engine_rpm for sample in result.telemetry),
                            default=0,
                        )
                        shift_threshold = min(
                            gearbox.shift_up_rpm, engine.max_rpm * 0.90
                        )
                        if (
                            engine.torque_curve_type not in ("turbojet", "rocket")
                            and gearbox.gear_count > 1
                            and result.peak_speed_mph > 20
                            and gears == {1}
                            and max_engine_rpm_seen >= shift_threshold - 1
                        ):
                            stuck_cases.append(
                                f"{car_key}/{engine.name}/{gearbox.name}/{track.name}"
                            )

        self.assertFalse(failures, "Combination failures: " + "; ".join(failures[:5]))
        self.assertFalse(stuck_cases, "Stuck in first gear: " + "; ".join(stuck_cases))


if __name__ == "__main__":
    unittest.main()
