"""Custom vehicle construction for Project Bonneville."""

from copy import deepcopy
from dataclasses import replace

from brakes import BRAKE_BY_NAME, select_brakes
from chassis import CHASSIS_BY_ID, select_chassis
from engines import AVAILABLE_ENGINES, ENGINE_TUNE_STAGES, select_engine, tune_engine
from gearbox import AVAILABLE_GEARBOXES, optimize_gearbox_for_engine, select_gearbox
from management import GarageVehicle
from research import aerodynamics_effects
from vehicle import Vehicle


def design_vehicle(campaign):
    """Walk the player through designing a vehicle.

    Returns (vehicle, cost_gbp, garage_entry), or (None, None, None) if cancelled.
    """
    print("\n=== VEHICLE DESIGNER ===")
    name = input("Name your vehicle: ").strip() or "Unnamed Special"

    chassis = select_chassis(campaign.research.chassis_technology)
    engine = select_engine(campaign.research.engine_technology)
    gearbox = select_gearbox(engine)
    brakes = select_brakes(current_year=campaign.current_year)
    aero_effects = aerodynamics_effects(campaign.research.aerodynamics_technology)

    vehicle = Vehicle(
        name=name,
        mass=chassis.mass_kg,
        cd=chassis.drag_coefficient * (1.0 - aero_effects["drag_reduction"]),
        area=chassis.frontal_area_m2,
        tyre_grip_factor=chassis.tyre_grip_factor,
        engine=engine,
        wheel_radius_m=chassis.wheel_radius_m,
        gearbox=gearbox,
        brakes=brakes,
        component_mass_enabled=True,
    )
    vehicle.chassis_id = chassis.chassis_id
    vehicle.aerodynamics_technology = tuple(campaign.research.aerodynamics_technology)

    cost_gbp = round(
        chassis.cost_gbp + engine.purchase_cost_gbp + gearbox.cost_gbp + brakes.cost_gbp
    )

    print("\n=== REVIEW SPECIFICATION ===")
    vehicle.display()
    print(f"Chassis: {chassis.name} (GBP {chassis.cost_gbp:,.0f})")
    print(f"Construction Cost: GBP {cost_gbp:,.0f}")
    print(f"Campaign funds: GBP {campaign.team.cash:,.0f}")

    confirm = input("Build this vehicle? Type 'yes' to confirm: ").strip().lower()
    if confirm != "yes":
        print("Vehicle design cancelled.")
        return None, None, None

    garage_entry = GarageVehicle(
        vehicle_name=name,
        chassis_id=chassis.chassis_id,
        engine_name=engine.name,
        gearbox_name=gearbox.name,
        brakes_name=brakes.name,
        aerodynamics_technology=tuple(campaign.research.aerodynamics_technology),
        gearbox_ratios=tuple(gearbox.gears),
        gearbox_final_drive=gearbox.final_drive_ratio,
    )
    return vehicle, cost_gbp, garage_entry


def change_vehicle_component(vehicle, campaign, allow_gearbox_optimization=False):
    """Change one installed component and return whether a change was made."""
    options = [
        ("Replace engine", lambda: _replace_engine(vehicle, campaign)),
        ("Tune engine", lambda: tune_engine_stage(vehicle)),
        ("Replace gearbox", lambda: _replace_gearbox(vehicle)),
        ("Tune gear ratios", lambda: tune_gearbox(vehicle)),
        ("Brakes", lambda: _replace_brakes(vehicle, campaign)),
    ]
    if has_new_aerodynamics(vehicle, campaign):
        options.append(
            ("Fit latest aerodynamics package", lambda: fit_latest_aerodynamics(vehicle, campaign))
        )
    if allow_gearbox_optimization:
        options.append(("Optimise gear ratios", lambda: _optimise_gearbox(vehicle)))

    print("\n=== CHANGE COMPONENT ===")
    for number, (label, _) in enumerate(options, start=1):
        print(f"{number}. {label}")
    print(f"{len(options) + 1}. Keep current components")
    choice = input("Choose a component: ").strip()

    if choice == str(len(options) + 1):
        return False
    try:
        _, change = options[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid component choice.")
        return False
    return change()


def _replace_engine(vehicle, campaign):
    engine = select_engine(
        campaign.research.engine_technology,
        current_engine=vehicle.engine,
    )
    vehicle.engine = engine
    vehicle.power = engine.power_hp
    vehicle.peak_torque_nm = engine.torque_nm
    vehicle.engine_tune_stage = 0
    print(f"Updated component on {vehicle.name}.")
    return True


def _replace_gearbox(vehicle):
    vehicle.gearbox = select_gearbox(
        vehicle.engine,
        current_gearbox=vehicle.gearbox,
    )
    print(f"Updated component on {vehicle.name}.")
    return True


def _replace_brakes(vehicle, campaign):
    vehicle.brakes = select_brakes(
        current_brakes=vehicle.brakes,
        current_year=campaign.current_year,
    )
    print(f"Updated component on {vehicle.name}.")
    return True


def _optimise_gearbox(vehicle):
    optimize_gearbox_for_engine(vehicle)
    print(
        f"Optimised gearbox: ratios {vehicle.gearbox.gears}, "
        f"final drive {vehicle.gearbox.final_drive_ratio}."
    )
    return True


def has_new_aerodynamics(vehicle, campaign):
    """Return whether the team has researched aero not yet fitted to this car."""
    return vehicle.chassis_id is not None and bool(
        set(campaign.research.aerodynamics_technology)
        - set(vehicle.aerodynamics_technology)
    )


def fit_latest_aerodynamics(vehicle, campaign):
    """Refit the car's bodywork with every aero technology researched so far."""
    researched = tuple(campaign.research.aerodynamics_technology)
    drag_reduction = aerodynamics_effects(researched)["drag_reduction"]
    previous_cd = vehicle.cd
    vehicle.cd = CHASSIS_BY_ID[vehicle.chassis_id].drag_coefficient * (
        1.0 - drag_reduction
    )
    vehicle.aerodynamics_technology = researched
    print(f"Fitted latest aerodynamics: Cd {previous_cd:.3f} -> {vehicle.cd:.3f}.")
    return True


def apply_engine_tune(vehicle, stage):
    """Install the given tune stage on the vehicle's stock engine."""
    engine = tune_engine(AVAILABLE_ENGINES[vehicle.engine.name], stage)
    vehicle.engine = engine
    vehicle.power = engine.power_hp
    vehicle.peak_torque_nm = engine.torque_nm
    vehicle.engine_tune_stage = stage


def tune_engine_stage(vehicle):
    """Trade engine reliability for power by choosing a tune stage."""
    stock_engine = AVAILABLE_ENGINES.get(vehicle.engine.name)
    if stock_engine is None:
        print("This engine cannot be tuned.")
        return False

    print("\n=== TUNE ENGINE ===")
    print(f"Current tune: Stage {vehicle.engine_tune_stage}")
    for stage, label, _, _ in ENGINE_TUNE_STAGES:
        tuned = tune_engine(stock_engine, stage)
        marker = "* " if stage == vehicle.engine_tune_stage else "  "
        print(
            f"{stage}. {marker}{label}: {tuned.power_hp:,.1f} hp, "
            f"reliability {tuned.reliability:.0%}"
        )
    try:
        stage = int(input("Choose a tune stage: ").strip())
    except ValueError:
        print("Invalid tune stage. Keeping current tune.")
        return False
    if not 0 <= stage < len(ENGINE_TUNE_STAGES):
        print("That tune stage does not exist.")
        return False
    if stage == vehicle.engine_tune_stage:
        return False

    apply_engine_tune(vehicle, stage)
    print(
        f"Engine tuned to Stage {stage}: {vehicle.engine.power_hp:,.1f} hp, "
        f"reliability {vehicle.engine.reliability:.0%}."
    )
    return True


def tune_gearbox(vehicle):
    """Edit one gearbox ratio or the final drive for a comparison rerun."""
    gearbox = vehicle.gearbox
    print("\n=== TUNE GEARBOX ===")
    print("Current gear ratios: " + " / ".join(f"{ratio:.3f}" for ratio in gearbox.gears))
    print(f"Current final drive: {gearbox.final_drive_ratio:.3f}")
    print("1. Adjust final drive")
    print("2. Adjust individual gear")
    print("3. Keep current setup")
    choice = input("Choose a tuning action: ").strip()

    if choice == "1":
        try:
            final_drive = float(input("New final drive ratio: ").strip())
        except ValueError:
            print("Invalid final drive. Keeping current setup.")
            return False
        if not 0.5 <= final_drive <= 6.0:
            print("Final drive must be between 0.500 and 6.000.")
            return False
        gearbox.final_drive = round(final_drive, 3)
    elif choice == "2":
        try:
            gear_number = int(input(f"Gear number (1-{gearbox.gear_count}): ").strip())
            ratio = float(input("New gear ratio: ").strip())
        except ValueError:
            print("Invalid gear or ratio. Keeping current setup.")
            return False
        if not 1 <= gear_number <= gearbox.gear_count:
            print("That gear does not exist.")
            return False
        if not 0.5 <= ratio <= 5.0:
            print("Gear ratio must be between 0.500 and 5.000.")
            return False
        ratios = list(gearbox.gears)
        ratios[gear_number - 1] = round(ratio, 3)
        gearbox.gears = tuple(ratios)
    elif choice == "3":
        return False
    else:
        print("Invalid tuning choice.")
        return False

    print(
        "Updated gearbox: ratios "
        + " / ".join(f"{ratio:.3f}" for ratio in gearbox.gears)
        + f", final drive {gearbox.final_drive_ratio:.3f}."
    )
    return True


def build_vehicle_from_garage_entry(entry):
    """Reconstruct a fresh Vehicle instance from a saved garage entry."""
    chassis = CHASSIS_BY_ID[entry.chassis_id]
    engine = AVAILABLE_ENGINES[entry.engine_name]
    gearbox = deepcopy(AVAILABLE_GEARBOXES[entry.gearbox_name])
    if entry.gearbox_ratios:
        gearbox.gears = tuple(entry.gearbox_ratios)
    if entry.gearbox_final_drive is not None:
        gearbox.final_drive = entry.gearbox_final_drive
    brakes = replace(BRAKE_BY_NAME[entry.brakes_name])
    aero_effects = aerodynamics_effects(entry.aerodynamics_technology)
    vehicle = Vehicle(
        name=entry.vehicle_name,
        mass=chassis.mass_kg,
        cd=chassis.drag_coefficient * (1.0 - aero_effects["drag_reduction"]),
        area=chassis.frontal_area_m2,
        tyre_grip_factor=chassis.tyre_grip_factor,
        engine=engine,
        wheel_radius_m=chassis.wheel_radius_m,
        gearbox=gearbox,
        brakes=brakes,
        component_mass_enabled=True,
    )
    vehicle.chassis_id = entry.chassis_id
    vehicle.aerodynamics_technology = tuple(entry.aerodynamics_technology)
    if entry.engine_tune_stage:
        apply_engine_tune(vehicle, entry.engine_tune_stage)
    return vehicle
