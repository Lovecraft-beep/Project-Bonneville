# Project Bonneville

from simulation import run_simulation
from cars import select_car
from tracks import select_track

# main loop
def main():
    print('LSR Simulator')

    vehicle = select_car()
    track = select_track()
    vehicle.display()
    print(f"Track: {track.name}")
    print(f"Altitude: {track.altitude_m} m")
    print(f"Temperature: {track.temperature_c} C")
    print(f"Air Density: {track.air_density_kg_m3} kg/m^3")
    print(f"Engine Cost: GBP {vehicle.engine.purchase_cost_gbp:,}")
    print(f"Gearbox Cost: GBP {vehicle.gearbox.cost_gbp:,.0f}")
    print(f"Track Event Cost: GBP {track.event_cost_gbp:,.0f}")
    print(
        f"Estimated Total Cost: "
        f"GBP {vehicle.engine.purchase_cost_gbp + vehicle.gearbox.cost_gbp + track.event_cost_gbp:,.0f}"
    )

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
    print(f"Time at Full Throttle: {result.full_throttle_seconds} seconds")
    print(f"Number of Gear Changes: {result.gear_change_count}")
    print(f"Wheelspin Events: {result.wheelspin_event_count}")
    print(f"Maximum Brake Temperature: {result.maximum_brake_temperature_c} C")
    print(f"Measured Mile Speed: {result.measured_mile_speed_mph} mph")


if __name__ == "__main__":
    main()