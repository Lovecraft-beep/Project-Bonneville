# Project6 Bonneville

import sys

from simulation import run_simulation
from cars import select_car
from management import (
    advance_turn,
    calculate_run_cost,
    calculate_workshop_upgrade_cost,
    complete_failed_run,
    complete_run,
    hire_engineer,
    hire_mechanic,
    load_campaign,
    research_engine_technology,
    reset_campaign,
    save_campaign,
    sign_sponsor,
    upgrade_workshop,
    ENGINEER_HIRE_COST_GBP,
    MECHANIC_HIRE_COST_GBP,
)
from records import create_record, display_records, load_records, save_record
from research import available_engine_technologies
from reliability import resolve_run_failure
from sponsors import available_sponsors
from tracks import select_track


def launch_ui():
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtWidgets import QApplication
        from ui.main_window import ProjectBonnevilleWindow
    except Exception as exc:  # pragma: no cover - environment-specific setup failure
        print(f"Unable to start PySide6: {exc}")
        print("This environment appears to be headless or missing the Qt runtime.")
        print("Run the app on a desktop machine, or use a GUI-enabled terminal session.")
        return 1

    if not QGuiApplication.platformName():
        print("No desktop GUI platform is available for PySide6.")
        print("This build requires a real desktop session, not a headless terminal.")
        return 1

    app = QApplication(sys.argv)
    window = ProjectBonnevilleWindow()
    window.show()
    return app.exec()


def print_status(campaign):
    print(
        f"\nTurn {campaign.turn_number} | "
        f"{campaign.current_year} season"
    )
    print(f"Team: {campaign.team.name}")
    print(f"Campaign funds: GBP {campaign.team.cash:,.0f}")
    print(f"Reputation: {campaign.team.reputation:.1f}")
    print(
        f"Staff: {campaign.team.engineers} engineers, "
        f"{campaign.team.mechanics} mechanics"
    )
    print(f"Workshop level: {campaign.team.workshop_level}")
    print(
        f"Engine technology level: "
        f"{campaign.research.engine_technology_level}"
    )
    available_technologies = available_engine_technologies(
        campaign.research.engine_technology
    )
    if available_technologies:
        print(
            "Research available: "
            + ", ".join(node.name for node in available_technologies)
        )
    print(f"Completed runs: {campaign.completed_runs}")
    print(f"Failed runs: {campaign.failed_runs}")
    if campaign.sponsorship.active_sponsors:
        print("Sponsors: " + ", ".join(campaign.sponsorship.active_sponsors))
    available = available_sponsors(
        campaign.team.reputation, campaign.sponsorship.active_sponsors
    )
    if available:
        print(
            "Sponsorship offers available: "
            + ", ".join(sponsor.name for sponsor in available)
        )
    if campaign.best_measured_mile_speed_mph:
        print(
            f"Best measured-mile speed: "
            f"{campaign.best_measured_mile_speed_mph:.1f} mph"
        )


def action_test_run(campaign):
    """Run the test-run turn action: select a car and track, then simulate."""
    vehicle = select_car()
    track = select_track()
    run_cost = calculate_run_cost(vehicle, track)
    vehicle.display()
    print(f"Track: {track.name}")
    print(f"Altitude: {track.altitude_m} m")
    print(f"Temperature: {track.temperature_c} C")
    print(f"Air Density: {track.air_density_kg_m3} kg/m^3")
    print(f"Engine Cost: GBP {vehicle.engine.purchase_cost_gbp:,}")
    print(f"Gearbox Cost: GBP {vehicle.gearbox.cost_gbp:,.0f}")
    print(f"Track Event Cost: GBP {track.event_cost_gbp:,.0f}")
    print(f"Estimated Total Cost: GBP {run_cost:,.0f}")

    if run_cost > campaign.funds_gbp:
        print(
            f"Insufficient campaign funds. Need GBP {run_cost:,.0f}, "
            f"but only have GBP {campaign.team.cash:,.0f}."
        )
        return

    print("\nRunning simulation...")

    result = run_simulation(
        vehicle,
        track_miles=track.length_miles,
        measured_mile_start=track.measured_mile_start,
        track_friction_factor=track.friction_factor,
        air_density_kg_m3=track.air_density_kg_m3,
    )

    print("\nTime   Distance   Speed   RPM    Accel G   Gear   Shift   Wheelspin   Brake C   Fade   Phase")
    print("----   --------   -----   -----  -------   ----   -----   ---------   -------   ----   ----------------")
    for sample in result.telemetry:
        print(
            f"{sample.time_seconds:4.1f}   "
            f"{sample.distance_miles:8.3f}   "
            f"{sample.speed_mph:5.1f}   "
            f"{sample.engine_rpm:5}  "
            f"{sample.acceleration_g:7.3f}   "
            f"{sample.gear:4}   "
            f"{str(sample.shifting):5}   "
            f"{str(sample.wheelspin):9}   "
            f"{sample.brake_temperature_c:7.1f}   "
            f"{str(sample.brake_fade):4}   "
            f"{sample.phase}"
        )

    print("\n=== RUN SUMMARY ===")
    print(f"Peak Speed: {result.peak_speed_mph} mph")
    print(f"Average Acceleration: {result.average_acceleration_g} G")
    print(f"Average Deceleration: {result.average_deceleration_g} G")
    print(f"Time at Full Throttle: {result.full_throttle_seconds} seconds")
    print(f"Number of Gear Changes: {result.gear_change_count}")
    print(f"Wheelspin Events: {result.wheelspin_event_count}")
    print(f"Maximum Brake Temperature: {result.maximum_brake_temperature_c} C")
    print(f"Measured Mile Speed: {result.measured_mile_speed_mph} mph")

    outcome = resolve_run_failure(
        vehicle.engine,
        result.peak_speed_mph,
        campaign.team,
        gearbox=vehicle.gearbox,
        brake_fade=any(sample.brake_fade for sample in result.telemetry),
        sponsor_reliability_bonus=campaign.sponsorship.reliability_bonus,
    )
    print(f"Failure probability: {outcome.failure_probability:.1%}")
    if outcome.failed:
        print(f"Aborted run: {outcome.failure_type.name}.")
        complete_failed_run(campaign, run_cost)
        advance_turn(campaign)
        save_campaign(campaign)
        if outcome.repaired:
            print("The team repaired the failure trackside for a future attempt.")
        else:
            print("The team did not have enough staff for a trackside repair.")
        print(f"Failed runs: {campaign.failed_runs}")
        print(
            f"Next turn: {campaign.turn_number} | "
            f"{campaign.current_year} season"
        )
        return

    complete_run(campaign, run_cost, result.measured_mile_speed_mph)
    advance_turn(campaign)
    save_campaign(campaign)
    print(
        f"Next turn: {campaign.turn_number} | "
        f"{campaign.current_year} season"
    )
    print(f"Campaign funds remaining: GBP {campaign.team.cash:,.0f}")

    record = create_record(vehicle, track, result, campaign)
    save_record(record)
    display_records(load_records(), campaign.campaign_id)


def action_research(campaign):
    """Spend cash, engineer time, and a turn to unlock an engine technology."""
    available_technologies = available_engine_technologies(
        campaign.research.engine_technology
    )
    if not available_technologies:
        print("No engine technologies are currently available to research.")
        return

    print("\nAvailable research projects:")
    for index, node in enumerate(available_technologies, start=1):
        print(
            f"{index}. {node.name} "
            f"(GBP {node.cost_gbp:,.0f}, {node.engineers_required} engineer(s))"
        )

    choice = input("Choose a research project (or press Enter to cancel): ").strip()
    if not choice:
        print("Research cancelled.")
        return

    try:
        technology = available_technologies[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice. Research cancelled.")
        return

    try:
        research_engine_technology(campaign, technology.technology_id)
    except ValueError as exc:
        print(f"Unable to research {technology.name}: {exc}")
        return

    advance_turn(campaign)
    save_campaign(campaign)
    print(f"Researched {technology.name}.")
    print(
        f"Next turn: {campaign.turn_number} | "
        f"{campaign.current_year} season"
    )


def action_hire_engineer(campaign):
    try:
        hire_engineer(campaign)
    except ValueError as exc:
        print(f"Unable to hire an engineer: {exc}")
        return

    advance_turn(campaign)
    save_campaign(campaign)
    print(
        f"Hired an engineer for GBP {ENGINEER_HIRE_COST_GBP:,.0f}. "
        f"Engineers: {campaign.team.engineers}."
    )
    print(
        f"Next turn: {campaign.turn_number} | "
        f"{campaign.current_year} season"
    )


def action_hire_mechanic(campaign):
    try:
        hire_mechanic(campaign)
    except ValueError as exc:
        print(f"Unable to hire a mechanic: {exc}")
        return

    advance_turn(campaign)
    save_campaign(campaign)
    print(
        f"Hired a mechanic for GBP {MECHANIC_HIRE_COST_GBP:,.0f}. "
        f"Mechanics: {campaign.team.mechanics}."
    )
    print(
        f"Next turn: {campaign.turn_number} | "
        f"{campaign.current_year} season"
    )


def action_upgrade_workshop(campaign):
    cost_gbp = calculate_workshop_upgrade_cost(campaign.team)
    try:
        upgrade_workshop(campaign)
    except ValueError as exc:
        print(f"Unable to upgrade the workshop: {exc}")
        return

    advance_turn(campaign)
    save_campaign(campaign)
    print(
        f"Upgraded the workshop for GBP {cost_gbp:,.0f}. "
        f"Workshop level: {campaign.team.workshop_level}."
    )
    print(
        f"Next turn: {campaign.turn_number} | "
        f"{campaign.current_year} season"
    )


def action_reset_campaign(campaign):
    """Erase the saved campaign and records, starting over from scratch."""
    confirm = input(
        "This will erase the current campaign and start a new one. "
        "Type 'yes' to confirm: "
    ).strip().lower()
    if confirm != "yes":
        print("Reset cancelled.")
        return None

    new_campaign = reset_campaign()
    save_campaign(new_campaign)
    print("Campaign reset. Starting a new campaign.")
    return new_campaign


def action_sponsorship(campaign):
    """Sign a sponsor for a cash bonus, ongoing income, or a reliability boost."""
    offers = available_sponsors(
        campaign.team.reputation, campaign.sponsorship.active_sponsors
    )
    if not offers:
        print("No sponsorship offers are currently available.")
        return

    print("\nAvailable sponsors:")
    for index, sponsor in enumerate(offers, start=1):
        print(f"{index}. {sponsor.name} - {sponsor.description}")
        print(
            f"   Reputation required: {sponsor.reputation_required:.1f} | "
            f"Signing bonus: GBP {sponsor.signing_bonus_gbp:,.0f} | "
            f"Income per turn: GBP {sponsor.income_per_turn_gbp:,.0f} | "
            f"Reliability bonus: {sponsor.reliability_bonus:.0%}"
        )

    choice = input("Choose a sponsor to sign (or press Enter to cancel): ").strip()
    if not choice:
        print("Sponsorship cancelled.")
        return

    try:
        sponsor = offers[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice. Sponsorship cancelled.")
        return

    try:
        sign_sponsor(campaign, sponsor.sponsor_id)
    except ValueError as exc:
        print(f"Unable to sign {sponsor.name}: {exc}")
        return

    advance_turn(campaign)
    save_campaign(campaign)
    print(f"Signed {sponsor.name}.")
    print(
        f"Next turn: {campaign.turn_number} | "
        f"{campaign.current_year} season"
    )


MENU_ACTIONS = {
    "1": ("Test Run", action_test_run),
    "2": ("Research Basic Engines", action_research),
    "3": ("Hire Engineer", action_hire_engineer),
    "4": ("Hire Mechanic", action_hire_mechanic),
    "5": ("Upgrade Workshop", action_upgrade_workshop),
    "6": ("Reset Campaign", action_reset_campaign),
    "7": ("Sponsorship", action_sponsorship),
}


# main loop
def main():
    print('LSR Simulator')
    campaign = load_campaign()

    while True:
        print_status(campaign)
        print("\nWhat would you like to do?")
        for key, (label, _) in MENU_ACTIONS.items():
            print(f"{key}. {label}")
        print("8. Exit")

        choice = input("Choose an action: ").strip()
        if choice == "8":
            break

        action = MENU_ACTIONS.get(choice)
        if action is None:
            print("Invalid choice.")
            continue

        _, action_fn = action
        updated_campaign = action_fn(campaign)
        if updated_campaign is not None:
            campaign = updated_campaign


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--ui":
        raise SystemExit(launch_ui())
    main()