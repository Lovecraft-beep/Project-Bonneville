"""Gearbox definitions for Project Bonneville."""

from dataclasses import dataclass
from math import pi


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


AVAILABLE_GEARBOXES = {
    gearbox.name: gearbox for gearbox in PREBUILT_GEARBOXES
}
