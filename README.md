# Project Bonneville

Project Bonneville is an early prototype for a management and engineering
simulation about the history of world land-speed records.

I see it evolving into a Malcolm Campbell simulator.

The intended game begins with early piston-engine record cars and progresses
through increasingly advanced piston, jet, rocket, and electric vehicles.
Future versions may use BeamNG or Unity to validate vehicle designs and stage
record attempts.

## Current Prototype

The current program runs one command-line land-speed test. It models:

- Vehicle mass, engine power, drag coefficient, and frontal area
- Aerodynamic drag using `Fd = 0.5 * Cd * rho * v^2 * A`
- Rolling resistance
- Drivetrain efficiency
- Tire traction limiting launch acceleration
- A configurable track length
- A measured mile within the track
- Acceleration, measured-mile travel, and deceleration phases
- Speed, distance, elapsed time, and acceleration in G telemetry

The default run uses a 10-mile track with the measured mile beginning at mile
4. Telemetry is recorded at one-second intervals, with an additional final
sample when the run ends between intervals.

## Running the Prototype

From the project directory, run:

```text
python main.py
```

The program displays the vehicle configuration, measured-mile result, peak
speed, total run time, completion status, and the telemetry table.

## Project Files

- `main.py` creates the example vehicle and runs the simulation.
- `vehicle.py` defines the `Vehicle` class and its engineering properties.
- `simulation.py` contains the physics loop, drag calculation, validation, and
	telemetry result types.
- `vision.md` describes the longer-term direction of the project.

## Vehicle Properties

The current `Vehicle` class accepts:

| Property | Unit | Description |
| --- | --- | --- |
| `name` | - | Vehicle name |
| `mass` | kg | Vehicle mass |
| `power` | hp | Engine power |
| `cd` | - | Aerodynamic drag coefficient |
| `area` | m^2 | Frontal area |
| `traction_coefficient` | g | Maximum tire-road grip used for launch traction |

## Physics Notes

The simulation uses SI units internally. Speeds are converted to mph for
display, and distances are converted to miles for display.

Aerodynamic drag is calculated with:

```text
Fd = 0.5 * Cd * rho * v^2 * A
```

At low speed, available engine force is limited by tire traction. At higher
speed, engine power and aerodynamic drag determine acceleration. During the
deceleration phase, braking, aerodynamic drag, and rolling resistance reduce
speed.

This is intentionally an early model. It does not yet include gear ratios,
engine torque curves, wind, gradients, tire temperature, stability, weather,
driver skill, component failures, or a detailed braking system.

## Direction

The next major systems are likely to include:

- Historical vehicles, teams, locations, and record progression
- Technology research and upgrade choices
- Sponsorship, funding, stakeholder set goals
- More detailed engine, tire, braking, and stability models
- Risk and failure during test runs
- More useful run summaries and visual telemetry
- Optional BeamNG or Unity integration
