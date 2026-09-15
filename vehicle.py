from engines import Engine
from gearbox import Gearbox
from brakes import BrakeSystem


# Define the Vehicle class
class Vehicle:
    def __init__(
        self,
        name,
        mass,
        cd,
        area,
        tyre_grip_factor=1.0,
        engine=None,
        wheel_radius_m=0.4,
        gearbox=None,
        brakes=None,
        model_year=None,
        length_m=None,
        height_m=None,
        wheelbase_m=None,
    ):
        self.name = name  # Name of the vehicle
        self.model_year = model_year
        self.mass = mass  # Mass of the vehicle in kg
        self.length_m = length_m
        self.height_m = height_m
        self.wheelbase_m = wheelbase_m
        if engine is None:
            raise ValueError("vehicle must have an engine")
        self.engine = engine
        self.power = engine.power_hp  # Power in hp
        self.cd = cd  # Drag coefficient
        self.area = area  # Frontal area in m^2
        self.tyre_grip_factor = tyre_grip_factor
        self.peak_torque_nm = engine.torque_nm
        self.wheel_radius_m = wheel_radius_m
        self.gearbox = gearbox or Gearbox(name="Standard Gearbox", gears=(3.0,))
        self.brakes = brakes

    def display(self):
        print("\n=== VEHICLE ===")
        print(f"Name: {self.name}")
        if self.model_year:
            print(f"Year: {self.model_year}")
        if self.engine:
            print(f"Engine: {self.engine.name}")
            print(f"Cylinders: {self.engine.cylinders}")
            print(f"Engine Reliability: {self.engine.reliability}")
            print(f"Engine Max RPM: {self.engine.max_rpm}")
            print(f"Torque Curve: {self.engine.torque_curve_type}")
        print(f"Mass: {self.mass} kg")
        if self.length_m:
            print(f"Length: {self.length_m} m")
        if self.height_m:
            print(f"Height: {self.height_m} m")
        if self.wheelbase_m:
            print(f"Wheelbase: {self.wheelbase_m} m")
        print(f"Power: {self.power} hp")
        print(f"Cd: {self.cd}")
        print(f"Area: {self.area} m²")
        print(f"Tyre Grip Factor: {self.tyre_grip_factor}")
        print(f"Peak Torque: {self.peak_torque_nm} Nm")
        print(f"Gearbox: {self.gearbox.name}")
        print(f"Gears: {self.gearbox.gear_count}")
        print(f"Final Drive Ratio: {self.gearbox.final_drive_ratio}")
        print(f"Wheel Radius: {self.wheel_radius_m} m")
        print(f"Gearbox Mass: {self.gearbox.mass_kg} kg")
        print(f"Gearbox Reliability: {self.gearbox.reliability}")
        if self.brakes:
            print(f"Brakes: {self.brakes.name}")
            print(f"Brake Efficiency: {self.brakes.efficiency}")