"""Diagnostic logging for the currently built test vehicle."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from math import pi
from pathlib import Path

from gearbox import estimate_power_limited_speed_mph
from research import (
    AERODYNAMICS_TECHNOLOGY_TREE,
    BRAKE_TECHNOLOGY_TREE,
    ENGINE_TECHNOLOGY_TREE,
    GEARBOX_TECHNOLOGY_TREE,
    TYRE_TECHNOLOGY_TREE,
    TECHNOLOGY_NAME_BY_ID,
    available_branch_technologies,
)

DIAGNOSTIC_LOG_FILE = Path(__file__).with_name("test_vehicle_diagnostics.log")


@dataclass(frozen=True)
class RunDiagnosis:
    """The most actionable engineering problem found in a test run."""

    problem: str
    evidence: str
    recommended_component: str
    research_branch: str


@dataclass(frozen=True)
class GearRatioSuggestion:
    final_drive: float
    gears: tuple[float, ...]
    description: str
    changes_needed: bool = True


# Mechanics work by eye and feel, so ratios are only set to the nearest 0.05.
MECHANIC_RATIO_STEP = 0.05
MECHANIC_EXTRA_LEGS = 1.10


def _mechanic_round(ratio, low, high):
    stepped = round(ratio / MECHANIC_RATIO_STEP) * MECHANIC_RATIO_STEP
    return round(min(high, max(low, stepped)), 2)


def _peak_power_rpm(engine):
    rpms = [engine.max_rpm * fraction / 100 for fraction in range(30, 99)]
    return max(rpms, key=lambda rpm: engine.torque_at_rpm(rpm) * rpm)


def _rpm_at_speed(speed_mph, overall_ratio, wheel_radius_m):
    speed_mps = speed_mph / 2.23694
    return speed_mps / (2 * pi * wheel_radius_m) * 60 * overall_ratio


def suggest_gear_ratio_adjustment(vehicle, result, track_friction_factor=1.0):
    """Suggest a full set of ratios matched to the engine's power and torque."""
    gearbox = vehicle.gearbox
    engine = vehicle.engine
    if (
        gearbox.gear_count < 2
        or engine.torque_curve_type in ("turbojet", "rocket")
        or not result.telemetry
    ):
        return None
    driven = [
        sample for sample in result.telemetry
        if getattr(sample, "phase", "accelerating") != "decelerating"
    ] or result.telemetry
    peak_sample = max(driven, key=lambda sample: sample.speed_mph)
    if peak_sample.speed_mph <= 0:
        return None

    radius = vehicle.wheel_radius_m
    top_gear = gearbox.gears[-1]
    power_rpm = _peak_power_rpm(engine)
    still_accelerating = getattr(peak_sample, "acceleration_g", 0.0) >= 0.02
    rev_limited = (
        peak_sample.gear == gearbox.gear_count
        and peak_sample.engine_rpm >= engine.max_rpm * 0.93
        and not still_accelerating
    )
    target_speed = peak_sample.speed_mph
    target_rpm = power_rpm
    if rev_limited:
        target_speed = max(
            target_speed,
            min(
                estimate_power_limited_speed_mph(vehicle, engine),
                target_speed * MECHANIC_EXTRA_LEGS,
            ),
        )
    elif still_accelerating:
        # Track ran out before the car did: use the whole rev range in top.
        target_rpm = engine.max_rpm * 0.95

    overall_top = target_rpm / _rpm_at_speed(target_speed, 1.0, radius)
    final_drive = _mechanic_round(overall_top / top_gear, 0.5, 6.0)
    top_gear = _mechanic_round(overall_top / final_drive, 0.5, 5.0)

    # First gear: peak torque just reaches the tyres' grip limit.
    traction_force = (
        vehicle.tyre_grip_factor * track_friction_factor * vehicle.mass * 9.81
    )
    first_gear = _mechanic_round(
        traction_force * radius
        / (engine.torque_nm * final_drive * gearbox.efficiency),
        min(5.0, top_gear * 1.2),
        5.0,
    )

    # Middle gears: even geometric steps so each shift lands at the same RPM drop.
    count = gearbox.gear_count
    step = (top_gear / first_gear) ** (1 / (count - 1))
    gears = tuple(
        _mechanic_round(first_gear * step**index, 0.5, 5.0)
        for index in range(count - 1)
    ) + (top_gear,)

    changes_needed = (
        abs(final_drive - gearbox.final_drive_ratio) >= MECHANIC_RATIO_STEP
        or any(
            abs(new - old) >= MECHANIC_RATIO_STEP
            for new, old in zip(gears, gearbox.gears)
        )
    )
    peak_rpm_now = peak_sample.engine_rpm
    if rev_limited:
        top_note = (
            f"She sat on the rev limit in top at {peak_sample.speed_mph:.0f} mph "
            f"({peak_rpm_now:,.0f} rpm). Gear her for about {target_speed:.0f} mph "
            f"with best power near {power_rpm:,.0f} rpm."
        )
    elif still_accelerating:
        top_note = (
            f"She was still pulling at {peak_sample.speed_mph:.0f} mph "
            f"({peak_rpm_now:,.0f} rpm in gear {peak_sample.gear}) when the course ran out. "
            f"Gear her to finish near {target_rpm:,.0f} rpm in top."
        )
    else:
        top_note = (
            f"She topped out at {peak_sample.speed_mph:.0f} mph turning "
            f"{peak_rpm_now:,.0f} rpm in gear {peak_sample.gear}; best power is "
            f"near {power_rpm:,.0f} rpm."
        )
    shift_rpm = min(gearbox.shift_up_rpm, engine.max_rpm * 0.90)
    drop_rpm = shift_rpm * step
    torque_rpm = max(
        (engine.max_rpm * fraction / 100 for fraction in range(10, 99)),
        key=engine.torque_at_rpm,
    )
    spacing_note = (
        f" Each upshift drops to about {drop_rpm:,.0f} rpm, "
        + (
            "right in the torque band."
            if drop_rpm >= torque_rpm * 0.85
            else "below the torque band, so she bogs down after each change. "
            "The gaps are too wide for this box; a gearbox with more speeds would help."
        )
    )
    if not changes_needed:
        return GearRatioSuggestion(
            gearbox.final_drive_ratio,
            tuple(gearbox.gears),
            f"{top_note} The current ratios are about where I'd set them.",
            changes_needed=False,
        )
    ratio_list = " / ".join(f"{ratio:.2f}" for ratio in gears)
    current_list = " / ".join(f"{ratio:.2f}" for ratio in gearbox.gears)
    return GearRatioSuggestion(
        final_drive,
        gears,
        f"{top_note} Final drive {gearbox.final_drive_ratio:.2f} -> {final_drive:.2f}. "
        f"Gears {current_list} -> {ratio_list}; first gear puts peak torque "
        f"right at the tyres' grip.{spacing_note}",
    )


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
        f"Peak speed reached {result.peak_speed_mph:.1f} mph. "
        "Review aerodynamic drag before the next test.",
        "chassis",
        "chassis and aerodynamic technology",
    )


@dataclass(frozen=True)
class EngineeringReport:
    vehicle_name: str
    track_name: str
    diagnosis: RunDiagnosis
    recommendations: tuple[str, ...]
    research_branch: str
    run_status: str
    completed: bool
    measured_mile_speed_mph: float
    comparison: str
    target_assessment: str


def _research_recommendation(campaign, branch, tree):
    if campaign is None:
        return f"Explore {branch.lower()} research in the campaign workshop."
    attribute = {"Tyres": "tyre", "Brakes": "brake"}.get(branch, branch.lower())
    researched = getattr(campaign.research, f"{attribute}_technology")
    node = next((item for item in tree if item.technology_id not in researched), None)
    if node is None:
        return f"Review installation of your researched {branch.lower()} technology in the Garage."
    project = next(
        (item for item in campaign.engineering_projects if item.technology_id == node.technology_id),
        None,
    )
    if project is not None:
        return f"Continue {node.name}: {project.turns_remaining} turn(s) remaining."
    available = available_branch_technologies(
        tree, researched, campaign.research.chassis_technology
    )
    if node not in available:
        known = set(researched) | set(campaign.research.chassis_technology)
        missing = ", ".join(
            TECHNOLOGY_NAME_BY_ID[item] for item in node.prerequisites if item not in known
        )
        return f"Work toward {node.name}; first research {missing}."
    blockers = []
    if campaign.team.cash < node.cost_gbp:
        blockers.append(f"raise GBP {node.cost_gbp - campaign.team.cash:,.0f} more")
    if campaign.available_engineers < node.engineers_required:
        blockers.append(f"free {node.engineers_required - campaign.available_engineers} engineer(s)")
    requirements = f"GBP {node.cost_gbp:,.0f}, {node.engineers_required} engineer(s), {node.turns_required} turns"
    if blockers:
        return f"Prepare {node.name} ({requirements}): {'; '.join(blockers)}."
    return f"Research {node.name} ({requirements})."


def create_engineering_report(
    vehicle, track, result, campaign=None, outcome=None, previous_report=None,
    target=None, is_record_attempt=False, record_attempt_in_progress=False,
    record_attempt_average_mph=None,
):
    """Build a read-only debrief from one run and its campaign context."""
    diagnosis = diagnose_run(vehicle, result)
    failed = outcome is not None and outcome.failed
    if failed:
        failure_name = outcome.failure_type.name if outcome.failure_type else "Mechanical failure"
        diagnosis = RunDiagnosis(
            failure_name,
            f"Run aborted. Failure probability was {outcome.failure_probability:.1%}. "
            + ("Trackside repair was possible." if outcome.repaired else "Workshop repair is required."),
            {
                "gear_failure": "gearbox", "tyre_burst": "tyres",
                "brake_fade": "brakes", "steering_vibration": "chassis",
            }.get(outcome.failure_type.failure_id if outcome.failure_type else "", "engine"),
            "reliability",
        )
    plans = {
        "brakes": ("Brakes", BRAKE_TECHNOLOGY_TREE, "Fit stronger brakes in the Garage.", "Retest braking on the same venue before a record attempt."),
        "tyres": ("Tyres", TYRE_TECHNOLOGY_TREE, "Review tyre grip when selecting a chassis.", "Use a higher-grip venue for the next test."),
        "gearbox": ("Gearbox", GEARBOX_TECHNOLOGY_TREE, "Adjust gear ratios and final drive in the Garage.", "Retest and check that telemetry records upshifts."),
        "engine": ("Engine", ENGINE_TECHNOLOGY_TREE, "Review engine choice and tuning in the Garage.", "Retest acceleration on the same venue before a record attempt."),
        "chassis": ("Aerodynamics", AERODYNAMICS_TECHNOLOGY_TREE, "Design a vehicle with a lower-drag chassis.", "Review a more powerful engine, including its reliability trade-off."),
    }
    branch, tree, modification, next_test = plans[diagnosis.recommended_component]
    recommendations = (
        _research_recommendation(campaign, branch, tree), modification, next_test,
    )
    if failed:
        recommendations = (
            "Inspect the failed component and review team mechanics and workshop support.",
            recommendations[0], "Complete a successful test before another record attempt.",
        )
    comparison = "No comparable completed run at this venue yet."
    if failed:
        comparison = "Aborted run: simulated speeds are not a valid performance comparison."
    elif (
        previous_report is not None and previous_report.completed
        and previous_report.vehicle_name == vehicle.name
        and previous_report.track_name == track.name
    ):
        change = result.measured_mile_speed_mph - previous_report.measured_mile_speed_mph
        comparison = f"Measured mile {change:+.1f} mph versus the previous completed run here."
    target_assessment = "Sandbox test: no campaign record is at stake."
    if campaign is not None:
        target_assessment = "All historical campaign targets have been completed."
        if failed:
            target_assessment = "No record credited: this run was aborted."
        elif target is not None:
            assessed_speed = (
                result.measured_mile_speed_mph
                if record_attempt_average_mph is None
                else record_attempt_average_mph
            )
            gap = target.speed_mph - assessed_speed
            benchmark = f"{target.year} {target.vehicle}: {target.speed_mph:.1f} mph"
            if record_attempt_in_progress:
                target_assessment = (
                    f"Outbound pass {result.measured_mile_speed_mph:.1f} mph; "
                    f"return pass required before assessing {benchmark}."
                )
            elif gap > 0:
                target_assessment = f"{gap:.1f} mph short of {benchmark}. Continue development."
            elif is_record_attempt:
                target_assessment = f"Historical benchmark beaten: {benchmark}."
            else:
                target_assessment = f"Test pace meets {benchmark}. Schedule an official record attempt."
    return EngineeringReport(
        vehicle.name, track.name, diagnosis, recommendations, branch,
        "ABORTED / SIMULATION ESTIMATES ONLY" if failed else "COMPLETED",
        not failed, result.measured_mile_speed_mph, comparison, target_assessment,
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


def clear_diagnostic_log(path=DIAGNOSTIC_LOG_FILE):
    """Delete the diagnostic log so a new campaign starts with a clean history."""
    path.unlink(missing_ok=True)


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
