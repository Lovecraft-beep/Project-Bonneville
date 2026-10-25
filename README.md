# Project Bonneville

Project Bonneville is an early prototype for a management and engineering
simulation about the history of world land-speed records.

I see it evolving into a Malcolm Campbell simulator.

The intended game begins with early piston-engine record cars and progresses
through increasingly advanced piston, jet, rocket, and electric vehicles.
Future versions may use BeamNG or Unity to validate vehicle designs and stage
record attempts.

## Current Prototype

Version 0.6 develops the prototype into a strategy-focused campaign. Each
historical era requires one binding major development program, with distinct
research costs, timelines, and reliability tradeoffs. Record holders can make
official attempts to extend their own mark, researched technology can unlock
historically early components, and retired vehicles are preserved in a separate
Museum. The button-driven Tkinter interface includes the campaign dashboard,
research tree, garage and vehicle designer, test-run setup, and telemetry views.

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
reputation, engineers, mechanics, and workshop level. Staff draw wages every
seasonal turn, including idle turns. The starting team (one standard engineer
and two standard mechanics) costs GBP 450 per turn.

| Staff | Recruitment | Wages Per Turn | Effect |
| --- | --- | --- | --- |
| Standard engineer | GBP 8,000 | GBP 250 | One engineer slot for research |
| Specialist engineer | GBP 16,000 | GBP 650 | One slot; matching research finishes one turn sooner |
| Standard mechanic | GBP 5,000 | GBP 100 | Standard reliability and repair contribution |
| Experienced mechanic | GBP 10,000 | GBP 250 | Double mechanic skill contribution and minor-repair coverage |

Specialists are hired for engines, aerodynamics, chassis, gearboxes, tyres, or
brakes. Projects reserve their staff until completion. One matching specialist
shortens a project by one turn, with a minimum duration of one turn; specialists
working outside their branch provide headcount but no speed bonus. Benefits do
not stack by assigning extra specialists to the same project.

One experienced mechanic provides the minor-repair coverage of two standard
mechanics, but an engineer is still required. Major failures still require the
workshop. The usual reliability skill cap remains in effect.

Team and Dashboard show payroll, net seasonal cash flow, and projected next-turn
cash. Recruitment confirmation includes the new wages and post-hire forecast.
Idle staff can be released without a recruitment refund; assigned engineers
cannot be released, and at least one engineer must remain. Staff quality and
project assignments are saved with the career.

End Turn pays sponsor income and deducts the full wage bill. If cash falls below
zero, the deficit remains visible and new spending is restricted by affordability;
turns can still advance while the team reduces staffing or secures funding.

Driver skill starts at 25%. The Team page lets you train once per turn for
GBP 1,000, gaining 15 percentage points up to 100%. Skill improves throttle
modulation and braking control; it is especially valuable before traction
control and anti-lock braking are researched.

### Sponsorship Objectives

Castrol and Dunlop are ongoing technical partnerships rather than run quotas.
Completing a research project or vehicle build earns their milestone reward
automatically on End Turn, without a test run. Their next milestone starts from
the new development total, so previously completed work and repeated tests do
not earn extra payouts. There is no inactivity deadline or withdrawal for taking
time between development projects. Existing saved run-quota contracts are
converted to these development objectives on load.

Speed-focused sponsors retain their timed measured-mile objectives and
withdrawal rules. Missing a deadline withdraws their support for one turn, not
permanently. The Team screen shows a temporary notice; after the next End Turn,
the notice clears and negotiations reopen under the normal reputation rules.
The Team screen and Dashboard distinguish ongoing technical partnerships from
those timed commitments.

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
Each seasonal turn pays sponsor income and staff wages, progresses research and
vehicle construction, updates rival attempts, and resets the test and record
sessions. Seasons provide the calendar foundation for future weather effects;
weather is not yet simulated.

End Turn fast-forwards from dates in 1914-1918 to Spring 1919, and from dates in
1939-1946 to Spring 1947, reflecting the pause in record-breaking activity.
Every elapsed season still counts for payroll, sponsor deadlines, research,
vehicle construction, workshop work, and campaign turn numbering. Historical
rival attempts are processed through the resumed date; no player records or test
runs are invented during the pause.

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

## Vehicle Condition and Incidents

Campaign cars retain wear, damage, and workshop progress between turns and saves.
Both tests and official passes add wear: 0.25 points at very low speed, rising
slowly with peak speed. Forty runs at 100 mph leave a car Worn with less than 1%
loss of power, grip, and braking. Wear also gradually increases failure exposure.
Sandbox cars do not affect career condition.

| Condition | Threshold | Workshop Work | Cost Versus Replacement |
| --- | --- | --- | --- |
| Pristine | Wear below 10, no damage | Optional service for accumulated wear | 8% |
| Worn | Wear 10 or more, no damage | Service | 8% |
| Damaged | Damage above 0 and below 60 | Repair; running remains possible with penalties | 30% |
| Heavily Damaged | Damage 60 to below 100 | Major repair; cannot run | 65% |
| Destroyed | Damage 100 | Rebuild; cannot run | 100% |

Replacement value uses the fitted chassis, stock engine, gearbox, and brakes.
Workshop work is paid up front and requires a mechanic. Service takes a quarter
of the vehicle's complexity-based build time, repairs half, major repairs three
quarters, and rebuilds the full build time, rounded up to at least one turn.
The Garage quotes the price and duration and shows progress. Condition returns
to Pristine only when the job completes; End Turn without a paid job does not
repair damage. Work in progress locks runs and component changes. Servicing does
not count as new development for sponsor milestone rewards.

Incident damage combines failure type and a speed-squared severity factor. A
tyre burst assessed at 100 mph adds about 20 damage; at 400 mph it destroys a
pristine car. The current incident speed estimate is the simulated run's peak
speed, not a separately simulated crash trajectory. Severe brake or steering
incidents can also prevent trackside repairs. Minor trackside fixes do not
remove accumulated wear or accident damage.

An incident leaving a car Heavily Damaged costs 3 reputation; destruction costs
5, with reputation floored at zero. These penalties are not undone by repairs.
Unrepairable incidents cancel active official attempts and end the current test
session. No failed incident is credited as an official record. Damage and the
latest incident assessment are visible in the Garage and team debrief.

## Research Progression

Choose one major development program per era before starting that era's
engineering projects. The choice is permanent for that era:

- **Aerodynamic Pioneer:** Aero projects cost 20% less and finish one season
  sooner; engine projects cost 25% more and take one extra season.
- **Horsepower Gambler:** Engine projects cost 20% less and finish one season
  sooner; aero projects cost 25% more and take one extra season. Run failure risk
  rises by 15%.
- **Engineering Perfectionist:** Chassis, gearbox, tyre, and brake projects cost
  20% less and finish one season sooner. Engine and aero projects cost 25% more
  and take one extra season; run failure risk falls by 25%.

The next era opens a new choice. Unchosen research remains available, but its
projects may take longer and cost more under the selected program.

Only aerodynamics research is otherwise available at the start of a new
campaign. Its base project times are:

| Project | Required completed research | Base turn advances to complete |
| --- | --- | --- |
| Wind Deflector | None | 3 |
| Wheel Fairings / Spats | Wind Deflector | 3 |
| Basic Streamlining | Wheel Fairings / Spats | 3 |
| Carriage Frame | Basic Streamlining | 6 |

Completing Basic Streamlining makes Carriage Frame available to research.
Completing Carriage Frame then unlocks these projects in their respective tabs:

- **Chassis:** Heavy-Duty Racing Ladder
- **Engine:** Pioneer Engines
- **Tyres:** Pneumatic Racing Tyres
- **Brakes:** Mechanical Drum Brakes

Under Aerodynamic Pioneer, the first three aero projects each take two seasonal
turns, so Carriage Frame becomes available after six turn advances. It then takes
six turns, completing in Spring 1898 when started as soon as it unlocks.
Starting a project does not advance time; **End turn** progresses
active projects by one season. Research becomes available through completed
prerequisites, not merely by reaching a particular calendar year.

Chassis development is a chain of three major generations per era rather than
a ladder of small refinements. Each generation is a substantial investment:
Pioneer frames take six to eight seasons and later generations take longer,
with the final era's chassis taking up to sixteen seasons. Completing all three
generations of an era opens the next era's chassis research.

The starting team has one engineer, and each opening project reserves that
engineer until completion, so only one can run at a time. Later projects may
require additional engineers. An unlocked project still needs sufficient funds
and unassigned engineers before it can start.

Later engine and component research depends on earlier branch technologies and
specific chassis tiers. For example, Edwardian Giants requires both Pioneer
Engines and Advanced Edwardian Racing Frame.

### Gearbox development

Only the 2-Speed Transmission (and Direct Drive for turbojet and rocket cars)
is available at the start. Better gearboxes must be researched, and each
carries a maximum engine power rating:

| Transmission | Rating | Research |
| --- | --- | --- |
| 2-Speed | 120 hp | Available at start |
| 3-Speed | 450 hp | 3-Speed Sliding-Mesh Gearbox (Pioneers, needs Heavy-Duty Racing Ladder) |
| 4-Speed | 1,200 hp | 4-Speed Racing Gearbox (Interwar, needs Twin-Rail Streamliner Frame) |
| 5-Speed | 3,000 hp | 5-Speed Close-Ratio Gearbox (Interwar, needs Full-Envelope Streamliner Chassis) |

Case-Hardened Gears (Interwar) and Alloy Steel Gear Sets (Jet Age) each raise
every gearbox's rating by 25%. A piston engine whose power, including any
tune, exceeds the gearbox rating costs gearbox reliability: 0.5 reliability
per 100% overload (5% per 10% over), down to a 5% floor. Lower reliability
raises the chance of a gear failure, which ends the run. Thrust engines do not
drive through the gearbox and are never penalised. The designer, the component
swap list, and the vehicle page all show each gearbox's rating, its load, and
any overload. Computer-Optimised Gear Ratios still requires
Computer-Optimised Spaceframe.

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
record attempt. A successful official attempt reports its credited result and
future development advice rather than prompting another attempt at the mark
just beaten. Aborted runs prioritize the named failure and label simulated
speeds as estimates, not valid records. Reports remain available through the
Team Debrief navigation for the current session; sandbox reports do not change
the campaign. Reviewing a report spends no funds and advances no time.

## Historical Records

Museum entries show each retired car's recorded peak speed, best measured mile,
best completed official average, and world-record achievements with campaign
season, year, and venue. Current/former holder status follows the live campaign
standings, so it changes when a rival or another team car beats the mark. Run
history is isolated by career and car name. Older run entries without official
attempt metadata still contribute peak speeds, but are not guessed to be official
records; unrun cars show that no results have been recorded.

Before a standing record exists, the Dashboard and Test Runs screen offer
**Set inaugural record**. A completed official attempt with a positive
measured-mile speed establishes the first mark, even in 1895; practice runs do
not count. Once established, the team can attempt to extend its own record
without waiting for a rival. Normal vehicle availability and official pass-count
rules still apply.

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
construction is paid in full when ordered, but the car only enters the active
Garage when its build is complete. The confirmation shows its complexity and
build time; the Garage shows construction progress and turns remaining.

Build complexity uses the most advanced fitted chassis, engine technology,
brake introduction era, or aerodynamic technology, rather than the campaign year:

| Component Era | Complexity | Build Time |
| --- | --- | --- |
| Pioneers | 1/5 | 1 turn |
| Interwar | 2/5 | 2 turns |
| Jet Age | 3/5 | 3 turns |
| Professional | 4/5 | 4 turns |
| Modern | 5/5 | 5 turns |

Each **End turn** advances every construction project by one turn. Progress and
the ordered specification are saved with the career; queued names are reserved.
Unfinished cars cannot be tested, entered in record attempts, or serviced.
Finished cars appear in the Garage with a completion notice and can then be
tuned, upgraded, and selected for campaign test runs.

Engine selection in both the vehicle builder and Garage replacement defaults to
a **new stock engine** at tune stage 0. Check **Reuse saved model tune** to apply
the best tune previously developed for that exact engine model. Tunes are never
transferred from the chassis or from another model, and learned model tunes
remain saved after the last installed example is replaced. Reuse applies the
saved tuning setup; it does not remove a physical engine from another car or
change component purchase pricing. Applying a new tune step costs 5%, 10%, or
15% of the stock engine's purchase price for stages 1, 2, and 3 respectively,
rounded to GBP 100 with a GBP 100 minimum. Only one tune step can be applied
across the entire team each seasonal turn; **End turn** resets the limit. The
Garage quotes the charge and reliability penalty before confirmation. Reusing
an already developed model tune does not incur a second tuning charge. Gearbox
ratio adjustment rules are unchanged.

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

For piston, steam, and wheel-driven gas-turbine engines, engine torque is
multiplied by the first-gear and final-drive ratios, then converted to wheel
force using wheel radius. Inexperienced drivers can spin the wheels when they
over-apply power; wheelspin reduces usable force and is recorded in telemetry.
Driver training reduces this loss, while later Traction Control research
modulates power automatically. Turbojets and rockets propel the chassis with
thrust, so tyre grip does not limit their acceleration or top speed and they
do not produce powered-wheel wheelspin.

At higher speed, engine power and aerodynamic drag determine acceleration.
During the deceleration phase, braking, aerodynamic drag, and rolling
resistance reduce speed.

The brake system has its own mechanical efficiency and maximum braking
capability. Actual brake force is limited by available tyre and track grip.
An inexperienced driver can lock the wheels when brake demand exceeds their
modulation threshold; a locked wheel slides with greatly reduced braking force
and risks a major high-speed incident. Driver training improves control, and
later Anti-lock Braking research prevents lock-ups. Brake temperature increases
with braking energy and decreases through cooling; above the fade threshold,
usable brake force is reduced. Aerodynamic braking is calculated separately
from the drag equation and becomes stronger as speed increases.

This is intentionally an early model. It does not yet include wind, gradients,
tyre temperature, stability, weather, or brake chutes.

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
- Binding, era-specific development programs with project and reliability tradeoffs
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
attempts survive current-format save/load. Official record attempts can challenge
a rival mark or extend the team's own record.

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