"""Campaign management state for Project Bonneville."""

import json
import uuid
from math import ceil
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path

from brakes import BRAKE_BY_NAME, available_brakes
from chassis import CHASSIS_BY_ID
from condition import assess_incident_damage, condition_state
from diagnostics import reset_vehicle_log
from engines import AVAILABLE_ENGINES
from campaign_world import (
    RivalState,
    WorldState,
    advance_world,
    create_world_state,
    historical_record_at,
)
from historical_records import (
    HISTORICAL_TARGETS,
    average_record_speed,
    next_historical_target,
    record_ids_achieved_by_speed,
    required_record_runs,
    target_completed,
)
from gearbox import AVAILABLE_GEARBOXES, adjust_gearbox_ratio
from research import (
    AERODYNAMICS_TECHNOLOGY_BY_ID,
    BRAKE_TECHNOLOGY_BY_ID,
    CHASSIS_TECHNOLOGY_BY_ID,
    ENGINE_TECHNOLOGY_BY_ID,
    ERA_ORDER,
    GEARBOX_TECHNOLOGY_BY_ID,
    TECHNOLOGY_NAME_BY_ID,
    TYRE_TECHNOLOGY_BY_ID,
    era_for_year,
)
from sponsors import (
    DEVELOPMENT_OBJECTIVE,
    RUNS_OBJECTIVE,
    SPEED_OBJECTIVE,
    SPONSOR_BY_ID,
    SPONSOR_OBJECTIVE_DEADLINE_TURNS,
)

SPONSOR_OBJECTIVE_REPUTATION_GAIN = 0.5
SPONSOR_DEPARTURE_REPUTATION_LOSS = 1.0

CAMPAIGN_FILE = Path(__file__).with_name("campaign_state.json")
STARTING_FUNDS_GBP = 100_000.0
STARTING_YEAR = 1895
SEASONS = ("Development", "Competition")
SEASON_START_DAYS = (1, 183)
DEFAULT_TEAM_NAME = "Bonneville Racing Team"
ENGINEER_HIRE_COST_GBP = 8_000.0
MECHANIC_HIRE_COST_GBP = 5_000.0
ENGINEER_WAGE_GBP = 500.0
MECHANIC_WAGE_GBP = 200.0
SPECIALIST_HIRE_COST_GBP = 16_000.0
SPECIALIST_WAGE_GBP = 1_300.0
EXPERIENCED_MECHANIC_HIRE_COST_GBP = 10_000.0
EXPERIENCED_MECHANIC_WAGE_GBP = 500.0
WORKSHOP_UPGRADE_BASE_COST_GBP = 10_000.0
TRACKSIDE_ADJUSTMENT_COST_GBP = 5.0
MAX_TESTS_PER_SESSION = 8
MAX_RECORD_RUNS_PER_SESSION = 8
WAR_TIME_PAUSES = ((1914, 1918, 1919), (1939, 1946, 1947))
ENGINE_TUNE_COST_FACTORS = {1: 0.05, 2: 0.10, 3: 0.15}
DEVELOPMENT_PROGRAMS = {
    "aerodynamic_pioneer": {
        "name": "Aerodynamic Pioneer",
        "description": "Aerodynamics projects cost 20% less and finish one season sooner; engine projects cost 25% more and take one extra season.",
        "preferred_branches": ("aerodynamics",),
        "penalized_branches": ("engine",),
        "failure_risk_multiplier": 1.0,
    },
    "power_gambler": {
        "name": "Horsepower Gambler",
        "description": "Engine projects cost 20% less and finish one season sooner; aero projects cost 25% more and take one extra season. Run failure risk rises 15%.",
        "preferred_branches": ("engine",),
        "penalized_branches": ("aerodynamics",),
        "failure_risk_multiplier": 1.15,
    },
    "engineering_perfectionist": {
        "name": "Engineering Perfectionist",
        "description": "Chassis, gearbox, tyre, and brake projects cost 20% less and finish one season sooner. Run failure risk falls 25%; engine and aero projects cost 25% more and take one extra season.",
        "preferred_branches": ("chassis", "gearbox", "tyre", "brake"),
        "penalized_branches": ("engine", "aerodynamics"),
        "failure_risk_multiplier": 0.75,
    },
}
DEVELOPMENT_PROGRAM_COST_FACTORS = {"preferred": 0.8, "penalized": 1.25}


def require_development_season(campaign):
    if campaign.current_season != "Development":
        raise ValueError("this action is available during the Development season")


def require_competition_season(campaign):
    if campaign.current_season != "Competition":
        raise ValueError("campaign testing and record attempts open during the Competition season")


@dataclass
class Team:
    """The management resources controlled by the player."""

    name: str = DEFAULT_TEAM_NAME
    cash: float = STARTING_FUNDS_GBP
    reputation: float = 0.0
    engineers: int = 1
    mechanics: int = 2
    workshop_level: int = 1
    engineer_specialties: list[str] = field(default_factory=list)
    experienced_mechanics: int = 0

    @property
    def payroll_per_turn_gbp(self):
        return (
            (self.engineers - len(self.engineer_specialties)) * ENGINEER_WAGE_GBP
            + len(self.engineer_specialties) * SPECIALIST_WAGE_GBP
            + (self.mechanics - self.experienced_mechanics) * MECHANIC_WAGE_GBP
            + self.experienced_mechanics * EXPERIENCED_MECHANIC_WAGE_GBP
        )


@dataclass
class ResearchState:
    """Technologies researched by the team."""

    engine_technology: list[str] = field(default_factory=list)
    chassis_technology: list[str] = field(default_factory=list)
    aerodynamics_technology: list[str] = field(default_factory=list)
    tyre_technology: list[str] = field(default_factory=list)
    brake_technology: list[str] = field(default_factory=list)
    gearbox_technology: list[str] = field(default_factory=list)

    @property
    def engine_technology_level(self):
        return len(self.engine_technology)

    def has_engine_technology(self, technology_id):
        return technology_id in self.engine_technology

    def _complete_engine_technology(self, technology_id):
        if technology_id not in ENGINE_TECHNOLOGY_BY_ID:
            raise ValueError(f"unknown engine technology: {technology_id}")
        if technology_id not in self.engine_technology:
            self.engine_technology.append(technology_id)

    @property
    def chassis_technology_level(self):
        return len(self.chassis_technology)

    def has_chassis_technology(self, technology_id):
        return technology_id in self.chassis_technology

    def _complete_chassis_technology(self, technology_id):
        if technology_id not in CHASSIS_TECHNOLOGY_BY_ID:
            raise ValueError(f"unknown chassis technology: {technology_id}")
        if technology_id not in self.chassis_technology:
            self.chassis_technology.append(technology_id)

    def has_aerodynamics_technology(self, technology_id):
        return technology_id in self.aerodynamics_technology

    def _complete_aerodynamics_technology(self, technology_id):
        if technology_id not in AERODYNAMICS_TECHNOLOGY_BY_ID:
            raise ValueError(f"unknown aerodynamics technology: {technology_id}")
        if technology_id not in self.aerodynamics_technology:
            self.aerodynamics_technology.append(technology_id)

    def has_tyre_technology(self, technology_id):
        return technology_id in self.tyre_technology

    def _complete_tyre_technology(self, technology_id):
        if technology_id not in TYRE_TECHNOLOGY_BY_ID:
            raise ValueError(f"unknown tyre technology: {technology_id}")
        if technology_id not in self.tyre_technology:
            self.tyre_technology.append(technology_id)

    def has_brake_technology(self, technology_id):
        return technology_id in self.brake_technology

    def _complete_brake_technology(self, technology_id):
        if technology_id not in BRAKE_TECHNOLOGY_BY_ID:
            raise ValueError(f"unknown brake technology: {technology_id}")
        if technology_id not in self.brake_technology:
            self.brake_technology.append(technology_id)

    def has_gearbox_technology(self, technology_id):
        return technology_id in self.gearbox_technology

    def _complete_gearbox_technology(self, technology_id):
        if technology_id not in GEARBOX_TECHNOLOGY_BY_ID:
            raise ValueError(f"unknown gearbox technology: {technology_id}")
        if technology_id not in self.gearbox_technology:
            self.gearbox_technology.append(technology_id)


@dataclass
class SponsorObjective:
    """The current demand a sponsor has set, with turns left to meet it."""

    sponsor_id: str
    kind: str
    target: float
    reward_gbp: float
    turns_remaining: int | None = SPONSOR_OBJECTIVE_DEADLINE_TURNS
    runs_at_issue: int = 0
    development_at_issue: int = 0


@dataclass
class SponsorshipState:
    """Sponsors signed by the team."""

    active_sponsors: list[str] = field(default_factory=list)
    objectives: list[SponsorObjective] = field(default_factory=list)
    departed_sponsors: list[str] = field(default_factory=list)
    recent_departures: list[str] = field(default_factory=list)

    def objective_for(self, sponsor_id):
        return next(
            (item for item in self.objectives if item.sponsor_id == sponsor_id),
            None,
        )

    def has_sponsor(self, sponsor_id):
        return sponsor_id in self.active_sponsors

    def add_sponsor(self, sponsor_id):
        if sponsor_id not in SPONSOR_BY_ID:
            raise ValueError(f"unknown sponsor: {sponsor_id}")
        if sponsor_id not in self.active_sponsors:
            self.active_sponsors.append(sponsor_id)

    @property
    def reliability_bonus(self):
        return sum(
            SPONSOR_BY_ID[sponsor_id].reliability_bonus
            for sponsor_id in self.active_sponsors
        )

    @property
    def income_per_turn_gbp(self):
        return sum(
            SPONSOR_BY_ID[sponsor_id].income_per_turn_gbp
            for sponsor_id in self.active_sponsors
        )


@dataclass
class GarageVehicle:
    """A custom vehicle designed and built by the team."""

    vehicle_name: str
    chassis_id: str
    engine_name: str
    gearbox_name: str
    brakes_name: str
    aerodynamics_technology: tuple[str, ...] = ()
    gearbox_ratios: tuple[float, ...] = ()
    gearbox_final_drive: float | None = None
    engine_tune_stage: int = 0
    tyre_grip_factor: float | None = None
    wear: float = 0.0
    damage: float = 0.0
    last_incident: str = ""
    workshop_action: str = ""
    workshop_turns_total: int = 0
    workshop_turns_remaining: int = 0

    @property
    def condition(self):
        return condition_state(self.wear, self.damage)


def apply_vehicle_run_condition(campaign, entry, peak_speed_mph, outcome):
    entry.wear = round(min(100.0, entry.wear + 0.25 * (1.0 + max(0.0, peak_speed_mph) / 400.0)), 3)
    if not outcome.failed:
        return f"Condition: {entry.condition} / wear {entry.wear:.1f}% / damage {entry.damage:.1f}%"
    incident = assess_incident_damage(outcome.failure_type, peak_speed_mph)
    entry.damage = round(min(100.0, entry.damage + incident.damage), 2)
    reputation_loss = 5.0 if entry.condition == "Destroyed" else 3.0 if entry.condition == "Heavily Damaged" else 0.0
    campaign.team.reputation = round(max(0.0, campaign.team.reputation - reputation_loss), 2)
    entry.last_incident = f"{incident.description}. Condition: {entry.condition}."
    if reputation_loss:
        entry.last_incident += f" Reputation -{reputation_loss:.0f}."
    return entry.last_incident


@dataclass
class Garage:
    """Custom vehicles in service and preserved in the team museum."""

    vehicles: list[GarageVehicle] = field(default_factory=list)
    museum: list[GarageVehicle] = field(default_factory=list)


@dataclass
class VehicleConstruction:
    vehicle: GarageVehicle
    complexity: int
    turns_total: int
    turns_remaining: int


@dataclass
class CampaignRecordAttempt:
    target_id: str
    vehicle_name: str
    track_name: str
    started_year: int
    required_runs: int
    speeds_mph: list[float] = field(default_factory=list)
    target_year: int | None = None
    target_vehicle: str = ""
    target_speed_mph: float | None = None


TEAM_RECORD_TARGET_ID = "team_record"
INAUGURAL_RECORD_TARGET_ID = "inaugural_record"


@dataclass(frozen=True)
class CampaignRecordTarget:
    record_id: str
    year: int
    vehicle: str
    speed_mph: float
    milestone: str


@dataclass
class EngineeringProject:
    """Research work in progress, with its staff allocated until completion."""

    branch: str
    technology_id: str
    turns_total: int
    turns_remaining: int
    engineers_required: int
    specialists: list[str] = field(default_factory=list)


@dataclass
class CampaignState:
    team: Team = field(default_factory=Team)
    research: ResearchState = field(default_factory=ResearchState)
    engineering_projects: list[EngineeringProject] = field(default_factory=list)
    sponsorship: SponsorshipState = field(default_factory=SponsorshipState)
    garage: Garage = field(default_factory=Garage)
    vehicle_construction: list[VehicleConstruction] = field(default_factory=list)
    record_attempt: CampaignRecordAttempt | None = None
    campaign_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    current_year: int = STARTING_YEAR
    current_day_of_year: int = 1
    development_programs: dict[str, str] = field(default_factory=dict)
    engine_tune_stages: dict[str, int] = field(default_factory=dict)
    engine_tunes_this_turn: int = 0
    turn_number: int = 1
    tests_this_session: int = 0
    record_runs_this_session: int = 0
    workshop_repair_pending: bool = False
    venues_paid_this_session: list[str] = field(default_factory=list)
    completed_runs: int = 0
    completed_development_milestones: int = 0
    failed_runs: int = 0
    best_measured_mile_speed_mph: float = 0.0
    official_record_mph: float = 0.0
    official_record_vehicle_name: str = ""
    completed_historical_record_ids: list[str] = field(default_factory=list)
    world: WorldState = field(default_factory=create_world_state)

    @property
    def current_season(self):
        return SEASONS[self.season_index]

    @property
    def current_era(self):
        return era_for_year(self.current_year).name

    @property
    def season_index(self):
        return sum(self.current_day_of_year >= day for day in SEASON_START_DAYS) - 1

    @property
    def allocated_engineers(self):
        return sum(project.engineers_required for project in self.engineering_projects)

    @property
    def available_engineers(self):
        return max(0, self.team.engineers - self.allocated_engineers)

    @property
    def cash_flow_per_turn_gbp(self):
        return self.sponsorship.income_per_turn_gbp - self.team.payroll_per_turn_gbp

    @property
    def projected_next_turn_cash_gbp(self):
        return round(self.team.cash + self.cash_flow_per_turn_gbp, 2)


def calculate_run_cost(track):
    """Return the venue cost for one run."""
    return track.event_cost_gbp


def calculate_session_run_cost(campaign, track):
    """Charge a venue fee only the first time a venue is used this session."""
    if track.name in campaign.venues_paid_this_session:
        return 0
    return calculate_run_cost(track)


def mark_session_venue_paid(campaign, track):
    """Record that the current test session has paid to use this venue."""
    if track.name not in campaign.venues_paid_this_session:
        campaign.venues_paid_this_session.append(track.name)


def next_vehicle_name(campaign):
    """Suggest a name, numbering later vehicles from the first vehicle's name."""
    owned_vehicles = (
        campaign.garage.vehicles
        + campaign.garage.museum
        + [project.vehicle for project in campaign.vehicle_construction]
    )
    if not owned_vehicles:
        return "Bonneville Special 01"

    first_name = owned_vehicles[0].vehicle_name.strip()
    base_name, separator, suffix = first_name.rpartition(" ")
    if separator and suffix.isdigit():
        first_number = int(suffix)
    else:
        base_name = first_name
        first_number = 1
    base_name = base_name.strip() or "Bonneville Special"

    existing_names = {vehicle.vehicle_name.casefold() for vehicle in owned_vehicles}
    next_number = first_number + len(owned_vehicles)
    candidate = f"{base_name} {next_number}"
    while candidate.casefold() in existing_names:
        next_number += 1
        candidate = f"{base_name} {next_number}"
    return candidate


def load_campaign(path=CAMPAIGN_FILE):
    """Load campaign state, creating a fresh campaign when none exists."""
    if not path.exists():
        return CampaignState()

    with path.open("r", encoding="utf-8") as campaign_file:
        data = json.load(campaign_file)

    data["team"] = Team(**data["team"])
    data["research"] = ResearchState(**data["research"])
    data["engineering_projects"] = [
        EngineeringProject(**project)
        for project in data["engineering_projects"]
    ]
    sponsorship_data = data["sponsorship"]
    sponsorship_data["objectives"] = [
        SponsorObjective(**objective)
        for objective in sponsorship_data["objectives"]
    ]
    data["sponsorship"] = SponsorshipState(**sponsorship_data)
    garage_data = data["garage"]
    data["garage"] = Garage(
        vehicles=[GarageVehicle(**vehicle) for vehicle in garage_data["vehicles"]],
        museum=[GarageVehicle(**vehicle) for vehicle in garage_data["museum"]],
    )
    data["vehicle_construction"] = [
        VehicleConstruction(**{
            **project,
            "vehicle": GarageVehicle(**{
                **project["vehicle"],
                "aerodynamics_technology": tuple(project["vehicle"]["aerodynamics_technology"]),
                "gearbox_ratios": tuple(project["vehicle"]["gearbox_ratios"]),
            }),
        })
        for project in data.get("vehicle_construction", [])
    ]
    record_attempt_data = data["record_attempt"]
    data["record_attempt"] = (
        CampaignRecordAttempt(**record_attempt_data)
        if record_attempt_data is not None
        else None
    )
    world_data = data["world"]
    world_data["rivals"] = [RivalState(**rival) for rival in world_data["rivals"]]
    data["world"] = WorldState(**world_data)
    campaign = CampaignState(**data)
    for objective in list(campaign.sponsorship.objectives):
        if objective.kind == RUNS_OBJECTIVE:
            issue_sponsor_objective(campaign, objective.sponsor_id)
    return campaign


def save_campaign(campaign, path=CAMPAIGN_FILE):
    """Persist campaign state as readable JSON."""
    with path.open("w", encoding="utf-8") as campaign_file:
        json.dump(asdict(campaign), campaign_file, indent=2)
        campaign_file.write("\n")


def complete_run(
    campaign,
    run_cost_gbp,
    measured_mile_speed_mph,
    is_record_attempt=False,
    record_attempt_average_mph=None,
    vehicle_name=None,
):
    """Charge a completed run and update campaign performance."""
    if run_cost_gbp > campaign.team.cash:
        raise ValueError("campaign does not have enough funds for this run")

    campaign.team.cash = round(campaign.team.cash - run_cost_gbp, 2)
    campaign.completed_runs += 1
    is_new_record = measured_mile_speed_mph > campaign.best_measured_mile_speed_mph
    campaign.best_measured_mile_speed_mph = max(
        campaign.best_measured_mile_speed_mph,
        measured_mile_speed_mph,
    )
    reputation_gain = 2.0 if is_new_record else 1.0
    newly_completed_record_ids = []
    if is_record_attempt:
        previous_record = standing_world_record(campaign)
        record_speed_mph = (
            measured_mile_speed_mph
            if record_attempt_average_mph is None
            else record_attempt_average_mph
        )
        if record_speed_mph > campaign.official_record_mph:
            campaign.official_record_vehicle_name = vehicle_name or ""
        campaign.official_record_mph = max(
            campaign.official_record_mph, record_speed_mph
        )
        if record_speed_mph > 0 and (previous_record is None or record_speed_mph > previous_record[0]):
            record_headline = (
                f"WORLD RECORD: {campaign.team.name} extends its record to "
                f"{record_speed_mph:.2f} mph."
                if previous_record and previous_record[1] == campaign.team.name
                else f"WORLD RECORD: {campaign.team.name} takes the record at "
                f"{record_speed_mph:.2f} mph."
            )
            campaign.world.headlines.append(
                record_headline
            )
            del campaign.world.headlines[:-8]
        target = next_historical_target(
            campaign.current_year,
            campaign.completed_historical_record_ids,
            campaign.current_day_of_year,
        )
        if target and target_completed(target, record_speed_mph):
            completed_ids = set(campaign.completed_historical_record_ids)
            newly_completed_record_ids = [
                record_id
                for record_id in record_ids_achieved_by_speed(
                    record_speed_mph
                )
                if record_id not in completed_ids
            ]
            campaign.completed_historical_record_ids.extend(
                newly_completed_record_ids
            )
            reputation_gain += len(newly_completed_record_ids)
            campaign.world.headlines.append(
                f"RECORD BEATEN: {campaign.team.name} exceeds the {target.year} "
                f"{target.vehicle} mark at {record_speed_mph:.1f} mph."
            )
            del campaign.world.headlines[:-8]
    campaign.team.reputation = round(
        campaign.team.reputation + reputation_gain, 2
    )
    return check_sponsor_objectives(campaign, measured_mile_speed_mph)


def standing_world_record(campaign):
    """Return (speed_mph, holder, year) for the record as it stands in this campaign."""
    historical = historical_record_at(campaign)
    credited = [
        target.speed_mph
        for target in HISTORICAL_TARGETS
        if target.record_id in campaign.completed_historical_record_ids
    ]
    # Older saves only know which historical marks were beaten, not the exact speed.
    team_speed = max([campaign.official_record_mph, *credited])
    rival_speed = campaign.world.record_speed_mph
    baseline_speed = historical.speed_mph if historical else 0.0
    if team_speed > 0 and team_speed >= max(rival_speed, baseline_speed):
        return team_speed, campaign.team.name, campaign.current_year
    if rival_speed > 0 and rival_speed >= baseline_speed:
        return rival_speed, campaign.world.record_holder, campaign.world.record_year
    if historical is None:
        return None
    return historical.speed_mph, f"{historical.driver} Team", historical.year


def record_chase_target(campaign):
    """Return an inaugural, rival, or team record target for official attempts."""
    record = standing_world_record(campaign)
    if record is None:
        return CampaignRecordTarget(
            record_id=INAUGURAL_RECORD_TARGET_ID,
            year=campaign.current_year,
            vehicle="Inaugural land-speed record",
            speed_mph=0.0,
            milestone="Set the first official record with a positive measured-mile speed.",
        )
    if record[1] == campaign.team.name:
        return CampaignRecordTarget(
            record_id=TEAM_RECORD_TARGET_ID,
            year=record[2],
            vehicle=f"{campaign.team.name} official record",
            speed_mph=record[0],
            milestone=f"Improve the team's official mark beyond {record[0]:.1f} mph.",
        )
    return next(
        (
            target
            for target in HISTORICAL_TARGETS
            if target.year == record[2] and target.speed_mph == record[0]
        ),
        None,
    )


def record_attempt_target(campaign, attempt):
    """Resolve a saved attempt's original target, including a team record."""
    historical_target = next(
        (target for target in HISTORICAL_TARGETS if target.record_id == attempt.target_id),
        None,
    )
    if historical_target is not None:
        return historical_target
    if attempt.target_id == INAUGURAL_RECORD_TARGET_ID:
        return CampaignRecordTarget(
            record_id=INAUGURAL_RECORD_TARGET_ID,
            year=attempt.target_year or attempt.started_year,
            vehicle="Inaugural land-speed record",
            speed_mph=0.0,
            milestone="Set the first official record with a positive measured-mile speed.",
        )
    if attempt.target_id != TEAM_RECORD_TARGET_ID:
        return None
    target_speed = attempt.target_speed_mph
    if target_speed is None:
        current_target = record_chase_target(campaign)
        return (
            current_target
            if current_target and current_target.record_id == TEAM_RECORD_TARGET_ID
            else None
        )
    target_year = attempt.target_year or attempt.started_year
    target_vehicle = attempt.target_vehicle or f"{campaign.team.name} official record"
    return CampaignRecordTarget(
        record_id=TEAM_RECORD_TARGET_ID,
        year=target_year,
        vehicle=target_vehicle,
        speed_mph=target_speed,
        milestone=f"Improve the team's official mark beyond {target_speed:.1f} mph.",
    )


def issue_sponsor_objective(campaign, sponsor_id):
    """Set a sponsor's next demand; speed targets track the standing world record."""
    sponsor = SPONSOR_BY_ID[sponsor_id]
    if sponsor.objective_kind == SPEED_OBJECTIVE:
        record = standing_world_record(campaign)
        speed = record[0] if record else HISTORICAL_TARGETS[0].speed_mph
        target = round(speed * sponsor.objective_value, 1)
    else:
        target = int(sponsor.objective_value)
    objective = SponsorObjective(
        sponsor_id=sponsor_id,
        kind=sponsor.objective_kind,
        target=target,
        reward_gbp=sponsor.objective_reward_gbp,
        runs_at_issue=campaign.completed_runs,
        development_at_issue=campaign.completed_development_milestones,
        turns_remaining=None if sponsor.objective_kind == DEVELOPMENT_OBJECTIVE else SPONSOR_OBJECTIVE_DEADLINE_TURNS,
    )
    campaign.sponsorship.objectives = [
        item
        for item in campaign.sponsorship.objectives
        if item.sponsor_id != sponsor_id
    ] + [objective]
    return objective


def sponsor_objective_progress(campaign, objective):
    """Return (current, target) progress for display."""
    if objective.kind == DEVELOPMENT_OBJECTIVE:
        return campaign.completed_development_milestones - objective.development_at_issue, objective.target
    return campaign.best_measured_mile_speed_mph, objective.target


def describe_sponsor_objective(campaign, objective):
    current, target = sponsor_objective_progress(campaign, objective)
    if objective.kind == DEVELOPMENT_OBJECTIVE:
        demand = f"Complete {target:.0f} research or vehicle build milestone ({min(current, target):.0f}/{target:.0f})"
    else:
        demand = f"Reach {target:.1f} mph on a measured mile"
    turns = objective.turns_remaining
    if turns is None:
        return f"{demand}  /  reward GBP {objective.reward_gbp:,.0f}  /  ongoing partnership, no deadline"
    return (
        f"{demand}  /  reward GBP {objective.reward_gbp:,.0f}  /  "
        f"{turns} turn{'s' if turns != 1 else ''} left"
    )


def check_sponsor_objectives(campaign, measured_mile_speed_mph=None):
    """Reward speed achievements or completed development, then renew objectives."""
    messages = []
    for objective in list(campaign.sponsorship.objectives):
        if objective.kind == DEVELOPMENT_OBJECTIVE:
            met = campaign.completed_development_milestones - objective.development_at_issue >= objective.target
        else:
            met = measured_mile_speed_mph is not None and measured_mile_speed_mph >= objective.target
        if not met:
            continue
        sponsor = SPONSOR_BY_ID[objective.sponsor_id]
        campaign.team.cash = round(campaign.team.cash + objective.reward_gbp, 2)
        campaign.team.reputation = round(
            campaign.team.reputation + SPONSOR_OBJECTIVE_REPUTATION_GAIN, 2
        )
        issue_sponsor_objective(campaign, objective.sponsor_id)
        messages.append(
            f"{sponsor.name} objective met: GBP {objective.reward_gbp:,.0f} paid."
        )
    return messages


def _expire_sponsor_objectives(campaign):
    sponsorship = campaign.sponsorship
    sponsorship.recent_departures = []
    sponsorship.departed_sponsors = []
    for objective in list(sponsorship.objectives):
        if objective.turns_remaining is None:
            continue
        objective.turns_remaining -= 1
        if objective.turns_remaining > 0:
            continue
        sponsor = SPONSOR_BY_ID[objective.sponsor_id]
        sponsorship.objectives.remove(objective)
        if objective.sponsor_id in sponsorship.active_sponsors:
            sponsorship.active_sponsors.remove(objective.sponsor_id)
        if objective.sponsor_id not in sponsorship.departed_sponsors:
            sponsorship.departed_sponsors.append(objective.sponsor_id)
        sponsorship.recent_departures.append(sponsor.name)
        campaign.team.reputation = round(
            max(0.0, campaign.team.reputation - SPONSOR_DEPARTURE_REPUTATION_LOSS), 2
        )
        campaign.world.headlines.append(
            f"{sponsor.name} withdraws its backing after {campaign.team.name} missed its target."
        )
        del campaign.world.headlines[:-8]


def complete_failed_run(campaign, run_cost_gbp):
    """Charge a run that failed and could not be repaired trackside."""
    if run_cost_gbp > campaign.team.cash:
        raise ValueError("campaign does not have enough funds for this run")

    campaign.team.cash = round(campaign.team.cash - run_cost_gbp, 2)
    campaign.failed_runs += 1


def advance_turn(campaign, days=None):
    """Advance a season, fast-forwarding over wartime pauses in record activity."""
    automatic_season_advance = days is None
    previous_year = campaign.current_year
    previous_season_index = campaign.season_index
    if days is None:
        next_season_day = (
            SEASON_START_DAYS[campaign.season_index + 1]
            if campaign.season_index < len(SEASONS) - 1
            else 366
        )
        days = next_season_day - campaign.current_day_of_year
    elapsed_days = campaign.current_day_of_year - 1 + days
    target_year = campaign.current_year + elapsed_days // 365
    target_day = elapsed_days % 365 + 1
    wartime_pause = None
    if automatic_season_advance:
        for war_start, war_end, resume_year in WAR_TIME_PAUSES:
            if war_start <= target_year <= war_end:
                wartime_pause = (war_start, war_end, resume_year)
                target_year = resume_year
                target_day = 1
                break
    campaign.current_year = target_year
    campaign.current_day_of_year = target_day
    elapsed_seasons = max(
        1,
        (campaign.current_year - previous_year) * len(SEASONS)
        + campaign.season_index - previous_season_index,
    )
    advance_world(campaign)
    completed_projects = []
    completed_vehicles = []
    completed_workshop_jobs = []
    sponsor_messages = []
    departed_during_skip = set()
    for _ in range(elapsed_seasons):
        campaign.team.cash = campaign.projected_next_turn_cash_gbp
        campaign.turn_number += 1
        campaign.tests_this_session = 0
        campaign.record_runs_this_session = 0
        campaign.engine_tunes_this_turn = 0
        campaign.workshop_repair_pending = False
        campaign.venues_paid_this_session = []

        turn_completions = []
        turn_vehicles = []
        for project in campaign.engineering_projects:
            project.turns_remaining -= 1
            if project.turns_remaining <= 0:
                _complete_engineering_project(campaign, project)
                turn_completions.append(project.technology_id)
        completed_projects.extend(turn_completions)
        if turn_completions:
            campaign.engineering_projects = [
                project for project in campaign.engineering_projects
                if project.technology_id not in turn_completions
            ]

        for construction in campaign.vehicle_construction:
            construction.turns_remaining -= 1
            if construction.turns_remaining <= 0:
                campaign.garage.vehicles.append(construction.vehicle)
                turn_vehicles.append(construction.vehicle.vehicle_name)
        completed_vehicles.extend(turn_vehicles)
        campaign.vehicle_construction = [
            construction for construction in campaign.vehicle_construction
            if construction.turns_remaining > 0
        ]

        for entry in campaign.garage.vehicles:
            if entry.workshop_turns_remaining <= 0:
                continue
            entry.workshop_turns_remaining -= 1
            if entry.workshop_turns_remaining == 0:
                completed_workshop_jobs.append((entry.vehicle_name, entry.workshop_action))
                entry.wear = 0.0
                entry.damage = 0.0
                entry.workshop_action = ""
                entry.workshop_turns_total = 0

        milestones = len(turn_completions) + len(turn_vehicles)
        campaign.completed_development_milestones += milestones
        sponsor_messages.extend(check_sponsor_objectives(campaign))
        _expire_sponsor_objectives(campaign)
        departed_during_skip.update(campaign.sponsorship.recent_departures)

    if wartime_pause:
        campaign.world.headlines.append(
            f"WARTIME STAND-DOWN: campaign advanced {previous_year}-{wartime_pause[1]}; "
            f"record activity resumes in {wartime_pause[2]}."
        )
    if campaign.team.cash < 0:
        campaign.world.headlines.append(
            f"PAYROLL WARNING: cash deficit GBP {-campaign.team.cash:,.0f}. "
            "Reduce staffing or secure sponsor funding."
        )
    for vehicle_name in completed_vehicles:
        campaign.world.headlines.append(
            f"CONSTRUCTION COMPLETE: {vehicle_name} is ready in the Garage."
        )
    for technology_id in completed_projects:
        campaign.world.headlines.append(
            f"RESEARCH COMPLETE: {TECHNOLOGY_NAME_BY_ID[technology_id]} is now available to the team."
        )
    for vehicle_name, action in completed_workshop_jobs:
        campaign.world.headlines.append(
            f"WORKSHOP COMPLETE: {vehicle_name} {action.lower()} finished; condition Pristine."
        )
    for name in sorted(departed_during_skip):
        if name not in campaign.sponsorship.recent_departures:
            campaign.sponsorship.recent_departures.append(name)
    for message in sponsor_messages:
        campaign.world.headlines.append(message)
    del campaign.world.headlines[:-8]
    return tuple(completed_projects)


def register_test_run(campaign):
    """Record one hourly campaign test, enforcing the session limit."""
    require_competition_season(campaign)
    if campaign.tests_this_session >= MAX_TESTS_PER_SESSION:
        raise ValueError("test session is full; end the turn to start another")
    campaign.tests_this_session += 1
    return campaign.tests_this_session


def register_record_run(campaign):
    """Record one official record pass against this turn's record session."""
    require_competition_season(campaign)
    if campaign.record_runs_this_session >= MAX_RECORD_RUNS_PER_SESSION:
        raise ValueError("record session is full; end the turn to start another")
    campaign.record_runs_this_session += 1
    return campaign.record_runs_this_session


def session_runs_remaining(campaign, record=False):
    """Return the runs left this turn in the test or record session."""
    if record:
        return MAX_RECORD_RUNS_PER_SESSION - campaign.record_runs_this_session
    return MAX_TESTS_PER_SESSION - campaign.tests_this_session


def lapse_record_attempt_if_out_of_runs(campaign):
    """Cancel an attempt whose remaining passes no longer fit the record session."""
    attempt = campaign.record_attempt
    if attempt is None:
        return False
    passes_needed = attempt.required_runs - len(attempt.speeds_mph)
    if session_runs_remaining(campaign, record=True) >= passes_needed:
        return False
    campaign.record_attempt = None
    return True


_ENGINEERING_PROJECT_BRANCHES = {
    "engine": (
        ENGINE_TECHNOLOGY_BY_ID,
        "engine_technology",
        "_complete_engine_technology",
        ("engine_technology", "chassis_technology", "aerodynamics_technology"),
    ),
    "chassis": (
        CHASSIS_TECHNOLOGY_BY_ID,
        "chassis_technology",
        "_complete_chassis_technology",
        ("chassis_technology", "aerodynamics_technology"),
    ),
    "aerodynamics": (
        AERODYNAMICS_TECHNOLOGY_BY_ID,
        "aerodynamics_technology",
        "_complete_aerodynamics_technology",
        ("aerodynamics_technology", "chassis_technology"),
    ),
    "tyre": (
        TYRE_TECHNOLOGY_BY_ID,
        "tyre_technology",
        "_complete_tyre_technology",
        ("tyre_technology", "chassis_technology"),
    ),
    "brake": (
        BRAKE_TECHNOLOGY_BY_ID,
        "brake_technology",
        "_complete_brake_technology",
        ("brake_technology", "chassis_technology"),
    ),
    "gearbox": (
        GEARBOX_TECHNOLOGY_BY_ID,
        "gearbox_technology",
        "_complete_gearbox_technology",
        ("gearbox_technology", "chassis_technology"),
    ),
}


def available_engineer_specialties(campaign):
    available = list(campaign.team.engineer_specialties)
    for project in campaign.engineering_projects:
        for specialty in project.specialists:
            available.remove(specialty)
    return available


def _project_specialists(campaign, branch, engineers_required):
    available = available_engineer_specialties(campaign)
    assigned = []
    if branch in available:
        assigned.append(branch)
        available.remove(branch)
    ordinary_allocated = sum(
        project.engineers_required - len(project.specialists)
        for project in campaign.engineering_projects
    )
    ordinary_available = (
        campaign.team.engineers - len(campaign.team.engineer_specialties)
        - ordinary_allocated
    )
    other_specialists_needed = max(
        0, engineers_required - len(assigned) - ordinary_available
    )
    return assigned + available[:other_specialists_needed]


def start_engineering_project(campaign, branch, technology_id):
    """Fund a technology project and reserve its required engineering staff."""
    require_development_season(campaign)
    branch = branch.lower()
    branch_data = _ENGINEERING_PROJECT_BRANCHES.get(branch)
    if branch_data is None:
        raise ValueError(f"unknown engineering branch: {branch}")

    technology_by_id, researched_attribute, _, prerequisite_attributes = branch_data
    technology = technology_by_id.get(technology_id)
    if technology is None:
        raise ValueError(f"unknown technology: {technology_id}")

    researched = getattr(campaign.research, researched_attribute)
    if technology_id in researched:
        raise ValueError(f"{technology.name} has already been researched")
    if any(
        project.branch == branch and project.technology_id == technology_id
        for project in campaign.engineering_projects
    ):
        raise ValueError(f"{technology.name} is already in progress")

    available_prerequisites = set()
    for attribute in prerequisite_attributes:
        available_prerequisites.update(getattr(campaign.research, attribute))
    if not set(technology.prerequisites).issubset(available_prerequisites):
        raise ValueError(f"prerequisites not met for {technology.name}")
    if (
        technology.era == campaign.current_era
        and technology.era not in campaign.development_programs
    ):
        raise ValueError(
            f"choose a major development program for {technology.era} first"
        )

    project_cost, turns_required = engineering_project_terms(
        campaign, branch, technology
    )
    if campaign.team.cash < project_cost:
        raise ValueError("insufficient funds for this engineering project")
    if campaign.available_engineers < technology.engineers_required:
        raise ValueError("not enough unassigned engineers for this project")

    project = EngineeringProject(
        branch=branch,
        technology_id=technology_id,
        turns_total=turns_required,
        turns_remaining=turns_required,
        engineers_required=technology.engineers_required,
        specialists=_project_specialists(campaign, branch, technology.engineers_required),
    )
    campaign.team.cash = round(campaign.team.cash - project_cost, 2)
    campaign.engineering_projects.append(project)
    return project


def engineering_project_terms(campaign, branch, technology):
    """Return the quoted cost and duration under the selected era program."""
    program = DEVELOPMENT_PROGRAMS.get(
        campaign.development_programs.get(technology.era)
    )
    cost_factor = 1.0
    turn_adjustment = 0
    if program:
        if branch in program["preferred_branches"]:
            cost_factor = DEVELOPMENT_PROGRAM_COST_FACTORS["preferred"]
            turn_adjustment = -1
        elif branch in program["penalized_branches"]:
            cost_factor = DEVELOPMENT_PROGRAM_COST_FACTORS["penalized"]
            turn_adjustment = 1
    project_cost = round(technology.cost_gbp * cost_factor, 2)
    turns_required = max(1, technology.turns_required + turn_adjustment)
    if branch in available_engineer_specialties(campaign):
        turns_required = max(1, turns_required - 1)
    return project_cost, turns_required


def select_development_program(campaign, program_id):
    """Commit the team to one major program for the current historical era."""
    require_development_season(campaign)
    if program_id not in DEVELOPMENT_PROGRAMS:
        raise ValueError(f"unknown development program: {program_id}")
    era = campaign.current_era
    if era in campaign.development_programs:
        raise ValueError(f"a development program is already committed for {era}")
    campaign.development_programs[era] = program_id
    campaign.world.headlines.append(
        f"DEVELOPMENT PROGRAM: {DEVELOPMENT_PROGRAMS[program_id]['name']} selected for {era}."
    )
    del campaign.world.headlines[:-8]
    return program_id


def development_failure_risk_multiplier(campaign):
    """Return the active era program's run-failure risk multiplier."""
    program = DEVELOPMENT_PROGRAMS.get(
        campaign.development_programs.get(campaign.current_era)
    )
    return program["failure_risk_multiplier"] if program else 1.0


def _complete_engineering_project(campaign, project):
    """Apply a finished project through the normal research-state API."""
    _, _, add_method, _ = _ENGINEERING_PROJECT_BRANCHES[project.branch]
    getattr(campaign.research, add_method)(project.technology_id)


def sign_sponsor(campaign, sponsor_id):
    """Sign a sponsor, banking its signing bonus once reputation allows it."""
    require_development_season(campaign)
    sponsor = SPONSOR_BY_ID.get(sponsor_id)
    if sponsor is None:
        raise ValueError(f"unknown sponsor: {sponsor_id}")
    if campaign.sponsorship.has_sponsor(sponsor_id):
        raise ValueError(f"{sponsor.name} has already been signed")
    if sponsor_id in campaign.sponsorship.departed_sponsors:
        raise ValueError(f"{sponsor.name} has withdrawn for this turn; negotiations reopen next turn")
    if campaign.team.reputation < sponsor.reputation_required:
        raise ValueError(f"not enough reputation to sign {sponsor.name}")

    campaign.sponsorship.add_sponsor(sponsor_id)
    campaign.team.cash = round(campaign.team.cash + sponsor.signing_bonus_gbp, 2)
    return issue_sponsor_objective(campaign, sponsor_id)


def reset_campaign(path=CAMPAIGN_FILE):
    """Erase the saved campaign and return a fresh one."""
    if path.exists():
        path.unlink()
    return CampaignState()


def calculate_workshop_upgrade_cost(team):
    """Return the cost to upgrade the workshop, scaling with its level."""
    return round(WORKSHOP_UPGRADE_BASE_COST_GBP * team.workshop_level)


def hire_engineer(campaign):
    """Spend cash to add an engineer to the team."""
    require_development_season(campaign)
    if campaign.team.cash < ENGINEER_HIRE_COST_GBP:
        raise ValueError("insufficient funds to hire an engineer")

    campaign.team.cash = round(campaign.team.cash - ENGINEER_HIRE_COST_GBP, 2)
    campaign.team.engineers += 1


def engine_tune_cost(engine_name, stage):
    engine = AVAILABLE_ENGINES[engine_name]
    factor = ENGINE_TUNE_COST_FACTORS.get(stage)
    if factor is None:
        raise ValueError("invalid engine tune stage")
    return max(100, round(engine.purchase_cost_gbp * factor / 100) * 100)


def apply_engine_tune(campaign, garage_entry, stage):
    require_development_season(campaign)
    if campaign.record_attempt is not None:
        raise ValueError("finish the official record attempt before tuning")
    reason = vehicle_unavailable_reason(garage_entry)
    if reason:
        raise ValueError(reason)
    if not any(entry is garage_entry for entry in campaign.garage.vehicles):
        raise ValueError("vehicle is not in the active garage")
    if campaign.engine_tunes_this_turn >= 1:
        raise ValueError("only one engine tune can be applied per turn")
    if stage != garage_entry.engine_tune_stage + 1:
        raise ValueError("engine tuning must advance exactly one stage")
    cost = engine_tune_cost(garage_entry.engine_name, stage)
    if campaign.team.cash < cost:
        raise ValueError("insufficient funds for engine tuning")
    campaign.team.cash = round(campaign.team.cash - cost, 2)
    garage_entry.engine_tune_stage = stage
    campaign.engine_tune_stages[garage_entry.engine_name] = max(
        stage, campaign.engine_tune_stages.get(garage_entry.engine_name, 0)
    )
    campaign.engine_tunes_this_turn += 1
    return cost


def hire_mechanic(campaign):
    """Spend cash to add a mechanic to the team."""
    require_development_season(campaign)
    if campaign.team.cash < MECHANIC_HIRE_COST_GBP:
        raise ValueError("insufficient funds to hire a mechanic")

    campaign.team.cash = round(campaign.team.cash - MECHANIC_HIRE_COST_GBP, 2)
    campaign.team.mechanics += 1


def hire_specialist_engineer(campaign, specialty):
    require_development_season(campaign)
    if specialty not in _ENGINEERING_PROJECT_BRANCHES:
        raise ValueError("unknown engineering specialty")
    if campaign.team.cash < SPECIALIST_HIRE_COST_GBP:
        raise ValueError("insufficient funds to hire a specialist")
    campaign.team.cash = round(campaign.team.cash - SPECIALIST_HIRE_COST_GBP, 2)
    campaign.team.engineers += 1
    campaign.team.engineer_specialties.append(specialty)


def hire_experienced_mechanic(campaign):
    require_development_season(campaign)
    if campaign.team.cash < EXPERIENCED_MECHANIC_HIRE_COST_GBP:
        raise ValueError("insufficient funds to hire an experienced mechanic")
    campaign.team.cash = round(campaign.team.cash - EXPERIENCED_MECHANIC_HIRE_COST_GBP, 2)
    campaign.team.mechanics += 1
    campaign.team.experienced_mechanics += 1


def dismiss_engineer(campaign, specialty=None):
    require_development_season(campaign)
    if campaign.record_attempt is not None:
        raise ValueError("finish the official attempt before releasing staff")
    if campaign.team.engineers <= 1:
        raise ValueError("retain at least one engineer for future research")
    if specialty is not None:
        if specialty not in available_engineer_specialties(campaign):
            raise ValueError("no unassigned specialist in this branch")
        campaign.team.engineer_specialties.remove(specialty)
    else:
        ordinary_allocated = sum(
            project.engineers_required - len(project.specialists)
            for project in campaign.engineering_projects
        )
        if campaign.team.engineers - len(campaign.team.engineer_specialties) <= ordinary_allocated:
            raise ValueError("no unassigned standard engineer to release")
    campaign.team.engineers -= 1


def dismiss_mechanic(campaign, experienced=False):
    require_development_season(campaign)
    if campaign.record_attempt is not None:
        raise ValueError("finish the official attempt before releasing staff")
    if campaign.team.mechanics <= 1 and any(entry.workshop_turns_remaining > 0 for entry in campaign.garage.vehicles):
        raise ValueError("retain a mechanic until workshop jobs are complete")
    if experienced:
        if campaign.team.experienced_mechanics <= 0:
            raise ValueError("no experienced mechanic to release")
        campaign.team.experienced_mechanics -= 1
    elif campaign.team.mechanics <= campaign.team.experienced_mechanics:
        raise ValueError("no standard mechanic to release")
    campaign.team.mechanics -= 1


def upgrade_workshop(campaign):
    require_development_season(campaign)
    """Spend cash to raise the workshop level."""
    cost_gbp = calculate_workshop_upgrade_cost(campaign.team)
    if campaign.team.cash < cost_gbp:
        raise ValueError("insufficient funds to upgrade the workshop")

    campaign.team.cash = round(campaign.team.cash - cost_gbp, 2)
    campaign.team.workshop_level += 1


def vehicle_construction_complexity(garage_entry):
    """Rate the most advanced fitted technology from 1 (Pioneer) to 5 (Modern)."""
    chassis = CHASSIS_BY_ID[garage_entry.chassis_id]
    engine = AVAILABLE_ENGINES[garage_entry.engine_name]
    technology_nodes = [
        CHASSIS_TECHNOLOGY_BY_ID.get(chassis.required_technology),
        ENGINE_TECHNOLOGY_BY_ID.get(engine.required_technology),
        *[
            AERODYNAMICS_TECHNOLOGY_BY_ID[technology_id]
            for technology_id in garage_entry.aerodynamics_technology
        ],
    ]
    eras = [node.era for node in technology_nodes if node is not None]
    eras.append(era_for_year(BRAKE_BY_NAME[garage_entry.brakes_name].introduced_year).name)
    return 1 + max(ERA_ORDER.index(era) for era in eras)


def vehicle_replacement_cost(entry):
    return round(
        CHASSIS_BY_ID[entry.chassis_id].cost_gbp
        + AVAILABLE_ENGINES[entry.engine_name].purchase_cost_gbp
        + AVAILABLE_GEARBOXES[entry.gearbox_name].cost_gbp
        + BRAKE_BY_NAME[entry.brakes_name].cost_gbp
    )


def vehicle_workshop_quote(entry):
    base_cost = vehicle_replacement_cost(entry)
    complexity = vehicle_construction_complexity(entry)
    if entry.condition == "Destroyed":
        return "Rebuild", base_cost, complexity
    if entry.condition == "Heavily Damaged":
        return "Major repair", round(base_cost * 0.65), max(1, ceil(complexity * 0.75))
    if entry.condition == "Damaged":
        return "Repair", round(base_cost * 0.30), max(1, ceil(complexity * 0.5))
    return "Service", round(base_cost * 0.08), max(1, ceil(complexity * 0.25))


def vehicle_unavailable_reason(entry):
    if entry.workshop_turns_remaining > 0:
        return f"{entry.workshop_action} in progress: {entry.workshop_turns_remaining} turn(s) remaining."
    if entry.condition == "Destroyed":
        return "Vehicle destroyed: a paid rebuild is required before another run."
    if entry.condition == "Heavily Damaged":
        return "Vehicle heavily damaged: workshop repair is required before another run."
    return None


def start_vehicle_workshop_job(campaign, entry):
    require_development_season(campaign)
    _require_active_garage_vehicle(campaign, entry, require_ready=False)
    if campaign.record_attempt is not None:
        raise ValueError("finish or abandon the official attempt before workshop work")
    if entry.workshop_turns_remaining > 0:
        raise ValueError("this vehicle already has workshop work in progress")
    if entry.wear <= 0 and entry.damage <= 0:
        raise ValueError("this vehicle does not need servicing")
    if campaign.team.mechanics < 1:
        raise ValueError("at least one mechanic is required for workshop work")
    action, cost, turns = vehicle_workshop_quote(entry)
    if campaign.team.cash < cost:
        raise ValueError("insufficient funds for workshop work")
    campaign.team.cash = round(campaign.team.cash - cost, 2)
    entry.workshop_action = action
    entry.workshop_turns_total = turns
    entry.workshop_turns_remaining = turns
    return action, cost, turns


def build_vehicle(campaign, garage_entry, cost_gbp, vehicle=None):
    """Pay up front and queue construction; End Turn delivers finished vehicles."""
    require_development_season(campaign)
    if campaign.record_attempt is not None:
        raise ValueError("finish the official record attempt before starting construction")
    owned_vehicles = (
        campaign.garage.vehicles
        + campaign.garage.museum
        + [project.vehicle for project in campaign.vehicle_construction]
    )
    if any(entry.vehicle_name.casefold() == garage_entry.vehicle_name.casefold() for entry in owned_vehicles):
        raise ValueError("vehicle name is already in use")
    if cost_gbp < 0:
        raise ValueError("construction cost must not be negative")
    if campaign.team.cash < cost_gbp:
        raise ValueError("insufficient funds to build this vehicle")

    complexity = vehicle_construction_complexity(garage_entry)
    construction = VehicleConstruction(
        vehicle=deepcopy(garage_entry),
        complexity=complexity,
        turns_total=complexity,
        turns_remaining=complexity,
    )
    campaign.team.cash = round(campaign.team.cash - cost_gbp, 2)
    campaign.vehicle_construction.append(construction)
    if vehicle is not None:
        reset_vehicle_log(vehicle)
    return construction


def _charge_trackside_adjustment(campaign):
    if campaign.team.cash < TRACKSIDE_ADJUSTMENT_COST_GBP:
        raise ValueError("insufficient funds for trackside service")
    campaign.team.cash = round(
        campaign.team.cash - TRACKSIDE_ADJUSTMENT_COST_GBP, 2
    )


def _require_active_garage_vehicle(campaign, garage_entry, require_ready=True):
    if not any(vehicle is garage_entry for vehicle in campaign.garage.vehicles):
        raise ValueError("vehicle is not in the active garage")
    if require_ready:
        reason = vehicle_unavailable_reason(garage_entry)
        if reason:
            raise ValueError(reason)


def adjust_vehicle_ratio_trackside(campaign, garage_entry, gear_index, delta):
    """Apply and charge for a small trackside gearbox ratio adjustment."""
    require_competition_season(campaign)
    _require_active_garage_vehicle(campaign, garage_entry)
    gearbox = deepcopy(AVAILABLE_GEARBOXES[garage_entry.gearbox_name])
    if garage_entry.gearbox_ratios:
        gearbox.gears = tuple(garage_entry.gearbox_ratios)
    if garage_entry.gearbox_final_drive is not None:
        gearbox.final_drive = garage_entry.gearbox_final_drive
    if not adjust_gearbox_ratio(gearbox, gear_index, delta):
        raise ValueError("requested ratio is outside the adjustment limits")

    _charge_trackside_adjustment(campaign)
    garage_entry.gearbox_ratios = tuple(gearbox.gears)
    garage_entry.gearbox_final_drive = gearbox.final_drive_ratio


def apply_gear_ratios_trackside(campaign, garage_entry, gears, final_drive):
    """Fit a complete set of ratios for one trackside service charge."""
    require_competition_season(campaign)
    _require_active_garage_vehicle(campaign, garage_entry)
    gearbox = AVAILABLE_GEARBOXES[garage_entry.gearbox_name]
    if len(gears) != gearbox.gear_count:
        raise ValueError("ratio set does not match this gearbox")
    if not 0.5 <= final_drive <= 6.0 or any(not 0.5 <= ratio <= 5.0 for ratio in gears):
        raise ValueError("requested ratio is outside the adjustment limits")

    _charge_trackside_adjustment(campaign)
    garage_entry.gearbox_ratios = tuple(gears)
    garage_entry.gearbox_final_drive = final_drive


def fit_trackside_tyres(campaign, garage_entry):
    """Fit researched pneumatic racing tyres without advancing campaign time."""
    require_competition_season(campaign)
    _require_active_garage_vehicle(campaign, garage_entry)
    if not campaign.research.has_tyre_technology("pneumatic_racing_tyres"):
        raise ValueError("Pneumatic Racing Tyres must be researched first")
    if garage_entry.tyre_grip_factor is not None:
        raise ValueError("this vehicle already has its trackside tyre set")
    current_grip = CHASSIS_BY_ID[garage_entry.chassis_id].tyre_grip_factor
    replacement_grip = min(1.0, current_grip + 0.03)
    if replacement_grip <= current_grip:
        raise ValueError("this vehicle is already at the tyre grip limit")

    _charge_trackside_adjustment(campaign)
    garage_entry.tyre_grip_factor = round(replacement_grip, 3)
    return garage_entry.tyre_grip_factor


def fit_trackside_brakes(campaign, garage_entry, brakes_name, current_year):
    """Fit an era-appropriate brake system as low-cost trackside service."""
    require_competition_season(campaign)
    _require_active_garage_vehicle(campaign, garage_entry)
    if not any(
        brakes.name == brakes_name
        for brakes in available_brakes(
            current_year, campaign.research.brake_technology
        )
    ):
        raise ValueError("brake system is not available in the current era")
    if garage_entry.brakes_name == brakes_name:
        raise ValueError("this brake system is already fitted")

    _charge_trackside_adjustment(campaign)
    garage_entry.brakes_name = brakes_name


def retire_vehicle(campaign, garage_entry):
    """Move an active garage vehicle into the team's museum."""
    require_development_season(campaign)
    if garage_entry.workshop_turns_remaining > 0:
        raise ValueError("finish workshop work before retiring this vehicle")
    vehicle_index = next(
        (
            index
            for index, vehicle in enumerate(campaign.garage.vehicles)
            if vehicle is garage_entry
        ),
        None,
    )
    if vehicle_index is None:
        raise ValueError("vehicle is not in the active garage")

    campaign.garage.museum.append(campaign.garage.vehicles.pop(vehicle_index))
