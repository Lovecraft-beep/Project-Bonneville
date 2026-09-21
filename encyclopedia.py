"""Historical Encyclopedia: browse-only reference data for Project Bonneville."""

from brakes import BRAKE_CATALOG
from cars import AVAILABLE_CARS
from engines import ALL_ENGINES
from gearbox import PREBUILT_GEARBOXES, TRANSMISSION_CATALOG
from research import CHASSIS_TECHNOLOGY_TREE, ENGINE_TECHNOLOGY_TREE, ERAS
from tracks import AVAILABLE_TRACKS


def print_vehicles():
    print("\n=== VEHICLES ===")
    for factory in AVAILABLE_CARS.values():
        factory().display()


def print_engines():
    print("\n=== ENGINES ===")
    for engine in ALL_ENGINES:
        print(
            f"{engine.name} ({engine.era or 'era unknown'}): {engine.power_hp} hp, "
            f"{engine.torque_nm} Nm, reliability {engine.reliability:.0%}, "
            f"{engine.configuration}"
        )


def print_gearboxes():
    print("\n=== GEARBOXES & TRANSMISSIONS ===")
    print("Historical gearboxes:")
    for gearbox in PREBUILT_GEARBOXES:
        print(
            f"  {gearbox.name}: {gearbox.gear_count} gears, "
            f"final drive {gearbox.final_drive}, GBP {gearbox.cost_gbp:,.0f}"
        )
    print("Vehicle designer transmissions:")
    for gearbox in TRANSMISSION_CATALOG:
        print(
            f"  {gearbox.name}: {gearbox.gear_count} gears, "
            f"final drive {gearbox.final_drive}, GBP {gearbox.cost_gbp:,.0f}"
        )


def print_brakes():
    print("\n=== BRAKE SYSTEMS ===")
    for brakes in BRAKE_CATALOG:
        print(
            f"{brakes.name}: {brakes.max_braking_g}g max, "
            f"{brakes.efficiency:.0%} efficiency, GBP {brakes.cost_gbp:,.0f}"
        )


def print_tracks():
    print("\n=== TRACKS ===")
    for track in AVAILABLE_TRACKS.values():
        print(
            f"{track.name}: {track.length_miles} miles, "
            f"altitude {track.altitude_m} m, GBP {track.event_cost_gbp:,.0f} event cost"
        )


def print_technologies():
    print("\n=== TECHNOLOGY ERAS ===")
    for era in ERAS:
        print(f"\n{era.name} ({era.year_range_label}) - {era.theme}")
        print("  Themes: " + ", ".join(era.technology_themes))
        print("  Challenges: " + ", ".join(era.challenges))
        chassis_tiers = [
            node.name for node in CHASSIS_TECHNOLOGY_TREE if node.era == era.name
        ]
        engine_types = [
            node.name for node in ENGINE_TECHNOLOGY_TREE if node.era == era.name
        ]
        print("  Chassis tiers: " + ", ".join(chassis_tiers))
        print("  Engine types: " + ", ".join(engine_types))


ENCYCLOPEDIA_SECTIONS = {
    "1": ("Vehicles", print_vehicles),
    "2": ("Engines", print_engines),
    "3": ("Gearboxes & Transmissions", print_gearboxes),
    "4": ("Brake Systems", print_brakes),
    "5": ("Tracks", print_tracks),
    "6": ("Technology Eras", print_technologies),
}


def run_encyclopedia():
    """Present the encyclopedia menu and print whichever section is picked."""
    print("\n=== HISTORICAL ENCYCLOPEDIA ===")
    print("Note: driver biographies aren't modelled yet in this prototype.")
    while True:
        print("\nWhat would you like to browse?")
        for key, (label, _) in ENCYCLOPEDIA_SECTIONS.items():
            print(f"{key}. {label}")
        print("7. Back to Main Menu")

        choice = input("Choose a section: ").strip()
        if choice == "7":
            break

        section = ENCYCLOPEDIA_SECTIONS.get(choice)
        if section is None:
            print("Invalid choice.")
            continue

        _, print_fn = section
        print_fn()
