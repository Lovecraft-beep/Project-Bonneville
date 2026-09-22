"""Diagnostic logging for the currently built test vehicle."""

from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path


DIAGNOSTIC_LOG_FILE = Path(__file__).with_name("test_vehicle_diagnostics.log")


def _vehicle_details(vehicle):
    return {
        "name": vehicle.name,
        "model_year": vehicle.model_year,
        "mass_kg": vehicle.mass,
        "drag_coefficient": vehicle.cd,
        "frontal_area_m2": vehicle.area,
        "tyre_grip_factor": vehicle.tyre_grip_factor,
        "wheel_radius_m": vehicle.wheel_radius_m,
        "engine": {
            "name": vehicle.engine.name,
            "power_hp": vehicle.engine.power_hp,
            "torque_nm": vehicle.engine.torque_nm,
            "max_rpm": vehicle.engine.max_rpm,
            "reliability": vehicle.engine.reliability,
        },
        "gearbox": {
            "name": vehicle.gearbox.name,
            "gears": vehicle.gearbox.gears,
            "final_drive": vehicle.gearbox.final_drive,
            "efficiency": vehicle.gearbox.efficiency,
        },
        "brakes": {
            "name": vehicle.brakes.name,
            "max_braking_g": vehicle.brakes.max_braking_g,
            "efficiency": vehicle.brakes.efficiency,
        },
    }


def reset_vehicle_log(vehicle):
    """Overwrite the diagnostic log for a newly built vehicle."""
    with DIAGNOSTIC_LOG_FILE.open("w", encoding="utf-8") as log_file:
        log_file.write("PROJECT BONNEVILLE TEST VEHICLE DIAGNOSTICS\n")
        log_file.write(f"Created: {datetime.now().isoformat(timespec='seconds')}\n")
        log_file.write(json.dumps(_vehicle_details(vehicle), indent=2, default=list))
        log_file.write("\n\n")


def append_run_log(vehicle, track, result, outcome=None):
    """Append one run's setup, result, outcome, and complete telemetry."""
    with DIAGNOSTIC_LOG_FILE.open("a", encoding="utf-8") as log_file:
        log_file.write("=" * 80 + "\n")
        log_file.write(f"RUN: {datetime.now().isoformat(timespec='seconds')}\n")
        log_file.write(f"Track: {track.name}\n")
        log_file.write("Vehicle configuration:\n")
        log_file.write(json.dumps(_vehicle_details(vehicle), indent=2, default=list))
        log_file.write("\nResult:\n")
        log_file.write(json.dumps(asdict(result), indent=2, default=list))
        if outcome is not None:
            log_file.write("\nFailure outcome:\n")
            log_file.write(json.dumps(asdict(outcome), indent=2, default=list))
        log_file.write("\n\n")
