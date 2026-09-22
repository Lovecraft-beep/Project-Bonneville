"""Gearbox definitions for Project Bonneville."""

from copy import deepcopy
from dataclasses import dataclass
from math import pi


HORSEPOWER_IN_WATTS = 745.7
METRES_PER_MILE = 1609.344


@dataclass
class Gearbox:
    name: str
    gears: tuple[float, ...]
    final_drive: float = 4.0
    shift_time_seconds: float = 0.65
    clutch_time_seconds: float = 0.35
    efficiency: float = 0.85
    mass_kg: float = 0.0
    reliability: float = 1.0
    cost_gbp: float = 0.0
    shift_up_rpm: int = 3_100
    shift_down_rpm: int = 1_200
    clutch_slip_factor: float = 0.15
    current_gear: int = 1
    shift_elapsed: float = 0.0
    pending_gear: int | None = None

    def __post_init__(self):
        if not self.gears or any(ratio <= 0 for ratio in self.gears):
            raise ValueError("gearbox must have positive gear ratios")
        if self.final_drive <= 0 or not 0 < self.efficiency <= 1:
            raise ValueError("final drive and efficiency must be positive")
        if self.shift_time_seconds <= 0 or self.clutch_time_seconds <= 0:
            raise ValueError("shift and clutch times must be positive")
        if self.mass_kg < 0 or not 0 < self.reliability <= 1 or self.cost_gbp < 0:
            raise ValueError("gearbox mass, reliability, and cost must be valid")
        if self.shift_up_rpm <= 0:
            raise ValueError("shift_up_rpm must be greater than zero")
        if self.shift_down_rpm <= 0 or self.shift_down_rpm >= self.shift_up_rpm:
            raise ValueError("shift_down_rpm must be below shift_up_rpm")
        if (
            not 0 <= self.clutch_slip_factor < 1
        ):
            raise ValueError("shift timings and clutch slip must be valid")

    @property
    def gear_count(self):
        return len(self.gears)

    @property
    def current_ratio(self):
        return self.gears[self.current_gear - 1]

    @property
    def ratios(self):
        return self.gears

    @property
    def final_drive_ratio(self):
        return self.final_drive

    def engine_rpm(self, speed_m_per_second, wheel_radius_m):
        wheel_revolutions_per_second = speed_m_per_second / (2 * pi * wheel_radius_m)
        return wheel_revolutions_per_second * 60 * self.current_ratio * self.final_drive_ratio

    @property
    def shift_duration(self):
        return self.shift_time_seconds

    @property
    def shifting(self):
        return self.pending_gear is not None

    def shift_if_needed(self, engine_rpm, decelerating=False, rpm_limit=None):
        upshift_rpm = self.shift_up_rpm if rpm_limit is None else min(self.shift_up_rpm, rpm_limit)
        if (
            not self.shifting
            and engine_rpm >= upshift_rpm
            and self.current_gear < self.gear_count
        ):
            self.pending_gear = self.current_gear + 1
            self.shift_elapsed = 0.0
        elif (
            not self.shifting
            and decelerating
            and engine_rpm <= self.shift_down_rpm
            and self.current_gear > 1
        ):
            self.pending_gear = self.current_gear - 1
            self.shift_elapsed = 0.0

    def clutch_torque_multiplier(self):
        if not self.shifting:
            return 1.0
        engagement_start = self.shift_time_seconds - self.clutch_time_seconds
        if self.shift_elapsed < engagement_start:
            return 0.0
        engagement_progress = min(
            1.0,
            (self.shift_elapsed - engagement_start) / self.clutch_time_seconds,
        )
        return engagement_progress * (
            1.0 - self.clutch_slip_factor * (1.0 - engagement_progress)
        )

    def advance_shift(self, time_step):
        if not self.shifting:
            return
        self.shift_elapsed += time_step
        if self.shift_elapsed >= self.shift_duration:
            self.current_gear = self.pending_gear
            self.pending_gear = None
            self.shift_elapsed = 0.0


def estimate_power_limited_speed_mph(vehicle, engine):
    """Estimate the speed where engine power balances drag and rolling loss."""
    power_watts = engine.power_hp * HORSEPOWER_IN_WATTS * 0.85
    rolling_force = vehicle.mass * 9.81 * 0.015
    low_speed = 0.1
    high_speed = 150.0
    for _ in range(60):
        speed_mps = (low_speed + high_speed) / 2
        drag_force = 0.5 * vehicle.cd * 1.2 * speed_mps**2 * vehicle.area
        required_power = (drag_force + rolling_force) * speed_mps
        if required_power < power_watts:
            low_speed = speed_mps
        else:
            high_speed = speed_mps
    speed_mps = (low_speed + high_speed) / 2
    return speed_mps * 2.23694


def estimate_gear_limited_speed_mph(vehicle):
    """Estimate top speed at 98% of engine redline in the highest gear."""
    gearbox = vehicle.gearbox
    rpm = vehicle.engine.max_rpm * 0.98
    wheel_revolutions_per_second = (
        rpm / 60 / (gearbox.gears[-1] * gearbox.final_drive_ratio)
    )
    speed_mps = wheel_revolutions_per_second * 2 * pi * vehicle.wheel_radius_m
    return speed_mps * 2.23694


def optimize_gearbox_for_engine(vehicle):
    """Update gearbox ratios to suit the engine's power and usable RPM range."""
    gearbox = vehicle.gearbox
    if vehicle.engine.torque_curve_type in ("turbojet", "rocket"):
        gearbox.gears = (1.0,)
        gearbox.final_drive = 2.25
        return gearbox

    target_speed_mph = estimate_power_limited_speed_mph(vehicle, vehicle.engine)
    target_speed_mps = target_speed_mph / 2.23694
    usable_rpm = vehicle.engine.max_rpm * 0.98
    wheel_revolutions_per_second = target_speed_mps / (2 * pi * vehicle.wheel_radius_m)
    target_overall_ratio = (
        usable_rpm / (wheel_revolutions_per_second * 60)
    )
    gear_count = max(1, gearbox.gear_count)
    final_drive = min(3.5, max(0.62, target_overall_ratio / 2.5))
    top_ratio = target_overall_ratio / final_drive
    first_ratio = min(4.5, max(top_ratio, top_ratio * (1.8 if gear_count > 1 else 1.0)))
    if gear_count == 1:
        ratios = (round(top_ratio, 3),)
    else:
        ratios = tuple(
            round(
                top_ratio
                + (first_ratio - top_ratio)
                * (gear_count - index - 1)
                / (gear_count - 1),
                3,
            )
            for index in range(gear_count)
        )
    gearbox.gears = ratios
    gearbox.final_drive = round(final_drive, 3)
    return gearbox


BLUE_BIRD_GEARBOX = Gearbox(
    name="Blue Bird 3-Speed",
    gears=(2.4, 1.6, 1.0),
    final_drive=1.1,
    shift_up_rpm=2_600,
    shift_down_rpm=1_200,
    cost_gbp=4_000.0,
)


BRICK_3_SPEED = Gearbox(
    name="Brick 3-Speed",
    gears=(2.5, 1.7, 1.0),
    final_drive=1.15,
    shift_up_rpm=2_600,
    shift_down_rpm=1_200,
    cost_gbp=4_500.0,
)


JEANTAUD_3_SPEED = Gearbox(
    name="Jeantaud 3-Speed",
    gears=(3.2, 1.8, 1.0),
    final_drive=3.5,
    shift_up_rpm=2_300,
    shift_down_rpm=1_100,
    cost_gbp=2_500.0,
)


RAILTON_3_SPEED_LSR = Gearbox(
    name="Railton 3-Speed LSR",
    gears=(4.01, 2.27, 1.24),
    final_drive=1.0,
    shift_time_seconds=2.0,
    clutch_time_seconds=1.0,
    efficiency=0.93,
    mass_kg=180.0,
    reliability=0.85,
    cost_gbp=12_000.0,
    shift_up_rpm=3_200,
    shift_down_rpm=1_400,
)


GOLDEN_ARROW_3_SPEED = Gearbox(
    name="Golden Arrow 3-Speed LSR",
    gears=(3.0, 1.8, 1.0),
    final_drive=1.0,
    shift_time_seconds=1.5,
    clutch_time_seconds=0.75,
    efficiency=0.90,
    mass_kg=160.0,
    reliability=0.80,
    cost_gbp=15_000.0,
    shift_up_rpm=3_300,
    shift_down_rpm=1_500,
)


STANLEY_ROCKET_DIRECT_DRIVE = Gearbox(
    name="Stanley Rocket Direct Drive",
    gears=(1.0,),
    final_drive=1.15,
    shift_time_seconds=0.5,
    clutch_time_seconds=0.25,
    efficiency=0.80,
    mass_kg=90.0,
    reliability=0.90,
    cost_gbp=3_000.0,
    shift_up_rpm=1_400,
    shift_down_rpm=700,
)


DARRACQ_2_SPEED = Gearbox(
    name="Darracq 2-Speed",
    gears=(2.8, 1.0),
    final_drive=2.0,
    shift_time_seconds=2.5,
    clutch_time_seconds=1.25,
    efficiency=0.85,
    mass_kg=120.0,
    reliability=0.70,
    cost_gbp=5_000.0,
    shift_up_rpm=1_800,
    shift_down_rpm=900,
)


BLUE_BIRD_GEARBOXES = (BLUE_BIRD_GEARBOX, RAILTON_3_SPEED_LSR)
PREBUILT_GEARBOXES = (
    BRICK_3_SPEED,
    BLUE_BIRD_GEARBOX,
    JEANTAUD_3_SPEED,
    RAILTON_3_SPEED_LSR,
    GOLDEN_ARROW_3_SPEED,
    STANLEY_ROCKET_DIRECT_DRIVE,
    DARRACQ_2_SPEED,
)


# Simplified transmission tiers for the vehicle designer: a single freewheel
# ratio for thrust engines (turbojets/rockets don't need a powerband to stay
# in), and an increasingly robust, closer-ratio multi-speed ladder for piston
# engines as their power rises.
DIRECT_DRIVE = Gearbox(
    name="Direct Drive",
    gears=(1.0,),
    final_drive=2.25,
    shift_time_seconds=0.5,
    clutch_time_seconds=0.25,
    efficiency=0.95,
    mass_kg=60.0,
    reliability=0.92,
    cost_gbp=5_000.0,
    shift_up_rpm=6_000,
    shift_down_rpm=2_000,
)


TWO_SPEED_TRANSMISSION = Gearbox(
    name="2-Speed Transmission",
    gears=(2.0, 1.0),
    final_drive=2.2,
    shift_time_seconds=0.8,
    clutch_time_seconds=0.4,
    efficiency=0.85,
    mass_kg=90.0,
    reliability=0.85,
    cost_gbp=4_000.0,
    shift_up_rpm=2_200,
    shift_down_rpm=900,
)


THREE_SPEED_TRANSMISSION = Gearbox(
    name="3-Speed Transmission",
    gears=(2.5, 1.6, 1.0),
    final_drive=1.15,
    shift_time_seconds=0.65,
    clutch_time_seconds=0.35,
    efficiency=0.87,
    mass_kg=140.0,
    reliability=0.82,
    cost_gbp=9_000.0,
    shift_up_rpm=2_800,
    shift_down_rpm=1_200,
)


FOUR_SPEED_TRANSMISSION = Gearbox(
    name="4-Speed Transmission",
    gears=(3.4, 2.2, 1.5, 1.0),
    final_drive=0.90,
    shift_time_seconds=0.55,
    clutch_time_seconds=0.3,
    efficiency=0.90,
    mass_kg=190.0,
    reliability=0.80,
    cost_gbp=16_000.0,
    shift_up_rpm=3_000,
    shift_down_rpm=1_400,
)


FIVE_SPEED_TRANSMISSION = Gearbox(
    name="5-Speed Transmission",
    gears=(4.0, 2.8, 2.0, 1.4, 1.0),
    final_drive=0.62,
    shift_time_seconds=0.45,
    clutch_time_seconds=0.25,
    efficiency=0.92,
    mass_kg=230.0,
    reliability=0.78,
    cost_gbp=26_000.0,
    shift_up_rpm=3_200,
    shift_down_rpm=1_500,
)


# Power brackets (engine power_hp) that select a sensible default tier for
# piston engines. Thrust engines (turbojet/rocket) always use Direct Drive.
PISTON_TRANSMISSION_TIERS = (
    (100.0, TWO_SPEED_TRANSMISSION),
    (1_000.0, THREE_SPEED_TRANSMISSION),
    (3_000.0, FOUR_SPEED_TRANSMISSION),
    (float("inf"), FIVE_SPEED_TRANSMISSION),
)

TRANSMISSION_CATALOG = (
    DIRECT_DRIVE,
    TWO_SPEED_TRANSMISSION,
    THREE_SPEED_TRANSMISSION,
    FOUR_SPEED_TRANSMISSION,
    FIVE_SPEED_TRANSMISSION,
)


AVAILABLE_GEARBOXES = {
    gearbox.name: gearbox for gearbox in PREBUILT_GEARBOXES + TRANSMISSION_CATALOG
}


def recommended_transmission(engine):
    """Return the transmission tier suited to an engine's propulsion type."""
    if engine.torque_curve_type in ("turbojet", "rocket"):
        return DIRECT_DRIVE
    for power_ceiling, transmission in PISTON_TRANSMISSION_TIERS:
        if engine.power_hp <= power_ceiling:
            return transmission
    return FIVE_SPEED_TRANSMISSION


def select_gearbox(engine=None, current_gearbox=None):
    if engine is not None and engine.torque_curve_type in ("turbojet", "rocket"):
        print(
            "\n=== SELECT GEARBOX ===\n"
            f"{engine.name} is a thrust engine, fitted with Direct Drive "
            "(no gears to shift)."
        )
        return deepcopy(DIRECT_DRIVE)

    print("\n=== SELECT GEARBOX ===")
    for number, gearbox in enumerate(TRANSMISSION_CATALOG, start=1):
        marker = "* " if current_gearbox and gearbox.name == current_gearbox.name else "  "
        print(
            f"{number}. {marker}{gearbox.name} ({gearbox.gear_count} gears, "
            f"GBP {gearbox.cost_gbp:,.0f}, {gearbox.efficiency:.0%} efficiency)"
        )

    default = recommended_transmission(engine) if engine is not None else THREE_SPEED_TRANSMISSION
    choice = input(
        f"Choose a gearbox (or press Enter for {default.name}): "
    ).strip()
    if not choice:
        return deepcopy(default)
    try:
        return deepcopy(TRANSMISSION_CATALOG[int(choice) - 1])
    except (ValueError, IndexError):
        print(f"Invalid choice. Using {default.name}.")
        return deepcopy(default)
