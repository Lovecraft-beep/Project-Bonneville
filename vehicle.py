from engines import Engine
from gearbox import Gearbox
from brakes import BrakeSystem


# Define the Vehicle class
class Vehicle:
    def __init__(
        self,
        name,
        mass,
        power,
        cd,
        area,
        tire_grip_factor=1.0,
        engine=None,
        peak_torque_nm=None,
        wheel_radius_m=0.4,
        gearbox=None,
        brakes=None,
    ):
        self.name = name  # Name of the vehicle
        self.mass = mass  # Mass of the vehicle in kg
        self.engine = engine
        self.power = engine.power_hp if engine else power  # Power in hp
        self.cd = cd  # Drag coefficient
        self.area = area  # Frontal area in m^2
        self.tire_grip_factor = tire_grip_factor
        self.peak_torque_nm = (
            peak_torque_nm
            if peak_torque_nm is not None
            else engine.torque_nm
            if engine
            else 2500.0
        )
        self.wheel_radius_m = wheel_radius_m
        self.gearbox = gearbox or Gearbox(ratios=(3.0,))
        self.brakes = brakes

    def display(self):
        print("\n=== VEHICLE ===")
        print(f"Name: {self.name}")
        if self.engine:
            print(f"Engine: {self.engine.name}")
            print(f"Engine Reliability: {self.engine.reliability}")
            print(f"Engine Max RPM: {self.engine.max_rpm}")
        print(f"Mass: {self.mass} kg")
        print(f"Power: {self.power} hp")
        print(f"Cd: {self.cd}")
        print(f"Area: {self.area} m²")
        print(f"Tire Grip Factor: {self.tire_grip_factor}")
        print(f"Peak Torque: {self.peak_torque_nm} Nm")
        print(f"Gears: {self.gearbox.gear_count}")
        print(f"Final Drive Ratio: {self.gearbox.final_drive_ratio}")
        print(f"Wheel Radius: {self.wheel_radius_m} m")
        if self.brakes:
            print(f"Brakes: {self.brakes.name}")
            print(f"Brake Efficiency: {self.brakes.efficiency}")