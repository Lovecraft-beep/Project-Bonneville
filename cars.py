"""Selectable vehicle definitions for Project Bonneville."""

from brakes import DRUM_BRAKES_1920S, BrakeSystem
from engines import NAPIER_LION_VIIA, WELCH_HEMI
from gearbox import Gearbox
from vehicle import Vehicle


def create_brick_mk1():
    return Vehicle(
        name="Brick Mk1",
        mass=3000,
        power=450,
        cd=0.30,
        area=2.5,
        tyre_grip_factor=0.8,
        engine=NAPIER_LION_VIIA,
        wheel_radius_m=0.4,
        gearbox=Gearbox(
            ratios=(2.5, 1.7, 1.0),
            final_drive_ratio=1.15,
            shift_up_rpm=2_600,
            shift_down_rpm=1_200,
        ),
        brakes=BrakeSystem(
            name=DRUM_BRAKES_1920S.name,
            max_braking_g=DRUM_BRAKES_1920S.max_braking_g,
            efficiency=DRUM_BRAKES_1920S.efficiency,
        ),
    )


def create_blue_bird_1927():
    return Vehicle(
        name="Blue Bird 1927",
        mass=2500,
        power=450,
        cd=0.28,
        area=2.2,
        tyre_grip_factor=0.85,
        engine=NAPIER_LION_VIIA,
        wheel_radius_m=0.38,
        gearbox=Gearbox(
            ratios=(2.4, 1.6, 1.0),
            final_drive_ratio=1.1,
            shift_up_rpm=2_600,
            shift_down_rpm=1_200,
        ),
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
        power=36,
        cd=0.95,
        area=1.7,
        tyre_grip_factor=0.75,
        engine=WELCH_HEMI,
        wheel_radius_m=0.35,
        gearbox=Gearbox(
            ratios=(3.2, 1.8, 1.0),
            final_drive_ratio=3.5,
            shift_up_rpm=2_300,
            shift_down_rpm=1_100,
        ),
        brakes=BrakeSystem(
            name=DRUM_BRAKES_1920S.name,
            max_braking_g=DRUM_BRAKES_1920S.max_braking_g,
            efficiency=DRUM_BRAKES_1920S.efficiency,
        ),
    )


AVAILABLE_CARS = {
    "1": create_brick_mk1,
    "2": create_blue_bird_1927,
    "3": create_jeantaud,
}


def select_car():
    print("\n=== SELECT VEHICLE ===")
    for choice, create_vehicle in AVAILABLE_CARS.items():
        print(f"{choice}. {create_vehicle().name}")

    choice = input("Choose a vehicle: ").strip()
    if choice not in AVAILABLE_CARS:
        print("Invalid choice. Using Brick Mk1.")
        choice = "1"
    return AVAILABLE_CARS[choice]()