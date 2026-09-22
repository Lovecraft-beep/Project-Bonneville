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
    required_technology: str | None = None

    def __post_init__(self):
        if self.torque_curve_type not in {
            "early_piston",
            "supercharged_piston",
            "steam",
            "turbojet",
            "rocket",
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
                (0.0, 0.60),
                (0.25, 0.60),
                (0.50, 0.90),
                (0.70, 1.00),
                (0.90, 0.85),
                (1.0, 0.65),
            ),
            "supercharged_piston": (
                (0.0, 0.55),
                (0.25, 0.65),
                (0.50, 0.90),
                (0.75, 1.00),
                (0.90, 0.90),
                (1.0, 0.75),
            ),
            "steam": (
                (0.0, 1.00),
                (0.50, 0.95),
                (0.80, 0.90),
                (1.0, 0.80),
            ),
            "turbojet": (
                (0.0, 0.70),
                (0.30, 0.85),
                (0.60, 0.95),
                (0.85, 1.00),
                (1.0, 0.95),
            ),
            "rocket": (
                (0.0, 1.00),
                (1.0, 1.00),
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


# A curated set of genuinely significant historical (and near-future) land
# speed record engines, spanning the full chassis/engine tech tree rather
# than every incremental production variant of each family.
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
    required_technology="pioneer_engines",
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
    name="Darracq V8",
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
    required_technology="edwardian_giants",
)


LIBERTY_V12 = Engine(
    name="Liberty V12",
    cylinders=12,
    power_hp=400.0,
    torque_nm=950.0,
    max_rpm=1_800,
    mass_kg=410.0,
    reliability=0.83,
    configuration="27-litre V12 aero engine",
    displacement_litres=27.0,
    era="1917",
    base_cost_gbp=8_800,
    rarity_factor=1.05,
    torque_curve_type="early_piston",
    required_technology="aircraft_conversions",
)


NAPIER_LION = Engine(
    name="Napier Lion",
    cylinders=12,
    power_hp=900.0,
    torque_nm=1_940.0,
    max_rpm=3_300,
    mass_kg=420.0,
    reliability=0.83,
    configuration="24-litre W12",
    displacement_litres=23.9,
    era="1927",
    base_cost_gbp=20_000,
    rarity_factor=1.15,
    torque_curve_type="supercharged_piston",
    required_technology="aircraft_conversions",
)


ROLLS_ROYCE_R = Engine(
    name="Rolls-Royce R",
    cylinders=12,
    power_hp=2_300.0,
    torque_nm=4_500.0,
    max_rpm=3_200,
    mass_kg=750.0,
    reliability=0.78,
    configuration="36.7-litre supercharged V12",
    displacement_litres=36.7,
    era="1933",
    base_cost_gbp=28_000,
    rarity_factor=1.6,
    torque_curve_type="supercharged_piston",
    required_technology="supercharged_aero_engines",
)


J47_TURBOJET = Engine(
    name="J47 Turbojet",
    cylinders=0,
    power_hp=6_000.0,
    torque_nm=8_000.0,
    max_rpm=8_000,
    mass_kg=1_050.0,
    reliability=0.72,
    configuration="axial-flow turbojet",
    era="1948",
    base_cost_gbp=9_500,
    rarity_factor=1.8,
    torque_curve_type="turbojet",
    required_technology="specialised_lsr_engines",
)


AVON_TURBOJET = Engine(
    name="Avon Turbojet",
    cylinders=0,
    power_hp=9_000.0,
    torque_nm=11_000.0,
    max_rpm=8_500,
    mass_kg=1_300.0,
    reliability=0.75,
    configuration="axial-flow turbojet",
    era="1957",
    base_cost_gbp=9_500,
    rarity_factor=1.9,
    torque_curve_type="turbojet",
    required_technology="gas_turbines",
)


XLR99_ROCKET = Engine(
    name="XLR99 Rocket",
    cylinders=0,
    power_hp=15_000.0,
    torque_nm=20_000.0,
    max_rpm=6_000,
    mass_kg=700.0,
    reliability=0.65,
    configuration="liquid-fuel rocket engine",
    era="1959",
    base_cost_gbp=8_500,
    rarity_factor=2.2,
    torque_curve_type="rocket",
    required_technology="rocket_propulsion",
)


EJ200_TURBOFAN = Engine(
    name="EJ200 Turbofan",
    cylinders=0,
    power_hp=20_000.0,
    torque_nm=22_000.0,
    max_rpm=10_000,
    mass_kg=1_000.0,
    reliability=0.90,
    configuration="afterburning turbofan",
    era="1990s",
    base_cost_gbp=10_700,
    rarity_factor=2.0,
    torque_curve_type="turbojet",
    required_technology="modern_turbofans",
)


ALL_ENGINES = (
    WELCH_HEMI,
    STANLEY_STEAM_ENGINE,
    DARRACQ_V8_25_LITRE,
    LIBERTY_V12,
    NAPIER_LION,
    ROLLS_ROYCE_R,
    J47_TURBOJET,
    AVON_TURBOJET,
    XLR99_ROCKET,
    EJ200_TURBOFAN,
)

AVAILABLE_ENGINES = {engine.name: engine for engine in ALL_ENGINES}


def is_engine_unlocked(engine, researched_technologies):
    """Return whether an engine's required technology has been researched."""
    return (
        engine.required_technology is None
        or engine.required_technology in researched_technologies
    )


def available_engines(researched_technologies):
    """Return catalogue engines unlocked by the given researched technologies."""
    return tuple(
        engine
        for engine in AVAILABLE_ENGINES.values()
        if is_engine_unlocked(engine, researched_technologies)
    )


def select_engine(researched_technologies=(), current_engine=None):
    print("\n=== SELECT ENGINE ===")
    engine_choices = available_engines(researched_technologies)
    if not engine_choices:
        print("No engines are unlocked yet. Using Stanley Rocket Steam Engine.")
        return STANLEY_STEAM_ENGINE

    for number, engine in enumerate(engine_choices, start=1):
        marker = "* " if current_engine and engine.name == current_engine.name else "  "
        print(
            f"{number}. {marker}{engine.name} ({engine.power_hp} hp, "
            f"GBP {engine.purchase_cost_gbp:,}, reliability {engine.reliability:.0%})"
        )

    choice = input("Choose an engine: ").strip()
    try:
        return engine_choices[int(choice) - 1]
    except (ValueError, IndexError):
        print(f"Invalid choice. Using {engine_choices[0].name}.")
        return engine_choices[0]
