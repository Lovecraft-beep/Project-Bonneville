"""Brake system definitions for Project Bonneville."""

from dataclasses import dataclass, field


@dataclass
class BrakeSystem:
    name: str
    max_braking_g: float
    efficiency: float
    mass_kg: float = 0.0
    cost_gbp: float = 0.0
    introduced_year: int = 1895
    fade_start_temperature_c: float = 250.0
    fade_end_temperature_c: float = 500.0
    heat_capacity_j_per_c: float = 120_000.0
    cooling_rate_w_per_c: float = 120.0
    temperature_c: float = field(default=20.0, init=False)

    def __post_init__(self):
        if self.max_braking_g <= 0 or not 0 < self.efficiency <= 1:
            raise ValueError("braking strength and efficiency must be positive")
        if self.mass_kg < 0:
            raise ValueError("brake mass must not be negative")
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
            self.max_braking_g * 9.81 * mass_kg * self.efficiency * self.fade_factor
        )
        return min(brake_capability, available_grip_force)

    def update_temperature(self, braking_force_n, speed_m_per_second, time_step):
        heat_watts = braking_force_n * speed_m_per_second
        cooling_watts = max(0.0, self.temperature_c - 20.0) * self.cooling_rate_w_per_c
        temperature_change = (
            (heat_watts - cooling_watts) * time_step / self.heat_capacity_j_per_c
        )
        self.temperature_c = max(20.0, self.temperature_c + temperature_change)

    def reset(self):
        self.temperature_c = 20.0


EARLY_BLOCK_BRAKES = BrakeSystem(
    name="Wooden block brakes",
    max_braking_g=0.12,
    efficiency=0.22,
    mass_kg=35.0,
    cost_gbp=150.0,
    introduced_year=1895,
    fade_start_temperature_c=80.0,
    fade_end_temperature_c=160.0,
    heat_capacity_j_per_c=45_000.0,
    cooling_rate_w_per_c=50.0,
)


MECHANICAL_DRUM_BRAKES = BrakeSystem(
    name="Early mechanical drum brakes",
    max_braking_g=0.20,
    efficiency=0.30,
    mass_kg=55.0,
    cost_gbp=500.0,
    introduced_year=1900,
    fade_start_temperature_c=120.0,
    fade_end_temperature_c=220.0,
    heat_capacity_j_per_c=70_000.0,
    cooling_rate_w_per_c=80.0,
)


DRUM_BRAKES_1920S = BrakeSystem(
    name="1920s mechanical drum brakes",
    max_braking_g=0.45,
    efficiency=0.55,
    mass_kg=90.0,
    cost_gbp=1_500.0,
    introduced_year=1920,
)


SERVO_ASSISTED_DRUM_BRAKES = BrakeSystem(
    name="Servo-assisted drum brakes",
    max_braking_g=0.55,
    efficiency=0.70,
    mass_kg=105.0,
    cost_gbp=4_000.0,
    introduced_year=1930,
    fade_start_temperature_c=300.0,
    fade_end_temperature_c=550.0,
)


HYDRAULIC_DISC_BRAKES = BrakeSystem(
    name="Hydraulic disc brakes",
    max_braking_g=0.70,
    efficiency=0.80,
    mass_kg=70.0,
    cost_gbp=8_000.0,
    introduced_year=1948,
    fade_start_temperature_c=350.0,
    fade_end_temperature_c=650.0,
    cooling_rate_w_per_c=150.0,
)


AIR_BRAKES = BrakeSystem(
    name="High-speed air brakes",
    max_braking_g=0.85,
    efficiency=0.84,
    mass_kg=80.0,
    cost_gbp=15_000.0,
    introduced_year=1955,
    fade_start_temperature_c=400.0,
    fade_end_temperature_c=750.0,
    cooling_rate_w_per_c=180.0,
)


CARBON_BRAKES = BrakeSystem(
    name="Carbon-carbon brakes",
    max_braking_g=1.10,
    efficiency=0.92,
    mass_kg=45.0,
    cost_gbp=35_000.0,
    introduced_year=1980,
    fade_start_temperature_c=650.0,
    fade_end_temperature_c=1_000.0,
    cooling_rate_w_per_c=220.0,
)


BRAKE_CATALOG = (
    EARLY_BLOCK_BRAKES,
    MECHANICAL_DRUM_BRAKES,
    DRUM_BRAKES_1920S,
    SERVO_ASSISTED_DRUM_BRAKES,
    HYDRAULIC_DISC_BRAKES,
    AIR_BRAKES,
    CARBON_BRAKES,
)
BRAKE_BY_NAME = {brakes.name: brakes for brakes in BRAKE_CATALOG}


def available_brakes(current_year=None):
    """Return brake systems historically available in the campaign year."""
    if current_year is None:
        return BRAKE_CATALOG
    return tuple(brake for brake in BRAKE_CATALOG if brake.introduced_year <= current_year)
