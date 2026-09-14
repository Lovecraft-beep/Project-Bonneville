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
    distance_from_midlands_miles: float = 0.0
    base_entry_cost_gbp: float = 0.0
    transport_cost_per_mile_gbp: float = 0.0

    @property
    def event_cost_gbp(self):
        return round(
            self.base_entry_cost_gbp
            + self.distance_from_midlands_miles * self.transport_cost_per_mile_gbp
        )


BONNEVILLE_SALT_FLATS = Track(
    name="Bonneville Salt Flats",
    length_miles=10.0,
    measured_mile_start=4.5,
    altitude_m=1_291.0,
    temperature_c=30.0,
    air_density_kg_m3=1.08,
    friction_factor=0.3,
    distance_from_midlands_miles=4_300.0,
    base_entry_cost_gbp=2_500.0,
    transport_cost_per_mile_gbp=2.0,
)


BROOKLANDS = Track(
    name="Brooklands",
    length_miles=3.0,
    measured_mile_start=1.0,
    altitude_m=15.0,
    temperature_c=15.0,
    air_density_kg_m3=1.225,
    friction_factor=0.8,
    distance_from_midlands_miles=25.0,
    base_entry_cost_gbp=250.0,
    transport_cost_per_mile_gbp=2.0,
)


PENDINE_SANDS = Track(
    name="Pendine Sands",
    length_miles=7.0,
    measured_mile_start=3.0,
    altitude_m=5.0,
    temperature_c=15.0,
    air_density_kg_m3=1.225,
    friction_factor=0.55,
    distance_from_midlands_miles=250.0,
    base_entry_cost_gbp=500.0,
    transport_cost_per_mile_gbp=2.0,
)


DAYTONA_BEACH = Track(
    name="Daytona Beach",
    length_miles=23.0,
    measured_mile_start=10.0,
    altitude_m=3.0,
    temperature_c=22.0,
    air_density_kg_m3=1.20,
    friction_factor=0.65,
    distance_from_midlands_miles=4_200.0,
    base_entry_cost_gbp=1_500.0,
    transport_cost_per_mile_gbp=2.0,
)


BLACK_ROCK_DESERT = Track(
    name="Black Rock Desert",
    length_miles=20.0,
    measured_mile_start=10.0,
    altitude_m=1_173.0,
    temperature_c=30.0,
    air_density_kg_m3=1.09,
    friction_factor=0.75,
    distance_from_midlands_miles=4_600.0,
    base_entry_cost_gbp=1_800.0,
    transport_cost_per_mile_gbp=2.0,
)


DONCASTER_TEST_TRACK = Track(
    name="Doncaster Test Track",
    length_miles=3.0,
    measured_mile_start=1.0,
    altitude_m=17.0,
    temperature_c=12.0,
    air_density_kg_m3=1.225,
    friction_factor=0.95,
    distance_from_midlands_miles=150.0,
    base_entry_cost_gbp=300.0,
    transport_cost_per_mile_gbp=2.0,
)


AVAILABLE_TRACKS = {
    "1": BONNEVILLE_SALT_FLATS,
    "2": BROOKLANDS,
    "3": PENDINE_SANDS,
    "4": DAYTONA_BEACH,
    "5": BLACK_ROCK_DESERT,
    "6": DONCASTER_TEST_TRACK,
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