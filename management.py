"""Campaign management state for Project Bonneville."""

import json
import uuid
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path

from brakes import available_brakes
from chassis import CHASSIS_BY_ID
from diagnostics import reset_vehicle_log
from campaign_world import (
    RivalState,
    WorldState,
    advance_world,
    create_world_state,
)
from historical_records import (
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
    GEARBOX_TECHNOLOGY_BY_ID,
    TYRE_TECHNOLOGY_BY_ID,
)
from sponsors import SPONSOR_BY_ID

CAMPAIGN_FILE = Path(__file__).with_name("campaign_state.json")
STARTING_FUNDS_GBP = 100_000.0
STARTING_YEAR = 1895
DEFAULT_TEAM_NAME = "Bonneville Racing Team"
ENGINEER_HIRE_COST_GBP = 8_000.0
MECHANIC_HIRE_COST_GBP = 5_000.0
WORKSHOP_UPGRADE_BASE_COST_GBP = 10_000.0
TRACKSIDE_ADJUSTMENT_COST_GBP = 5.0
MAX_TESTS_PER_SESSION = 8


@dataclass
class Team:
    """The management resources controlled by the player."""

    name: str = DEFAULT_TEAM_NAME
    cash: float = STARTING_FUNDS_GBP
    reputation: float = 0.0
    engineers: int = 1
    mechanics: int = 2
    workshop_level: int = 1


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
class SponsorshipState:
    """Sponsors signed by the team."""

    active_sponsors: list[str] = field(default_factory=list)

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


@dataclass
class Garage:
    """Custom vehicles in service and preserved in the team museum."""

    vehicles: list[GarageVehicle] = field(default_factory=list)
    museum: list[GarageVehicle] = field(default_factory=list)


@dataclass
class CampaignRecordAttempt:
    target_id: str
    vehicle_name: str
    track_name: str
    started_year: int
    required_runs: int
    speeds_mph: list[float] = field(default_factory=list)


@dataclass
class EngineeringProject:
    """Research work in progress, with its staff allocated until completion."""

    branch: str
    technology_id: str
    turns_total: int
    turns_remaining: int
    engineers_required: int


@dataclass
class CampaignState:
    team: Team = field(default_factory=Team)
    research: ResearchState = field(default_factory=ResearchState)
    engineering_projects: list[EngineeringProject] = field(default_factory=list)
    sponsorship: SponsorshipState = field(default_factory=SponsorshipState)
    garage: Garage = field(default_factory=Garage)
    record_attempt: CampaignRecordAttempt | None = None
    campaign_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    current_year: int = STARTING_YEAR
    current_day_of_year: int = 1
    turn_number: int = 1
    tests_this_session: int = 0
    venues_paid_this_session: list[str] = field(default_factory=list)
    completed_runs: int = 0
    failed_runs: int = 0
    best_measured_mile_speed_mph: float = 0.0
    completed_historical_record_ids: list[str] = field(default_factory=list)
    world: WorldState = field(default_factory=create_world_state)

    @property
    def funds_gbp(self):
        """Compatibility view of the team's available cash."""
        return self.team.cash

    @funds_gbp.setter
    def funds_gbp(self, value):
        self.team.cash = value

    @property
    def allocated_engineers(self):
        return sum(project.engineers_required for project in self.engineering_projects)

    @property
    def available_engineers(self):
        return max(0, self.team.engineers - self.allocated_engineers)


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
    owned_vehicles = campaign.garage.vehicles + campaign.garage.museum
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

    if "team" in data:
        data["team"] = Team(**data["team"])
        data["research"] = ResearchState(**data.get("research", {}))
        data["engineering_projects"] = [
            EngineeringProject(**project)
            for project in data.get("engineering_projects", [])
        ]
        data["sponsorship"] = SponsorshipState(**data.get("sponsorship", {}))
        garage_data = data.get("garage", {})
        data["garage"] = Garage(
            vehicles=[
                GarageVehicle(**vehicle) for vehicle in garage_data.get("vehicles", [])
            ],
            museum=[
                GarageVehicle(**vehicle) for vehicle in garage_data.get("museum", [])
            ],
        )
        record_attempt_data = data.get("record_attempt")
        data["record_attempt"] = (
            CampaignRecordAttempt(**record_attempt_data)
            if record_attempt_data is not None
            else None
        )
        data.setdefault(
            "completed_historical_record_ids",
            record_ids_achieved_by_speed(data.get("best_measured_mile_speed_mph", 0.0)),
        )
        world_data = data.get("world", {})
        data["world"] = WorldState(
            rivals=[RivalState(**rival) for rival in world_data.get("rivals", [])]
            or create_world_state().rivals,
            headlines=world_data.get("headlines", [])
            or create_world_state().headlines,
            reactions=world_data.get("reactions", []),
            historical_events_seen=world_data.get("historical_events_seen", []),
        )
        return CampaignState(**data)

    # Migrate campaign files written before Team became the owner of cash.
    team = Team(cash=data.pop("funds_gbp", STARTING_FUNDS_GBP))
    return CampaignState(team=team, **data)


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
):
    """Charge a completed run and update campaign performance."""
    if run_cost_gbp > campaign.funds_gbp:
        raise ValueError("campaign does not have enough funds for this run")

    campaign.funds_gbp = round(campaign.funds_gbp - run_cost_gbp, 2)
    campaign.completed_runs += 1
    is_new_record = measured_mile_speed_mph > campaign.best_measured_mile_speed_mph
    campaign.best_measured_mile_speed_mph = max(
        campaign.best_measured_mile_speed_mph,
        measured_mile_speed_mph,
    )
    reputation_gain = 2.0 if is_new_record else 1.0
    newly_completed_record_ids = []
    if is_record_attempt:
        record_speed_mph = (
            measured_mile_speed_mph
            if record_attempt_average_mph is None
            else record_attempt_average_mph
        )
        target = next_historical_target(
            campaign.current_year, campaign.completed_historical_record_ids
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


def complete_failed_run(campaign, run_cost_gbp):
    """Charge a run that failed and could not be repaired trackside."""
    if run_cost_gbp > campaign.funds_gbp:
        raise ValueError("campaign does not have enough funds for this run")

    campaign.funds_gbp = round(campaign.funds_gbp - run_cost_gbp, 2)
    campaign.failed_runs += 1


def advance_turn(campaign, days=365):
    """Advance campaign time and update the world when a year changes."""
    previous_year = campaign.current_year
    campaign.team.cash = round(
        campaign.team.cash + campaign.sponsorship.income_per_turn_gbp, 2
    )
    campaign.turn_number += 1
    campaign.tests_this_session = 0
    campaign.venues_paid_this_session = []
    elapsed_days = campaign.current_day_of_year - 1 + days
    campaign.current_year += elapsed_days // 365
    campaign.current_day_of_year = elapsed_days % 365 + 1
    completed_projects = []
    for project in campaign.engineering_projects:
        project.turns_remaining -= 1
        if project.turns_remaining <= 0:
            _complete_engineering_project(campaign, project)
            completed_projects.append(project.technology_id)
    if completed_projects:
        campaign.engineering_projects = [
            project
            for project in campaign.engineering_projects
            if project.technology_id not in completed_projects
        ]
    if campaign.current_year != previous_year:
        advance_world(campaign)
    return tuple(completed_projects)


def register_test_run(campaign):
    """Record one hourly campaign test, enforcing the session limit."""
    if campaign.tests_this_session >= MAX_TESTS_PER_SESSION:
        raise ValueError("test session is full; advance campaign time to start another")
    campaign.tests_this_session += 1
    return campaign.tests_this_session


def end_test_session(campaign):
    """End track operations and clear this session's hourly slots and venue fees."""
    if campaign.record_attempt is not None:
        raise ValueError("complete or abandon the official record attempt first")
    campaign.tests_this_session = 0
    campaign.venues_paid_this_session.clear()


_ENGINEERING_PROJECT_BRANCHES = {
    "engine": (
        ENGINE_TECHNOLOGY_BY_ID,
        "engine_technology",
        "_complete_engine_technology",
        ("engine_technology", "chassis_technology"),
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


def start_engineering_project(campaign, branch, technology_id):
    """Fund a technology project and reserve its required engineering staff."""
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
    if campaign.team.cash < technology.cost_gbp:
        raise ValueError("insufficient funds for this engineering project")
    if campaign.available_engineers < technology.engineers_required:
        raise ValueError("not enough unassigned engineers for this project")

    turns_required = max(1, technology.turns_required)
    project = EngineeringProject(
        branch=branch,
        technology_id=technology_id,
        turns_total=turns_required,
        turns_remaining=turns_required,
        engineers_required=technology.engineers_required,
    )
    campaign.team.cash = round(campaign.team.cash - technology.cost_gbp, 2)
    campaign.engineering_projects.append(project)
    return project


def _complete_engineering_project(campaign, project):
    """Apply a finished project through the normal research-state API."""
    _, _, add_method, _ = _ENGINEERING_PROJECT_BRANCHES[project.branch]
    getattr(campaign.research, add_method)(project.technology_id)


def sign_sponsor(campaign, sponsor_id):
    """Sign a sponsor, banking its signing bonus once reputation allows it."""
    sponsor = SPONSOR_BY_ID.get(sponsor_id)
    if sponsor is None:
        raise ValueError(f"unknown sponsor: {sponsor_id}")
    if campaign.sponsorship.has_sponsor(sponsor_id):
        raise ValueError(f"{sponsor.name} has already been signed")
    if campaign.team.reputation < sponsor.reputation_required:
        raise ValueError(f"not enough reputation to sign {sponsor.name}")

    campaign.sponsorship.add_sponsor(sponsor_id)
    campaign.team.cash = round(campaign.team.cash + sponsor.signing_bonus_gbp, 2)


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
    if campaign.team.cash < ENGINEER_HIRE_COST_GBP:
        raise ValueError("insufficient funds to hire an engineer")

    campaign.team.cash = round(campaign.team.cash - ENGINEER_HIRE_COST_GBP, 2)
    campaign.team.engineers += 1


def hire_mechanic(campaign):
    """Spend cash to add a mechanic to the team."""
    if campaign.team.cash < MECHANIC_HIRE_COST_GBP:
        raise ValueError("insufficient funds to hire a mechanic")

    campaign.team.cash = round(campaign.team.cash - MECHANIC_HIRE_COST_GBP, 2)
    campaign.team.mechanics += 1


def upgrade_workshop(campaign):
    """Spend cash to raise the workshop level."""
    cost_gbp = calculate_workshop_upgrade_cost(campaign.team)
    if campaign.team.cash < cost_gbp:
        raise ValueError("insufficient funds to upgrade the workshop")

    campaign.team.cash = round(campaign.team.cash - cost_gbp, 2)
    campaign.team.workshop_level += 1


def build_vehicle(campaign, garage_entry, cost_gbp, vehicle=None):
    """Pay the construction cost and save a new vehicle to the garage."""
    if campaign.team.cash < cost_gbp:
        raise ValueError("insufficient funds to build this vehicle")

    campaign.team.cash = round(campaign.team.cash - cost_gbp, 2)
    campaign.garage.vehicles.append(garage_entry)
    if vehicle is not None:
        reset_vehicle_log(vehicle)


def _charge_trackside_adjustment(campaign):
    if campaign.team.cash < TRACKSIDE_ADJUSTMENT_COST_GBP:
        raise ValueError("insufficient funds for trackside service")
    campaign.team.cash = round(
        campaign.team.cash - TRACKSIDE_ADJUSTMENT_COST_GBP, 2
    )


def _require_active_garage_vehicle(campaign, garage_entry):
    if not any(vehicle is garage_entry for vehicle in campaign.garage.vehicles):
        raise ValueError("vehicle is not in the active garage")


def adjust_vehicle_ratio_trackside(campaign, garage_entry, gear_index, delta):
    """Apply and charge for a small trackside gearbox ratio adjustment."""
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


def fit_trackside_tyres(campaign, garage_entry):
    """Fit a modestly higher-grip tyre set without advancing campaign time."""
    _require_active_garage_vehicle(campaign, garage_entry)
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
    _require_active_garage_vehicle(campaign, garage_entry)
    if not any(
        brakes.name == brakes_name
        for brakes in available_brakes(current_year)
    ):
        raise ValueError("brake system is not available in the current era")
    if garage_entry.brakes_name == brakes_name:
        raise ValueError("this brake system is already fitted")

    _charge_trackside_adjustment(campaign)
    garage_entry.brakes_name = brakes_name


def retire_vehicle(campaign, garage_entry):
    """Move an active garage vehicle into the team's museum."""
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
