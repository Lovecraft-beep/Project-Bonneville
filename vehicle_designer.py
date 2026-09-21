"""Custom vehicle construction for Project Bonneville."""

from copy import deepcopy
from dataclasses import replace

from brakes import BRAKE_BY_NAME, select_brakes
from chassis import CHASSIS_BY_ID, select_chassis
from engines import AVAILABLE_ENGINES, select_engine
from gearbox import AVAILABLE_GEARBOXES, select_gearbox
from management import GarageVehicle
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
    brakes = select_brakes()

    vehicle = Vehicle(
        name=name,
        mass=chassis.mass_kg,
        cd=chassis.drag_coefficient,
        area=chassis.frontal_area_m2,
        tyre_grip_factor=chassis.tyre_grip_factor,
        engine=engine,
        wheel_radius_m=chassis.wheel_radius_m,
        gearbox=gearbox,
        brakes=brakes,
    )

    cost_gbp = round(
        chassis.cost_gbp
        + engine.purchase_cost_gbp
        + gearbox.cost_gbp
        + brakes.cost_gbp
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
    )
    return vehicle, cost_gbp, garage_entry


def build_vehicle_from_garage_entry(entry):
    """Reconstruct a fresh Vehicle instance from a saved garage entry."""
    chassis = CHASSIS_BY_ID[entry.chassis_id]
    engine = AVAILABLE_ENGINES[entry.engine_name]
    gearbox = deepcopy(AVAILABLE_GEARBOXES[entry.gearbox_name])
    brakes = replace(BRAKE_BY_NAME[entry.brakes_name])
    return Vehicle(
        name=entry.vehicle_name,
        mass=chassis.mass_kg,
        cd=chassis.drag_coefficient,
        area=chassis.frontal_area_m2,
        tyre_grip_factor=chassis.tyre_grip_factor,
        engine=engine,
        wheel_radius_m=chassis.wheel_radius_m,
        gearbox=gearbox,
        brakes=brakes,
    )
