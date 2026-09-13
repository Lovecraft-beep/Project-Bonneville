# Define the Vehicle class
class Vehicle:
    def __init__(self, name, mass, power, cd, area, traction_coefficient=1.0):
        self.name = name  # Name of the vehicle
        self.mass = mass  # Mass of the vehicle in kg
        self.power = power  # Power of the vehicle in hp
        self.cd = cd  # Drag coefficient
        self.area = area  # Frontal area in m^2
        self.traction_coefficient = traction_coefficient

    def display(self):
        print("\n=== VEHICLE ===")
        print(f"Name: {self.name}")
        print(f"Mass: {self.mass} kg")
        print(f"Power: {self.power} hp")
        print(f"Cd: {self.cd}")
        print(f"Area: {self.area} m²")
        print(f"Tire Grip: {self.traction_coefficient} g")