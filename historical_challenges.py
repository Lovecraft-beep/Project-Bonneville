"""Historical Challenges: attempt to recreate real land-speed record runs."""

from dataclasses import dataclass

from cars import (
    create_blue_bird_1927,
    create_campbell_napier_railton_blue_bird,
    create_darracq_1905,
    create_irving_napier_golden_arrow,
    create_stanley_steamer_rocket,
)
from simulation import run_simulation
from tracks import DAYTONA_BEACH, PENDINE_SANDS


@dataclass(frozen=True)
class Challenge:
    challenge_id: str
    name: str
    description: str
    create_vehicle: object
    track: object
    target_speed_mph: float


# Target speeds are the real historical measured-mile records for each car
# (or the closest well-documented equivalent), used as a benchmark rather
# than a guarantee this simulation reproduces them exactly.
CHALLENGES = (
    Challenge(
        "darracq_1905",
        "Darracq 200hp - Ormond Beach Sprint",
        "Recreate Victor Hemery's 1905 speed trial run.",
        create_darracq_1905,
        DAYTONA_BEACH,
        125.6,
    ),
    Challenge(
        "stanley_1906",
        "Stanley Rocket - Steam Speed Record",
        "Recreate Fred Marriott's 1906 steam-powered record run.",
        create_stanley_steamer_rocket,
        DAYTONA_BEACH,
        127.7,
    ),
    Challenge(
        "blue_bird_1927",
        "Blue Bird 1927 - Pendine Sands Record",
        "Recreate Malcolm Campbell's 1927 record attempt.",
        create_blue_bird_1927,
        PENDINE_SANDS,
        174.9,
    ),
    Challenge(
        "golden_arrow_1929",
        "Irving-Napier Golden Arrow - 1929 Daytona Record",
        "Recreate Henry Segrave's 1929 record run.",
        create_irving_napier_golden_arrow,
        DAYTONA_BEACH,
        231.5,
    ),
    Challenge(
        "blue_bird_1931",
        "Campbell-Napier-Railton Blue Bird - 1931 Daytona Record",
        "Recreate Malcolm Campbell's 1931 record run.",
        create_campbell_napier_railton_blue_bird,
        DAYTONA_BEACH,
        246.1,
    ),
)


def attempt_challenge(challenge):
    """Simulate a challenge's historical vehicle/track and compare to its target."""
    vehicle = challenge.create_vehicle()
    track = challenge.track
    vehicle.display()
    print(f"Track: {track.name}")
    print(f"Target measured-mile speed: {challenge.target_speed_mph:.1f} mph")

    print("\nRunning simulation...")
    result = run_simulation(
        vehicle,
        track_miles=track.length_miles,
        measured_mile_start=track.measured_mile_start,
        track_friction_factor=track.friction_factor,
        air_density_kg_m3=track.air_density_kg_m3,
    )

    print(f"\nMeasured Mile Speed: {result.measured_mile_speed_mph} mph")
    print(f"Peak Speed: {result.peak_speed_mph} mph")
    if result.measured_mile_speed_mph >= challenge.target_speed_mph:
        print("Challenge complete! You matched or beat the historical record.")
    else:
        shortfall = challenge.target_speed_mph - result.measured_mile_speed_mph
        print(f"Not quite: {shortfall:.1f} mph short of the historical record.")


def run_historical_challenges():
    """Present the challenge menu and run whichever the player picks."""
    print("\n=== HISTORICAL CHALLENGES ===")
    while True:
        print("\nAvailable challenges:")
        for number, challenge in enumerate(CHALLENGES, start=1):
            print(
                f"{number}. {challenge.name} "
                f"(target {challenge.target_speed_mph:.1f} mph)"
            )
        back_choice = str(len(CHALLENGES) + 1)
        print(f"{back_choice}. Back to Main Menu")

        choice = input("Choose a challenge: ").strip()
        if choice == back_choice:
            break

        try:
            challenge = CHALLENGES[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid choice.")
            continue

        print(f"\n=== {challenge.name} ===")
        print(challenge.description)
        attempt_challenge(challenge)
