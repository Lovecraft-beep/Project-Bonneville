"""Basic time-and-distance simulation for a land-speed run."""

from dataclasses import dataclass


METRES_PER_MILE = 1609.344
HORSEPOWER_IN_WATTS = 745.7
STANDARD_AIR_DENSITY = 1.2


@dataclass
class TelemetrySample:
    time_seconds: float
    distance_miles: float
    speed_mph: float
    engine_rpm: int
    acceleration_g: float
    wheelspin: bool
    gear: int
    shifting: bool
    brake_temperature_c: float
    brake_fade: bool
    phase: str


@dataclass
class SimulationResult:
    track_miles: float
    measured_mile_time_seconds: float
    measured_mile_speed_mph: float
    peak_speed_mph: float
    total_time_seconds: float
    total_distance_miles: float
    average_acceleration_g: float
    full_throttle_seconds: float
    gear_change_count: int
    wheelspin_event_count: int
    maximum_brake_temperature_c: float
    completed: bool
    telemetry: list[TelemetrySample]


def calculate_drag_force(
    vehicle,
    speed_m_per_second,
    air_density_kg_m3=STANDARD_AIR_DENSITY,
):
    """Return aerodynamic drag in newtons at the given speed."""
    return (
        0.5
        * vehicle.cd
        * air_density_kg_m3
        * speed_m_per_second**2
        * vehicle.area
    )


def calculate_wheel_torque(vehicle):
    """Return current-gear wheel torque before traction limits are applied."""
    return (
        vehicle.peak_torque_nm
        * vehicle.gearbox.current_ratio
        * vehicle.gearbox.final_drive_ratio
        * vehicle.gearbox.efficiency
    )


def run_simulation(
    vehicle,
    track_miles=10.0,
    measured_mile_start=4.0,
    measured_mile_length=1.0,
    time_step=0.1,
    track_friction_factor=1.0,
    air_density_kg_m3=STANDARD_AIR_DENSITY,
):
    """Simulate acceleration, a measured mile, and braking on a track."""
    if track_miles <= 0:
        raise ValueError("track_miles must be greater than zero")
    if measured_mile_start < 0 or measured_mile_length <= 0:
        raise ValueError("measured mile must have a positive length and start")
    if measured_mile_start + measured_mile_length > track_miles:
        raise ValueError("measured mile must fit within the track")
    if (
        vehicle.mass <= 0
        or vehicle.power <= 0
        or vehicle.cd <= 0
        or vehicle.area <= 0
        or vehicle.tyre_grip_factor <= 0
        or vehicle.peak_torque_nm <= 0
        or vehicle.wheel_radius_m <= 0
        or track_friction_factor <= 0
        or air_density_kg_m3 <= 0
    ):
        raise ValueError("vehicle values and friction factors must be greater than zero")

    rolling_resistance = 0.015
    drivetrain_efficiency = 0.85
    track_distance = track_miles * METRES_PER_MILE
    measured_start = measured_mile_start * METRES_PER_MILE
    measured_end = (measured_mile_start + measured_mile_length) * METRES_PER_MILE
    power_watts = vehicle.power * HORSEPOWER_IN_WATTS * drivetrain_efficiency
    effective_traction = vehicle.tyre_grip_factor * track_friction_factor
    maximum_traction_force = effective_traction * vehicle.mass * 9.81
    if vehicle.brakes is None:
        raise ValueError("vehicle must have a brake system")
    vehicle.brakes.reset()
    vehicle.gearbox.current_gear = 1

    distance = 0.0
    speed = 0.0
    elapsed = 0.0
    peak_speed = 0.0
    measured_start_time = None
    measured_end_time = None
    next_telemetry_time = 1.0
    previous_gear = 1
    previous_wheelspin = False
    gear_change_count = 0
    wheelspin_event_count = 0
    vehicle.gearbox.current_gear = 1
    vehicle.gearbox.pending_gear = None
    vehicle.gearbox.shift_elapsed = 0.0
    telemetry = [
        TelemetrySample(0.0, 0.0, 0.0, 0, 0.0, False, 1, False, 20.0, False, "accelerating")
    ]

    while distance < track_distance and elapsed < 3600:
        previous_distance = distance
        previous_speed = speed
        wheelspin = False

        if distance < measured_end:
            engine_rpm = vehicle.gearbox.engine_rpm(speed, vehicle.wheel_radius_m)
            vehicle.gearbox.shift_if_needed(engine_rpm)
            engine_rpm = vehicle.gearbox.engine_rpm(speed, vehicle.wheel_radius_m)
            drag_force = calculate_drag_force(
                vehicle,
                speed,
                air_density_kg_m3,
            )
            rolling_force = vehicle.mass * 9.81 * rolling_resistance
            power_limited_force = power_watts / max(speed, 1.0)
            torque_limited_force = (
                calculate_wheel_torque(vehicle)
                * vehicle.gearbox.clutch_torque_multiplier()
                / vehicle.wheel_radius_m
            )
            requested_force = min(power_limited_force, torque_limited_force)
            wheelspin = requested_force > maximum_traction_force
            available_force = min(requested_force, maximum_traction_force)
            acceleration = (available_force - drag_force - rolling_force) / vehicle.mass
            speed = max(0.0, speed + acceleration * time_step)
            vehicle.gearbox.advance_shift(time_step)
        else:
            engine_rpm = vehicle.gearbox.engine_rpm(speed, vehicle.wheel_radius_m)
            vehicle.gearbox.shift_if_needed(engine_rpm, decelerating=True)
            brake_force = vehicle.brakes.calculate_force(
                vehicle.mass,
                maximum_traction_force,
            )
            vehicle.brakes.update_temperature(brake_force, speed, time_step)
            brake_acceleration = brake_force / vehicle.mass
            drag_acceleration = (
                calculate_drag_force(
                    vehicle,
                    speed,
                    air_density_kg_m3,
                )
                / vehicle.mass
            )
            rolling_acceleration = 9.81 * rolling_resistance
            total_deceleration = (
                brake_acceleration + drag_acceleration + rolling_acceleration
            )
            speed = max(0.0, speed - total_deceleration * time_step)
            vehicle.gearbox.advance_shift(time_step)

        distance += ((previous_speed + speed) / 2) * time_step
        elapsed += time_step
        peak_speed = max(peak_speed, speed)
        acceleration_g = (speed - previous_speed) / time_step / 9.81

        if vehicle.gearbox.current_gear != previous_gear:
            gear_change_count += 1
            previous_gear = vehicle.gearbox.current_gear
        if wheelspin and not previous_wheelspin:
            wheelspin_event_count += 1
        previous_wheelspin = wheelspin

        if measured_start_time is None and distance >= measured_start:
            measured_start_time = elapsed
        if measured_end_time is None and distance >= measured_end:
            measured_end_time = elapsed

        while elapsed + 1e-9 >= next_telemetry_time:
            if distance < measured_start:
                phase = "accelerating"
            elif distance < measured_end:
                phase = "measured mile"
            else:
                phase = "decelerating"
            telemetry.append(
                TelemetrySample(
                    time_seconds=round(next_telemetry_time, 1),
                    distance_miles=round(distance / METRES_PER_MILE, 3),
                    speed_mph=round(speed * 2.23694, 1),
                    engine_rpm=round(engine_rpm),
                    acceleration_g=round(acceleration_g, 3),
                    wheelspin=wheelspin,
                    gear=vehicle.gearbox.current_gear,
                    shifting=vehicle.gearbox.shifting,
                    brake_temperature_c=round(vehicle.brakes.temperature_c, 1),
                    brake_fade=vehicle.brakes.faded,
                    phase=phase,
                )
            )
            next_telemetry_time += 1.0

        if speed <= 0.1 and distance < track_distance:
            break

    completed = distance >= track_distance
    if telemetry[-1].time_seconds < round(elapsed, 1):
        telemetry.append(
            TelemetrySample(
                time_seconds=round(elapsed, 1),
                distance_miles=round(distance / METRES_PER_MILE, 3),
                speed_mph=round(speed * 2.23694, 1),
                engine_rpm=round(engine_rpm),
                acceleration_g=round(acceleration_g, 3),
                wheelspin=wheelspin,
                gear=vehicle.gearbox.current_gear,
                shifting=vehicle.gearbox.shifting,
                brake_temperature_c=round(vehicle.brakes.temperature_c, 1),
                brake_fade=vehicle.brakes.faded,
                phase="decelerating",
            )
        )
    measured_time = (measured_end_time or elapsed) - (measured_start_time or elapsed)
    measured_speed = measured_mile_length * METRES_PER_MILE / max(measured_time, time_step)
    average_acceleration_g = peak_speed / max(elapsed, time_step) / 9.81
    full_throttle_seconds = measured_end_time or elapsed

    return SimulationResult(
        track_miles=track_miles,
        measured_mile_time_seconds=round(measured_time, 2),
        measured_mile_speed_mph=round(measured_speed * 2.23694, 1),
        peak_speed_mph=round(peak_speed * 2.23694, 1),
        total_time_seconds=round(elapsed, 2),
        total_distance_miles=round(distance / METRES_PER_MILE, 3),
        average_acceleration_g=round(average_acceleration_g, 3),
        full_throttle_seconds=round(full_throttle_seconds, 2),
        gear_change_count=gear_change_count,
        wheelspin_event_count=wheelspin_event_count,
        maximum_brake_temperature_c=round(vehicle.brakes.temperature_c, 1),
        completed=completed,
        telemetry=telemetry,
    )