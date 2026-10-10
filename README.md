# Project Bonneville

Project Bonneville is an early prototype for a management and engineering
simulation about the history of world land-speed records.

I see it evolving into a Malcolm Campbell simulator.

The intended game begins with early piston-engine record cars and progresses
through increasingly advanced piston, jet, rocket, and electric vehicles.
Future versions may use BeamNG or Unity to validate vehicle designs and stage
record attempts.

## Current Prototype

Version 0.5 introduces a button-driven desktop interface with a campaign
dashboard, research tree, vehicle garage and designer, test-run setup, and
speed/acceleration telemetry graphs. It uses Tkinter from the Python standard
library and keeps the existing campaign, vehicle, reliability, and simulation
rules.

The simulation models:

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

Research is managed through multi-turn engineering projects. Starting a project
spends its cost and reserves its required engineers; it advances on every
campaign turn and unlocks only when its duration is complete. Opening projects
such as `Wind Deflector` require three turns. Active projects and their remaining
time are saved with the campaign, and assigned engineers become available again
at completion. The research screen shows cost, staffing, duration, prerequisites,
and current progress before a project is started.

The campaign starts in Spring 1895 and uses four seasonal turns per year:
Spring, Summer, Autumn, Winter, then Spring of the next year. Only **End turn**
advances the season; research, management actions, and runs do not advance time.
Each seasonal turn pays sponsor income, progresses engineering projects, updates
rival attempts, and resets the test and record sessions. Seasons provide the
calendar foundation for future weather effects; weather is not yet simulated.

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

## Research Progression

Only aerodynamics research is available at the start of a new campaign. Complete
the opening projects in this order to unlock chassis development:

| Project | Required completed research | Turn advances to complete |
| --- | --- | --- |
| Wind Deflector | None | 3 |
| Wheel Fairings / Spats | Wind Deflector | 3 |
| Basic Streamlining | Wheel Fairings / Spats | 3 |
| Carriage Frame | Basic Streamlining | 3 |

Completing Basic Streamlining makes Carriage Frame available to research.
Completing Carriage Frame then unlocks these projects in their respective tabs:

- **Chassis:** Reinforced Ladder Frame
- **Engine:** Pioneer Engines
- **Tyres:** Pneumatic Racing Tyres
- **Brakes:** Mechanical Drum Brakes

From a fresh campaign, this means nine turn advances before Carriage Frame can
be started, and another three to complete it and open those branches. Starting a
project does not advance time; **End turn** progresses active projects by one
season. Wind Deflector started in Spring 1895 completes in Winter 1895, and the
four opening projects can be completed by Spring 1898. Research becomes available
through completed prerequisites, not merely by reaching a particular calendar
year.

The starting team has one engineer, and each opening project reserves that
engineer until completion, so only one can run at a time. Later projects may
require additional engineers. An unlocked project still needs sufficient funds
and unassigned engineers before it can start.

Later engine and component research depends on earlier branch technologies and
specific chassis tiers. For example, Edwardian Giants requires both Pioneer
Engines and Advanced Edwardian Racing Frame. Gearbox research currently has only
one project, Computer-Optimised Gear Ratios, which requires Computer-Optimised
Spaceframe and is therefore unavailable in the opening campaign.

## Running the Prototype

From the project directory, run:

```text
python main.py
```

The application opens the desktop GUI. Use the left navigation to move between
the campaign dashboard, research, garage, test runs, telemetry, team management,
records, and historical challenges. No additional GUI package installation is
required.

## Engineering Reports

Campaign and engineering-facility tests open the **Team Debrief** screen with a
Chief Engineer Report: primary concern, telemetry evidence, and three practical
recommendations. Campaign research advice reflects prerequisites, active
projects, available engineers, and funding. The screen links to the relevant
research branch, Garage, telemetry, and the next test or record attempt.

The debrief compares measured-mile speed with the preceding run only when both
runs completed and used the same vehicle name and venue. It also shows the gap
to the historical campaign target and distinguishes test pace from an official
record attempt. Aborted runs prioritize the named failure and label simulated
speeds as estimates, not valid records. Reports remain available through the
Team Debrief navigation for the current session; sandbox reports do not change
the campaign. Reviewing a report spends no funds and advances no time.

## Historical Records

Each simulation is saved to `historical_records.json`, which persists between
sessions. A record stores the car, engine, gearbox, brakes, track, peak speed,
average acceleration and deceleration, full-throttle time, and measured-mile
average speed. The most recent records are displayed after each run.

## Project Files

- `main.py` launches the desktop GUI.
- `management.py` stores campaign funds and completed-run progression.
- `research.py` defines the engine technology tree and research prerequisites.
- `reliability.py` resolves engine failure risk and trackside repairs.
- `cars.py` contains the selectable prebuilt vehicle definitions.
- `tracks.py` contains selectable track definitions and surface conditions.
- `records.py` saves and displays the persistent historical records table.
- `vehicle.py` defines the `Vehicle` class and its engineering properties.
- `engines.py` contains the available engine definitions.
- `simulation.py` contains the physics loop, drag calculation, validation, and
  telemetry result types.
- `gearbox.py` defines gear ratios, final drive, efficiency, and shift behaviour.
- `brakes.py` defines brake systems, heat buildup, efficiency, and fade.
- `ui/app.py` contains the button-driven desktop application.
- `Docs/vision.md` describes the longer-term direction of the project.

## Available Vehicles

The current catalogue contains:

- `Brick Mk1`: a heavier Lion-powered prototype with a larger frontal area.
- `Blue Bird 1927`: a lighter, more aerodynamic Lion-powered configuration.
- `Jeantaud`: a 1,400 kg Welch Hemi-powered prototype with estimated
  `Cd=0.95` and `1.7 m^2` frontal area.
- `Campbell-Napier-Railton Blue Bird`: a 1931, 3,600 kg car using the Napier
  Lion, with `Cd=0.55`, `2.3 m^2` frontal area, and `0.50 m` wheel radius.
- `Irving-Napier Golden Arrow`: Major Segrave's 1929 streamlined record car,
  using the Rolls-Royce R and Golden Arrow 3-Speed LSR gearbox. Its recorded
  dimensions are 8.43 m long, 1.14 m high, with a 4.07 m wheelbase and 3,661 kg
  mass.
- `Stanley Steamer Rocket`: a 1906 steam-powered record car using a two-cylinder
  150 hp steam engine and direct-drive transmission. It is 4.74 m long and
  0.93 m high, weighs 1,000 kg, and has a 2.49 m wheelbase; remaining prototype
  figures will be refined as historical source data is added.
- `Darracq 1905`: a 1,000 kg car with a 200 hp, 25.422-litre V8, two-speed
  gearbox with a `2.0` final drive, weak mechanical drum brakes, `Cd=0.75`, and
  `1.9 m^2` frontal area. Its prototype gearbox efficiency is set to 85%.

Build custom cars from unlocked chassis, engines, transmissions, and historically
available brakes in the Garage. The builder assigns a vehicle name automatically;
garage vehicles can be tuned, upgraded, and selected for campaign test runs.
Choose the test venue from the available track buttons. Track length,
measured-mile position, altitude, temperature, air density, and surface friction
remain stored on each track; the simulation uses track length, measured-mile
position, friction, and air density.

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

Vehicles can also reference an engine definition. The current catalogue is a
curated set of ten genuinely significant historical (and near-future) land
speed record engines, including a historically inspired 1920s Napier Lion: a
23.9-litre W12 rated here at 900 hp and 1,940 Nm, with a reliability factor
of 0.83. It also includes the 36 hp, four-cylinder Welch Hemi, weighing 120
kg and producing approximately 203 Nm at a 2,500 RPM limit. The Welch Hemi
reliability factor is provisionally set to 0.80. These values are prototype
data intended for gameplay balancing and will need to be refined as the
historical database grows.

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

Project Bonneville has evolved from a land speed record simulator into an engineering and management game about the history of world land speed record attempts. The simulator, campaign, research, reliability, and vehicle design systems now form a solid foundation for future development.

### Completed or Largely Implemented

#### Historical Content

- Historical vehicles, engines, tracks, and record progression
- Persistent campaign records and historical run tracking
- Historically themed technology eras and research progression

#### Research & Development

- Multi-turn engineering projects
- Research prerequisites and unlock chains
- Aerodynamics, chassis, engine, tyre, and brake technology progression
- Technology era structure supporting future expansion

#### Vehicle Engineering

- Vehicle designer allows selection of:
	- Chassis
	- Engine
	- Gearbox
	- Brakes
- Engine tuning system
- Gearbox tuning system
- Modular vehicle architecture supporting future component expansion

#### Campaign Management

- Persistent campaign state
- Team management framework
- Engineers and mechanics
- Funding and operating costs
- Sponsorship foundations
- Progression through time and technology eras

#### Simulation

- Multi-speed gearboxes
- Torque and gearing effects
- Aerodynamic drag
- Rolling resistance
- Tyre grip modelling
- Brake performance and fade
- Reliability and mechanical failures
- Historical record attempts
- Telemetry and graphical outputs

### Current Development Priorities

#### Rival Teams and Historical Competition

Historical rival teams now compete using the dated attempts in the curated
40-record dataset. Jenatzy, Hemery, Segrave, Campbell, Eyston, Cobb, Breedlove,
Arfons, Green, and the other recorded drivers enter the standings as they compete.

Ending a turn progresses engineering projects and replays rival attempts whose
historical dates have been reached, including attempts across skipped years.
Funding research does not itself advance time. Quiet periods in the chronology
remain preparation years; rival speeds are not randomly inflated.

Rivals can take the world record, but cannot displace a faster official player
record. Practice personal bests do not count as official records. The dashboard
shows official team standings and record announcements, and a new rival world
record triggers an end-turn notice. Standings, record ownership, and processed
attempts survive save/load; older anonymous-rival saves migrate automatically.

#### Sponsorship and Stakeholder Pressure

Expand sponsorship into a genuine management system.

Examples:

- Sponsorship contracts
- Record-breaking objectives
- Publicity targets
- Financial objectives
- Reputation effects

Players should balance engineering goals against commercial pressures.

#### Workshop and Team Development

Expand team management.

Potential features:

- Hiring engineers
- Hiring mechanics
- Specialist designers
- Aerodynamicists
- Workshop upgrades
- Wind tunnel access
- Testing facilities

#### Bodywork and Aerodynamics

Expand vehicle design beyond core mechanical components.

Allow independent selection of:

- Nose designs
- Cockpit types
- Wheel fairings
- Bodywork packages
- Streamlining concepts
- Tail configurations

Vehicle appearance should evolve visually with research.

#### 16-Bit Vehicle Presentation

Introduce a retro-inspired visual presentation layer.

Features:

- Side-profile pixel-art vehicles
- Layered sprite system
- Vehicle appearance changes based on research and upgrades
- Visible progression from primitive pioneers to rocket cars
- Dashboard and telemetry inspired by classic management games

#### Improved Event System

Introduce campaign events.

Examples:

- Engine failures
- Sponsorship offers
- Driver injuries
- Funding shortages
- Breakthrough discoveries
- Rival record announcements

The campaign should generate unique stories each playthrough.

### Future Development

#### FIA and Historical Record Rules

Implement authentic record procedures.

Examples:

- Two runs in opposite directions
- One-hour turnaround requirement
- Class-specific records
- Timing authority verification
- International regulations

#### Advanced Simulation

Potential future additions:

- Dynamic tyre temperatures
- Tyre growth at speed
- Crosswinds
- Aerodynamic lift
- Stability modelling
- Weight transfer
- Surface condition effects

#### Telemetry Export

- Export telemetry to CSV
- External analysis support
- Engineering reports
- Run comparison tools

#### Optional External Integration

Potential future integrations:

- BeamNG vehicle validation
- Unity visualisation
- 3D replay generation
- Player-driven record attempts

These would complement, rather than replace, the core management game.

### Long-Term Vision

Project Bonneville ultimately becomes a management and engineering simulation covering the entire history of land speed record competition, from primitive pioneer machines in the 1890s through streamliners, aircraft-engined monsters, jet cars, rocket cars, and future record technologies.

The focus remains on balancing:

- Engineering innovation
- Reliability
- Funding
- Team management
- Historical competition
- Risk

while pursuing the world land speed record across more than a century of technological evolution.