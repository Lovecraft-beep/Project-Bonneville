"""Historically inspired engine definitions for Project Bonneville."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Engine:
    name: str
    cylinders: int
    power_hp: float
    torque_nm: float
    max_rpm: int
    mass_kg: float
    reliability: float
    configuration: str = ""
    displacement_litres: float | None = None
    era: str = ""
    base_cost_gbp: float = 0.0
    rarity_factor: float = 1.0
    torque_curve_type: str = "early_piston"

    def __post_init__(self):
        if self.torque_curve_type not in {
            "early_piston",
            "supercharged_piston",
            "steam",
        }:
            raise ValueError("engine torque curve type must be recognised")

    @property
    def purchase_cost_gbp(self):
        power_factor = 1.0 + self.power_hp / 1_000
        return round(self.base_cost_gbp * power_factor * self.rarity_factor)

    def torque_at_rpm(self, rpm):
        """Return generic period-appropriate engine torque at the given RPM."""
        if rpm > self.max_rpm:
            return 0.0

        rpm_fraction = max(0.0, rpm / self.max_rpm)
        curve_points = {
            "early_piston": (
                (0.0, 0.60), (0.25, 0.60), (0.50, 0.90),
                (0.70, 1.00), (0.90, 0.85), (1.0, 0.65),
            ),
            "supercharged_piston": (
                (0.0, 0.55), (0.25, 0.65), (0.50, 0.90),
                (0.75, 1.00), (0.90, 0.90), (1.0, 0.75),
            ),
            "steam": (
                (0.0, 1.00), (0.50, 0.95), (0.80, 0.90),
                (1.0, 0.80),
            ),
        }
        points = curve_points[self.torque_curve_type]
        for (lower_rpm, lower_torque), (upper_rpm, upper_torque) in zip(
            points,
            points[1:],
        ):
            if rpm_fraction <= upper_rpm:
                interpolation = (rpm_fraction - lower_rpm) / (upper_rpm - lower_rpm)
                return self.torque_nm * (
                    lower_torque + interpolation * (upper_torque - lower_torque)
                )
        return self.torque_nm * points[-1][1]


NAPIER_LION_VIIA = Engine(
    name="Napier Lion VIIA",
    cylinders=12,
    power_hp=900.0,
    torque_nm=1_940.0,
    max_rpm=3_300,
    mass_kg=420.0,
    reliability=0.82,
    configuration="24-litre W12",
    displacement_litres=23.9,
    era="1927",
    base_cost_gbp=20_000,
    rarity_factor=1.15,
    torque_curve_type="supercharged_piston",
)


NAPIER_LION_VARIANTS = (
    Engine("Napier Lion I", 12, 450, 1660, 1925, 390, 0.95, "W12", 23.94, "1918", 9_000, 1.0),
    Engine("Napier Lion II", 12, 450, 1660, 1925, 392, 0.96, "W12", 23.94, "1920", 9_500, 1.0),
    Engine("Napier Lion V", 12, 500, 1750, 2100, 395, 0.94, "W12", 23.94, "1923", 10_000, 1.05),
    Engine("Napier Lion VI", 12, 580, 1910, 2250, 400, 0.92, "W12", 23.94, "1924", 11_000, 1.1),
    Engine("Napier Lion VII", 12, 680, 1840, 2585, 405, 0.90, "W12", 23.94, "1925", 12_500, 1.15),
    NAPIER_LION_VIIA,
    Engine("Napier Lion VIIB", 12, 930, 1980, 3350, 420, 0.80, "W12", 23.94, "1928", 17_000, 1.25),
    Engine("Napier Lion VIII", 12, 1000, 2050, 3500, 425, 0.75, "W12", 23.94, "1928", 19_000, 1.35),
    Engine("Napier Lion VIID", 12, 1320, 2600, 3600, 430, 0.65, "Supercharged W12", 23.94, "1929", 24_000, 1.5),
    Engine("Napier Lion XI", 12, 1050, 2150, 3500, 425, 0.75, "W12", 23.94, "1930", 20_000, 1.4),
)


WELCH_HEMI = Engine(
    name="Welch Hemi",
    cylinders=4,
    power_hp=36.0,
    torque_nm=203.0,
    max_rpm=2_500,
    mass_kg=120.0,
    reliability=0.80,
    configuration="four-cylinder hemi",
    era="1920s",
    base_cost_gbp=2_000,
    rarity_factor=0.9,
)


STANLEY_STEAM_ENGINE = Engine(
    name="Stanley Rocket Steam Engine",
    cylinders=2,
    power_hp=150.0,
    torque_nm=800.0,
    max_rpm=2_500,
    mass_kg=250.0,
    reliability=0.88,
    configuration="two-cylinder steam engine",
    era="1906",
    base_cost_gbp=4_000,
    rarity_factor=1.3,
    torque_curve_type="steam",
)


DARRACQ_V8_25_LITRE = Engine(
    name="Darracq 25.422-litre V8",
    cylinders=8,
    power_hp=200.0,
    torque_nm=850.0,
    max_rpm=2_000,
    mass_kg=300.0,
    reliability=0.75,
    configuration="25.422-litre V8",
    displacement_litres=25.422,
    era="1905",
    base_cost_gbp=8_000,
    rarity_factor=1.4,
    torque_curve_type="early_piston",
)


AVAILABLE_ENGINES = {
    engine.name: engine for engine in NAPIER_LION_VARIANTS
}
AVAILABLE_ENGINES.update({
    WELCH_HEMI.name: WELCH_HEMI,
    STANLEY_STEAM_ENGINE.name: STANLEY_STEAM_ENGINE,
    DARRACQ_V8_25_LITRE.name: DARRACQ_V8_25_LITRE,
})