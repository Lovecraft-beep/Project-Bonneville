# Project Bonneville

from vehicle import Vehicle
from simulation import run_simulation

# main loop
def main():
    print('LSR Simulator')

    vehicle = Vehicle(
        name="Brick Mk1",
        mass=3000,
        power=2000,
        cd=0.30,
        area=2.5,
        traction_coefficient=0.3 #Bonneville is a low traction environment, so we will use a low traction coefficient
    )

    vehicle.display()

    print("\nRunning simulation...")

    result = run_simulation(vehicle, track_miles=10.0, measured_mile_start=4.0)

    print(f"\nMeasured Mile Speed: {result.measured_mile_speed_mph} mph")
    print(f"Measured Mile Time: {result.measured_mile_time_seconds} seconds")
    print(f"Peak Speed: {result.peak_speed_mph} mph")
    print(f"Total Run Time: {result.total_time_seconds} seconds")
    print(f"Completed: {result.completed}")

    print("\nTime   Distance   Speed   Accel G   Phase")
    print("----   --------   -----   -------   ----------------")
    for sample in result.telemetry:
        print(
            f"{sample.time_seconds:4.1f}   "
            f"{sample.distance_miles:8.3f}   "
            f"{sample.speed_mph:5.1f}   "
            f"{sample.acceleration_g:7.3f}   "
            f"{sample.phase}"
        )


if __name__ == "__main__":
    main()