# Project Bonneville

Project Bonneville is an early prototype for a management and engineering
simulation about the history of world land-speed records.

I see it evolving into a Malcolm Campbell simulator.

The intended game begins with early piston-engine record cars and progresses
through increasingly advanced piston, jet, rocket, and electric vehicles.
Future versions may use BeamNG or Unity to validate vehicle designs and stage
record attempts.

## Current Prototype

The current application runs one command-line land-speed test. It models:

- Vehicle mass, engine power, drag coefficient, and frontal area
- Aerodynamic drag using `Fd = 0.5 * Cd * rho * v^2 * A`
- Rolling resistance
- Drivetrain efficiency
- Tyre grip and track friction limiting launch acceleration
- Engine torque and drivetrain gearing
- A configurable multi-speed gearbox with automatic upshifts
- Timed clutch-based gear changes with clutch slip
- Automatic downshifts during deceleration
- Brake-system efficiency, grip-limited braking, and brake fade
- Aerodynamic braking from speed-dependent drag
- Wheelspin detection when requested force exceeds available traction
- Historically inspired engine definitions, beginning with the Napier Lion
- A selectable vehicle catalogue with Brick Mk1 and Blue Bird 1927
- A selectable track catalogue with Bonneville Salt Flats and Brooklands
- A configurable track length
- A measured mile within the track
- Acceleration, measured-mile travel, and deceleration phases
- Speed, distance, elapsed time, and acceleration in G telemetry
- Engine RPM and current gear in telemetry

The default run uses a 10-mile track with the measured mile beginning at mile
4. Telemetry is recorded at one-second intervals, with an additional final
sample when the run ends between intervals.

## Running the Prototype

From the project directory, run:

```text
python main.py
```

The application presents a vehicle selection menu, then displays the chosen
vehicle configuration, measured-mile result, peak speed, total run time,
distance travelled, and telemetry table.

## Project Files

- `main.py` creates the example vehicle and runs the simulation.
- `cars.py` contains selectable vehicle definitions and the command-line menu.
- `tracks.py` contains selectable track definitions and surface conditions.
- `vehicle.py` defines the `Vehicle` class and its engineering properties.
- `engines.py` contains the available engine definitions.
- `simulation.py` contains the physics loop, drag calculation, validation, and
	telemetry result types.
- `gearbox.py` defines gear ratios, final drive, efficiency, and shift behaviour.
- `brakes.py` defines brake systems, heat buildup, efficiency, and fade.
- `vision.md` describes the longer-term direction of the project.

## Available Vehicles

The current catalogue contains:

- `Brick Mk1`: a heavier Lion-powered prototype with a larger frontal area.
- `Blue Bird 1927`: a lighter, more aerodynamic Lion-powered configuration.
- `Jeantaud`: a 1,400 kg Welch Hemi-powered prototype with estimated
	`Cd=0.95` and `1.7 m^2` frontal area.

Run `python main.py` and choose `1`, `2`, or `3` from the vehicle menu. Each menu
selection creates a fresh vehicle, gearbox, and brake system for the run.

The track menu currently offers Bonneville Salt Flats and Brooklands. Track
length, measured-mile position, altitude, temperature, air density, and surface
friction are stored as track properties. The simulation currently uses track
length, measured-mile position, and friction; altitude, temperature, and air
density are recorded for the future engine and aerodynamic models.

## Vehicle Properties

The current `Vehicle` class accepts:

| Property | Unit | Description |
| --- | --- | --- |
| `name` | - | Vehicle name |
| `mass` | kg | Vehicle mass |
| `power` | hp | Engine power |
| `cd` | - | Aerodynamic drag coefficient |
| `area` | m^2 | Frontal area |
| `tyre_grip_factor` | - | Tyre capability to transmit engine force |
| `peak_torque_nm` | Nm | Engine torque used for low-speed wheel force |
| `first_gear_ratio` | - | First-gear torque multiplication |
| `final_drive_ratio` | - | Final-drive torque multiplication |
| `wheel_radius_m` | m | Radius used to convert wheel torque to force |

The vehicle can use a `Gearbox` with a tuple of gear ratios, a final-drive
ratio, drivetrain efficiency, and an upshift RPM. Engine RPM is calculated from
road speed, wheel radius, the current gear, and the final drive. The prototype
automatically shifts up when the engine reaches the configured shift RPM.

Gear changes take time and are divided into clutch disengagement, gear
selection, and clutch re-engagement. Drive torque is unavailable while the
clutch is disengaged, then ramps back in during re-engagement. The
`clutch_slip_factor` controls how much torque is lost while the clutch is
reconnecting, and telemetry marks samples taken during a shift. During
deceleration, the gearbox downshifts when engine RPM falls below
`shift_down_rpm`. Engine braking is not yet modelled separately from the
braking system.

Vehicles can also reference an engine definition. The current catalogue
includes a historically inspired 1920s Napier Lion VIIA: a 23.9-litre W12
rated here at 900 hp and 1,900 Nm, with a reliability factor of 0.85. It also
includes the 36 hp, four-cylinder Welch Hemi, weighing 120 kg and producing
approximately 203 Nm at a 2,500 RPM limit. The Welch Hemi reliability factor
is provisionally set to 0.80. These values are prototype data intended for gameplay
balancing and will need to be refined as the historical database grows.

## Physics Notes

The simulation uses SI units internally. Speeds are converted to mph for
display, and distances are converted to miles for display.

Aerodynamic drag is calculated with:

```text
Fd = 0.5 * Cd * rho * v^2 * A
```

At low speed, available engine force is limited by the product of the tyre grip
factor and track friction factor:

```text
effective traction = tyre grip factor * track friction factor
```

Engine torque is multiplied by the first-gear and final-drive ratios, then
converted to wheel force using wheel radius. If requested wheel force is
greater than effective traction, the telemetry reports wheelspin and actual
vehicle acceleration is capped by the track surface.

At higher speed, engine power and aerodynamic drag determine acceleration.
During the deceleration phase, braking, aerodynamic drag, and rolling
resistance reduce speed.

The brake system has its own mechanical efficiency and maximum braking
capability. Actual brake force is limited by available tyre and track grip.
Brake temperature increases with braking energy and decreases through cooling;
above the fade threshold, usable brake force is reduced. Aerodynamic braking
is calculated separately from the drag equation and becomes stronger as speed
increases.

This is intentionally an early model. It does not yet include engine torque
curves, wind, gradients, tyre temperature, stability, weather, driver skill,
component failures, carbon brakes, or brake chutes.

## Telemetry

Telemetry will be very important as people develop new technologies and tune
their existing setups. There will need to be screens, graphs, and simulations
which may begin as inaccurate pencil-and-paper estimates, then become more
accurate as mechanical calculators, computers, and CFD are introduced. Think
wind tunnels and all the useful data they provide.

## Direction

The next major systems are likely to include:

- Historical vehicles, teams, locations, and record progression
- Research and Development - Tech Trees?
- Ability to download .csv files of the telemetry
- Technology research and upgrade choices
- Sponsorship, funding, stakeholder set goals
- More detailed engine, tyre, braking, and stability models
- Risk and failure during test runs
- More useful run summaries and visual telemetry
- Optional BeamNG or Unity integration
- If we can get Unity/Gary's Mod/BeamNG working - the record attempt will be driven by the player.

