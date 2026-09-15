"""Selectable vehicle definitions for Project Bonneville."""

from copy import deepcopy

from brakes import DRUM_BRAKES_1920S, BrakeSystem
from engines import (
    NAPIER_LION_VIIA,
    NAPIER_LION_VARIANTS,
    DARRACQ_V8_25_LITRE,
    STANLEY_STEAM_ENGINE,
    WELCH_HEMI,
)
from engines import AVAILABLE_ENGINES
from gearbox import (
    BLUE_BIRD_GEARBOX,
    BLUE_BIRD_GEARBOXES,
    BRICK_3_SPEED,
    DARRACQ_2_SPEED,
    GOLDEN_ARROW_3_SPEED,
    JEANTAUD_3_SPEED,
    RAILTON_3_SPEED_LSR,
    STANLEY_ROCKET_DIRECT_DRIVE,
)
from vehicle import Vehicle


def create_brick_mk1():
    return Vehicle(
        name="Brick Mk1",
        mass=3000,
        cd=0.30,
        area=2.5,
        tyre_grip_factor=0.8,
        engine=NAPIER_LION_VIIA,
        wheel_radius_m=0.4,
        gearbox=deepcopy(BRICK_3_SPEED),
        brakes=BrakeSystem(
            name=DRUM_BRAKES_1920S.name,
            max_braking_g=DRUM_BRAKES_1920S.max_braking_g,
            efficiency=DRUM_BRAKES_1920S.efficiency,
        ),
    )


def create_blue_bird_1927(engine=NAPIER_LION_VIIA, gearbox=None):
    return Vehicle(
        name="Blue Bird 1927",
        mass=2500,
        cd=0.40,
        area=2.2,
        tyre_grip_factor=0.85,
        engine=engine,
        wheel_radius_m=0.38,
        gearbox=deepcopy(gearbox or BLUE_BIRD_GEARBOX),
        brakes=BrakeSystem(
            name=DRUM_BRAKES_1920S.name,
            max_braking_g=DRUM_BRAKES_1920S.max_braking_g,
            efficiency=DRUM_BRAKES_1920S.efficiency,
        ),
    )


def create_jeantaud():
    """Create the 1,400 kg Welch Hemi-powered Jeataud prototype."""
    return Vehicle(
        name="Jeantaud",
        mass=1400,
        cd=0.95,
        area=1.7,
        tyre_grip_factor=0.75,
        engine=WELCH_HEMI,
        wheel_radius_m=0.35,
        gearbox=deepcopy(JEANTAUD_3_SPEED),
        brakes=BrakeSystem(
            name=DRUM_BRAKES_1920S.name,
            max_braking_g=DRUM_BRAKES_1920S.max_braking_g,
            efficiency=DRUM_BRAKES_1920S.efficiency,
        ),
    )


def create_campbell_napier_railton_blue_bird(
    engine=None,
    gearbox=None,
):
    """Create the 1931 Campbell-Napier-Railton Blue Bird."""
    engine = engine or AVAILABLE_ENGINES["Napier Lion XI"]
    gearbox = deepcopy(gearbox or RAILTON_3_SPEED_LSR)
    return Vehicle(
        name="Campbell-Napier-Railton Blue Bird",
        model_year=1931,
        mass=3600,
        cd=0.55,
        area=2.3,
        tyre_grip_factor=0.9,
        engine=engine,
        wheel_radius_m=0.55,
        gearbox=gearbox,
        brakes=BrakeSystem(
            name=DRUM_BRAKES_1920S.name,
            max_braking_g=DRUM_BRAKES_1920S.max_braking_g,
            efficiency=DRUM_BRAKES_1920S.efficiency,
        ),
    )


def create_irving_napier_golden_arrow():
    """Create Major Segrave's 1929 Irving-Napier Golden Arrow."""
    return Vehicle(
        name="Irving-Napier Golden Arrow",
        model_year=1929,
        mass=3661,
        length_m=8.43,
        height_m=1.14,
        wheelbase_m=4.07,
        cd=0.22,
        area=1.9,
        tyre_grip_factor=0.9,
        engine=AVAILABLE_ENGINES["Napier Lion VIIB"],
        wheel_radius_m=0.52,
        gearbox=deepcopy(GOLDEN_ARROW_3_SPEED),
        brakes=BrakeSystem(
            name=DRUM_BRAKES_1920S.name,
            max_braking_g=DRUM_BRAKES_1920S.max_braking_g,
            efficiency=DRUM_BRAKES_1920S.efficiency,
        ),
    )


def create_stanley_steamer_rocket():
    """Create the 1906 Stanley Steamer Rocket record car."""
    return Vehicle(
        name="Stanley Steamer Rocket",
        model_year=1906,
        mass=1_000,
        length_m=4.74,
        height_m=0.93,
        wheelbase_m=2.49,
        cd=0.45,
        area=1.45,
        tyre_grip_factor=0.7,
        engine=STANLEY_STEAM_ENGINE,
        wheel_radius_m=0.55,
        gearbox=deepcopy(STANLEY_ROCKET_DIRECT_DRIVE),
        brakes=BrakeSystem(
            name=DRUM_BRAKES_1920S.name,
            max_braking_g=0.35,
            efficiency=0.45,
        ),
    )


def create_darracq_1905():
    """Create the 1905 Darracq land-speed record car."""
    return Vehicle(
        name="Darracq 1905",
        model_year=1905,
        mass=1_000,
        length_m=4.5,
        height_m=1.24,
        wheelbase_m=3.25,
        cd=0.75,
        area=1.9,
        tyre_grip_factor=0.65,
        engine=DARRACQ_V8_25_LITRE,
        wheel_radius_m=0.42,
        gearbox=deepcopy(DARRACQ_2_SPEED),
        brakes=BrakeSystem(
            name="1905 mechanical drum brakes",
            max_braking_g=0.20,
            efficiency=0.30,
            fade_start_temperature_c=120.0,
            fade_end_temperature_c=220.0,
            heat_capacity_j_per_c=70_000.0,
            cooling_rate_w_per_c=80.0,
        ),
    )


AVAILABLE_CARS = {
    "1": create_brick_mk1,
    "2": create_blue_bird_1927,
    "3": create_jeantaud,
    "4": create_campbell_napier_railton_blue_bird,
    "5": create_irving_napier_golden_arrow,
    "6": create_stanley_steamer_rocket,
    "7": create_darracq_1905,
}


def select_car():
    print("\n=== SELECT VEHICLE ===")
    for choice, create_vehicle in AVAILABLE_CARS.items():
        print(f"{choice}. {create_vehicle().name}")

    choice = input("Choose a vehicle: ").strip()
    if choice not in AVAILABLE_CARS:
        print("Invalid choice. Using Brick Mk1.")
        choice = "1"
    if choice == "2":
        return select_blue_bird_engine()
    if choice == "4":
        return select_campbell_engine()
    return AVAILABLE_CARS[choice]()


def select_blue_bird_engine():
    print("\n=== SELECT BLUE BIRD ENGINE ===")
    for number, engine in enumerate(NAPIER_LION_VARIANTS, start=1):
        print(f"{number}. {engine.name} ({engine.power_hp} hp, {engine.era})")

    choice = input("Choose a Napier Lion variant: ").strip()
    try:
        engine = NAPIER_LION_VARIANTS[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice. Using Napier Lion VIIA.")
        engine = NAPIER_LION_VIIA
    gearbox = select_blue_bird_gearbox()
    return create_blue_bird_1927(engine, gearbox)


def select_campbell_engine():
    print("\n=== SELECT CAMPBELL BLUE BIRD ENGINE ===")
    for number, engine in enumerate(NAPIER_LION_VARIANTS, start=1):
        print(f"{number}. {engine.name} ({engine.power_hp} hp, {engine.era})")

    choice = input("Choose a Napier Lion variant: ").strip()
    try:
        engine = NAPIER_LION_VARIANTS[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice. Using Napier Lion XI.")
        engine = AVAILABLE_ENGINES["Napier Lion XI"]

    gearbox = select_campbell_gearbox()
    return create_campbell_napier_railton_blue_bird(engine, gearbox)


def select_campbell_gearbox():
    print("\n=== SELECT CAMPBELL BLUE BIRD GEARBOX ===")
    gearboxes = (RAILTON_3_SPEED_LSR, BLUE_BIRD_GEARBOX)
    for number, gearbox in enumerate(gearboxes, start=1):
        print(
            f"{number}. {gearbox.name} "
            f"({gearbox.gear_count} gears, {gearbox.efficiency:.0%} efficiency)"
        )

    choice = input("Choose a gearbox: ").strip()
    try:
        return gearboxes[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice. Using Railton 3-Speed LSR.")
        return RAILTON_3_SPEED_LSR


def select_blue_bird_gearbox():
    print("\n=== SELECT BLUE BIRD GEARBOX ===")
    for number, gearbox in enumerate(BLUE_BIRD_GEARBOXES, start=1):
        print(
            f"{number}. {gearbox.name} "
            f"({gearbox.gear_count} gears, {gearbox.efficiency:.0%} efficiency)"
        )

    choice = input("Choose a gearbox: ").strip()
    try:
        return BLUE_BIRD_GEARBOXES[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice. Using Blue Bird 3-Speed.")
        return BLUE_BIRD_GEARBOX