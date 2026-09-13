# Project Bonneville

from vehicle import Vehicle
from simulation import run_simulation
from engines import NAPIER_LION_VIIA
from gearbox import Gearbox
from brakes import DRUM_BRAKES_1920S

# main loop
def main():
    print('LSR Simulator')

    vehicle = Vehicle(
        name="Brick Mk1",
        mass=3000,
        power=450,
        cd=0.30,
        area=2.5,
        tyre_grip_factor=0.8,
        engine=NAPIER_LION_VIIA,
        wheel_radius_m=0.4,
        gearbox=Gearbox(
            ratios=(2.5, 1.7, 1.0),
            final_drive_ratio=1.15,
            shift_up_rpm=2_600,
            shift_down_rpm=1_200,
        ),
        brakes=DRUM_BRAKES_1920S,
    )

    vehicle.display()

    print("\nRunning simulation...")

    result = run_simulation(
        vehicle,
        track_miles=10.0,
        measured_mile_start=4.5,
        track_friction_factor=0.3,
    )

    print(f"\nMeasured Mile Speed: {result.measured_mile_speed_mph} mph")
    print(f"Measured Mile Time: {result.measured_mile_time_seconds} seconds")
    print(f"Peak Speed: {result.peak_speed_mph} mph")
    print(f"Total Run Time: {result.total_time_seconds} seconds")
    print(f"Total Distance Run: {result.total_distance_miles} miles")

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


if __name__ == "__main__":
    main()