"""Brake system definitions for Project Bonneville."""

from dataclasses import dataclass, field


@dataclass
class BrakeSystem:
    name: str
    max_braking_g: float
    efficiency: float
    fade_start_temperature_c: float = 250.0
    fade_end_temperature_c: float = 500.0
    heat_capacity_j_per_c: float = 120_000.0
    cooling_rate_w_per_c: float = 120.0
    temperature_c: float = field(default=20.0, init=False)

    def __post_init__(self):
        if self.max_braking_g <= 0 or not 0 < self.efficiency <= 1:
            raise ValueError("braking strength and efficiency must be positive")
        if self.fade_start_temperature_c >= self.fade_end_temperature_c:
            raise ValueError("fade start must be below fade end temperature")
        if self.heat_capacity_j_per_c <= 0 or self.cooling_rate_w_per_c < 0:
            raise ValueError("brake heat and cooling values must be valid")

    @property
    def fade_factor(self):
        if self.temperature_c <= self.fade_start_temperature_c:
            return 1.0
        fade_progress = min(
            1.0,
            (self.temperature_c - self.fade_start_temperature_c)
            / (self.fade_end_temperature_c - self.fade_start_temperature_c),
        )
        return 1.0 - 0.6 * fade_progress

    @property
    def faded(self):
        return self.temperature_c > self.fade_start_temperature_c

    def calculate_force(self, mass_kg, available_grip_force):
        """Return usable mechanical braking force in newtons."""
        brake_capability = (
            self.max_braking_g
            * 9.81
            * mass_kg
            * self.efficiency
            * self.fade_factor
        )
        return min(brake_capability, available_grip_force)

    def update_temperature(self, braking_force_n, speed_m_per_second, time_step):
        heat_watts = braking_force_n * speed_m_per_second
        cooling_watts = max(0.0, self.temperature_c - 20.0) * self.cooling_rate_w_per_c
        temperature_change = (heat_watts - cooling_watts) * time_step / self.heat_capacity_j_per_c
        self.temperature_c = max(20.0, self.temperature_c + temperature_change)

    def reset(self):
        self.temperature_c = 20.0


DRUM_BRAKES_1920S = BrakeSystem(
    name="1920s mechanical drum brakes",
    max_braking_g=0.45,
    efficiency=0.55,
)