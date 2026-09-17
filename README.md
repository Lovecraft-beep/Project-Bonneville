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
- A selectable vehicle catalogue including Brick Mk1, Blue Bird 1927, and the
	1931 Campbell-Napier-Railton Blue Bird
- A selectable track catalogue with Bonneville Salt Flats, Brooklands, Pendine
	Sands, Daytona Beach, Black Rock Desert, Doncaster Test Track, and Public Roads
- A configurable track length
- A measured mile within the track
- Acceleration, measured-mile travel, and deceleration phases
- Speed, distance, elapsed time, and acceleration in G telemetry
- Engine RPM and current gear in telemetry
- Persistent historical run records with vehicle, track, and summary data

## Management Costs

Engines have a base cost and rarity factor. Purchase cost increases with engine
power and rarity. Tracks have an entry cost and a transport cost based on their
distance from the Midlands of England. The selected engine cost, track event
cost, and estimated combined cost are displayed before each run.

The prototype also has a persistent campaign budget. A new campaign starts
with GBP 100,000. Each completed run pays for the selected engine, gearbox,
and track event. Runs that exceed the available budget are refused before the
simulation starts. The campaign stores remaining funds, completed-run count,
and the best measured-mile speed in `campaign_state.json`.

Campaign management is represented by a `Team` with a name, cash balance,
reputation, engineers, mechanics, and workshop level. These values are ready
to support future hiring, sponsorship, workshop upgrades, and engineering
constraints without coupling them to the physics simulation.

The first research tree is `Engine Technology`, beginning with the `Basic
Engines` era. Its initial nodes are `Multi Cylinder`, `Aluminium Pistons`,
`Supercharging`, `Fuel Injection`, and `Aircraft Engine Conversion`. Research
state is persisted with the campaign; `Basic Engines` is the first available
research project and the five child technologies require it as a prerequisite.

The campaign now has an annual turn structure. Each launch currently acts as
one turn: the team reviews its state, performs a test run, pays the run cost,
and advances to the next year. Research, hiring, workshop upgrades, and other
management actions can become alternative turn actions as they are added.

Test runs now include named failure risks: `Misfire`, `Oil leak`, `Gear
failure`, `Tyre burst`, `Brake fade`, and `Steering vibration`. Failure
probability combines component reliability, a speed factor based on peak speed,
and a team skill modifier from the number of engineers and mechanics. Every
failure causes an aborted run. A team needs at least one engineer and two
mechanics to repair a failure trackside for a future attempt. Aborted failures
are charged and counted, but do not create a successful historical record.

Compatible vehicle classes can select from a gearbox catalogue. The Blue Bird
class currently offers the standard `Blue Bird 3-Speed` and the `Railton
3-Speed LSR`. Each selection receives a fresh gearbox instance so shifting
state is not shared between runs.

Gearboxes also have acquisition costs. The standard Blue Bird gearbox is
currently priced at GBP 4,000, while the specialised Railton 3-Speed LSR is
priced at GBP 12,000. The selected gearbox cost is included in the estimated
total setup cost.
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

## Historical Records

Each simulation is saved to `historical_records.json`, which persists between
sessions. A record stores the car, engine, gearbox, brakes, track, peak speed,
average acceleration and deceleration, full-throttle time, and measured-mile
average speed. The most recent records are displayed after each run.

## Project Files

- `main.py` creates the example vehicle and runs the simulation.
- `management.py` stores campaign funds and completed-run progression.
- `research.py` defines the engine technology tree and research prerequisites.
- `reliability.py` resolves engine failure risk and trackside repairs.
- `cars.py` contains selectable vehicle definitions and the command-line menu.
- `tracks.py` contains selectable track definitions and surface conditions.
- `records.py` saves and displays the persistent historical records table.
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
- `Campbell-Napier-Railton Blue Bird`: a 1931, 3,600 kg car using the Napier
	Lion XI, with `Cd=0.55`, `2.3 m^2` frontal area, and `0.50 m` wheel radius.
- `Irving-Napier Golden Arrow`: Major Segrave's 1929 streamlined record car,
	using the Napier Lion VIIB and Golden Arrow 3-Speed LSR gearbox. Its recorded
	dimensions are 8.43 m long, 1.14 m high, with a 4.07 m wheelbase and 3,661 kg
	mass.
- `Stanley Steamer Rocket`: a 1906 steam-powered record car using a two-cylinder
	150 hp steam engine and direct-drive transmission. It is 4.74 m long and
	0.93 m high, weighs 1,000 kg, and has a 2.49 m wheelbase; remaining prototype
	figures will be refined as historical source data is added.
- `Darracq 1905`: a 1,000 kg car with a 200 hp, 25.422-litre V8, two-speed
	gearbox with a `2.0` final drive, weak mechanical drum brakes, `Cd=0.75`, and
	`1.9 m^2` frontal area. Its prototype gearbox efficiency is set to 85%.

Run `python main.py` and choose `1`, `2`, `3`, `4`, `5`, `6`, or `7` from the vehicle menu. Each menu
selection creates a fresh vehicle, gearbox, and brake system for the run.

When `Blue Bird 1927` is selected, a second menu offers the available Napier
Lion variants. Each variant supplies its own power, torque, RPM limit, mass,
reliability, configuration, displacement, and era.

When the 1931 Campbell-Napier-Railton Blue Bird is selected, the player can
also choose its Napier Lion variant and gearbox. Its defaults are the Napier
Lion XI and Railton 3-Speed LSR.

The track menu currently offers Bonneville Salt Flats, Brooklands, Pendine
Sands, Daytona Beach, Black Rock Desert, and Doncaster Test Track. Track
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
| `cd` | - | Aerodynamic drag coefficient |
| `area` | m^2 | Frontal area |
| `tyre_grip_factor` | - | Tyre capability to transmit engine force |
| `wheel_radius_m` | m | Radius used to convert wheel torque to force |

Each vehicle must reference an `Engine` and a `Gearbox`. Engine power and
torque are derived from the selected engine; gear ratios, final drive,
efficiency, mass, reliability, and shift timings are derived from the selected
gearbox. Car definitions therefore contain only chassis properties and
component choices.

Engines use a generic torque-curve category until verified historical dyno data
is available. `early_piston` torque rises to a mid-range peak then falls near
redline, `supercharged_piston` holds stronger high-RPM torque, and `steam`
delivers high low-RPM torque with a gradual fall at speed. Torque is calculated
from the current engine RPM before gearbox multiplication, and falls to zero
above the engine's maximum RPM.

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

Gearboxes are separate components with their own name, ratios, final drive,
shift time, clutch time, efficiency, mass, and reliability. The
Campbell-Napier-Railton Blue Bird uses the `Railton 3-Speed LSR` gearbox with
ratios `4.01`, `2.27`, and `1.24`.

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

Aerodynamic drag is calculated with the selected track's air density:

```text
Fd = 0.5 * Cd * rho * v^2 * A
```

Air density affects both aerodynamic drag during acceleration and aerodynamic
braking during deceleration. Lower-density air reduces both forces. Standalone
simulation calls default to standard air density unless a track-specific value
is supplied.

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
	Engine trees have started to be implemented
- Ability to download .csv files of the telemetry
- Technology research and upgrade choices
- Sponsorship, funding, stakeholder set goals
- More detailed engine, tyre, braking, and stability models
- Risk and failure during test runs
- More useful run summaries and visual telemetry
- Optional BeamNG or Unity integration
- Eventually I'd like to see simulations of the runs rendered in Unity and even allow the player to pilot the car
- Real rules will apply, two runs in opposite directions within one hour
- Rather than choosing complete vehicles, eventually allow:
	Chassis
	Engine
	Gearbox
	Tyres
	Bodywork
- to be swapped independently.
- The current architecture already supports this direction quite well
