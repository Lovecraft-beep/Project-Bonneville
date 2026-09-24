"""Diagnostic logging for the currently built test vehicle."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

DIAGNOSTIC_LOG_FILE = Path(__file__).with_name("test_vehicle_diagnostics.log")


@dataclass(frozen=True)
class RunDiagnosis:
    """The most actionable engineering problem found in a test run."""

    problem: str
    evidence: str
    recommended_component: str
    research_branch: str


def diagnose_run(vehicle, result):
    """Turn run telemetry into one actionable engineering recommendation."""
    if any(sample.brake_fade for sample in result.telemetry):
        return RunDiagnosis(
            "Brake fade",
            f"Brakes reached {result.maximum_brake_temperature_c:.0f} C.",
            "brakes",
            "brake technology",
        )

    if result.wheelspin_event_count:
        return RunDiagnosis(
            "Traction loss",
            f"The run recorded {result.wheelspin_event_count} wheelspin event(s).",
            "tyres",
            "tyre technology",
        )

    highest_gear = max((sample.gear for sample in result.telemetry), default=1)
    if vehicle.gearbox.gear_count > 1 and highest_gear == 1:
        return RunDiagnosis(
            "Power delivery is trapped in first gear",
            "Telemetry never recorded an upshift during the run.",
            "gearbox",
            "gearbox technology",
        )

    if result.average_acceleration_g < 0.1:
        return RunDiagnosis(
            "Insufficient acceleration",
            f"Average acceleration was {result.average_acceleration_g:.2f} G.",
            "engine",
            "engine technology",
        )

    return RunDiagnosis(
        "Aerodynamic drag",
        f"Peak speed plateaued at {result.peak_speed_mph:.1f} mph.",
        "chassis",
        "chassis and aerodynamic technology",
    )


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
    diagnosis = diagnose_run(vehicle, result)
    with DIAGNOSTIC_LOG_FILE.open("a", encoding="utf-8") as log_file:
        log_file.write("=" * 80 + "\n")
        log_file.write(f"RUN: {datetime.now().isoformat(timespec='seconds')}\n")
        log_file.write(f"Track: {track.name}\n")
        log_file.write("Vehicle configuration:\n")
        log_file.write(json.dumps(_vehicle_details(vehicle), indent=2, default=list))
        log_file.write("\nResult:\n")
        log_file.write(json.dumps(asdict(result), indent=2, default=list))
        log_file.write("\nEngineering diagnosis:\n")
        log_file.write(json.dumps(asdict(diagnosis), indent=2, default=list))
        if outcome is not None:
            log_file.write("\nFailure outcome:\n")
            log_file.write(json.dumps(asdict(outcome), indent=2, default=list))
        log_file.write("\n\n")
