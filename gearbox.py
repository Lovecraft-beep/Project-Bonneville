"""Gearbox definitions for Project Bonneville."""

from dataclasses import dataclass
from math import pi


@dataclass
class Gearbox:
    ratios: tuple[float, ...]
    final_drive_ratio: float = 4.0
    efficiency: float = 0.85
    shift_up_rpm: int = 3_100
    shift_down_rpm: int = 1_200
    clutch_disengage_seconds: float = 0.15
    gear_select_seconds: float = 0.15
    clutch_engage_seconds: float = 0.35
    clutch_slip_factor: float = 0.15
    current_gear: int = 1
    shift_elapsed: float = 0.0
    pending_gear: int | None = None

    def __post_init__(self):
        if not self.ratios or any(ratio <= 0 for ratio in self.ratios):
            raise ValueError("gearbox must have positive gear ratios")
        if self.final_drive_ratio <= 0 or not 0 < self.efficiency <= 1:
            raise ValueError("final drive and efficiency must be positive")
        if self.shift_up_rpm <= 0:
            raise ValueError("shift_up_rpm must be greater than zero")
        if self.shift_down_rpm <= 0 or self.shift_down_rpm >= self.shift_up_rpm:
            raise ValueError("shift_down_rpm must be below shift_up_rpm")
        if (
            self.clutch_disengage_seconds < 0
            or self.gear_select_seconds < 0
            or self.clutch_engage_seconds <= 0
            or not 0 <= self.clutch_slip_factor < 1
        ):
            raise ValueError("shift timings and clutch slip must be valid")

    @property
    def gear_count(self):
        return len(self.ratios)

    @property
    def current_ratio(self):
        return self.ratios[self.current_gear - 1]

    def engine_rpm(self, speed_m_per_second, wheel_radius_m):
        wheel_revolutions_per_second = speed_m_per_second / (2 * pi * wheel_radius_m)
        return wheel_revolutions_per_second * 60 * self.current_ratio * self.final_drive_ratio

    @property
    def shift_duration(self):
        return (
            self.clutch_disengage_seconds
            + self.gear_select_seconds
            + self.clutch_engage_seconds
        )

    @property
    def shifting(self):
        return self.pending_gear is not None

    def shift_if_needed(self, engine_rpm, decelerating=False):
        if (
            not self.shifting
            and engine_rpm >= self.shift_up_rpm
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
        engagement_start = self.clutch_disengage_seconds + self.gear_select_seconds
        if self.shift_elapsed < engagement_start:
            return 0.0
        engagement_progress = min(
            1.0,
            (self.shift_elapsed - engagement_start) / self.clutch_engage_seconds,
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
