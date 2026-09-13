"""Track definitions for Project Bonneville."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Track:
    name: str
    length_miles: float
    measured_mile_start: float
    altitude_m: float
    temperature_c: float
    air_density_kg_m3: float
    friction_factor: float


BONNEVILLE_SALT_FLATS = Track(
    name="Bonneville Salt Flats",
    length_miles=10.0,
    measured_mile_start=4.5,
    altitude_m=1_291.0,
    temperature_c=30.0,
    air_density_kg_m3=1.08,
    friction_factor=0.3,
)


BROOKLANDS = Track(
    name="Brooklands",
    length_miles=3.0,
    measured_mile_start=1.0,
    altitude_m=15.0,
    temperature_c=15.0,
    air_density_kg_m3=1.225,
    friction_factor=0.8,
)


AVAILABLE_TRACKS = {
    "1": BONNEVILLE_SALT_FLATS,
    "2": BROOKLANDS,
}


def select_track():
    print("\n=== SELECT TRACK ===")
    for choice, track in AVAILABLE_TRACKS.items():
        print(f"{choice}. {track.name}")

    choice = input("Choose a track: ").strip()
    if choice not in AVAILABLE_TRACKS:
        print("Invalid choice. Using Bonneville Salt Flats.")
        choice = "1"
    return AVAILABLE_TRACKS[choice]