"""Rebuild garage vehicles and apply their saved component settings."""

from copy import deepcopy
from dataclasses import replace

from brakes import BRAKE_BY_NAME
from chassis import CHASSIS_BY_ID
from engines import AVAILABLE_ENGINES, tune_engine
from gearbox import AVAILABLE_GEARBOXES
from research import aerodynamics_effects
from vehicle import Vehicle


def apply_engine_tune(vehicle, stage):
    """Install the given tune stage on the vehicle's stock engine."""
    engine = tune_engine(AVAILABLE_ENGINES[vehicle.engine.name], stage)
    vehicle.engine = engine
    vehicle.power = engine.power_hp
    vehicle.peak_torque_nm = engine.torque_nm
    vehicle.engine_tune_stage = stage


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
        tyre_grip_factor=(
            chassis.tyre_grip_factor
            if entry.tyre_grip_factor is None
            else entry.tyre_grip_factor
        ),
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
