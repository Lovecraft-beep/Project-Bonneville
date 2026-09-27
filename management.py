"""Campaign management state for Project Bonneville."""

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from diagnostics import reset_vehicle_log
from campaign_world import (
    RivalState,
    WorldState,
    advance_world,
    create_world_state,
)
from historical_records import (
    next_historical_target,
    record_ids_achieved_by_speed,
    target_completed,
)
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


@dataclass
class Garage:
    """Custom vehicles built by the team and available for future runs."""

    vehicles: list[GarageVehicle] = field(default_factory=list)


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
    campaign_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    current_year: int = STARTING_YEAR
    current_day_of_year: int = 1
    turn_number: int = 1
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
            ]
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
    campaign, run_cost_gbp, measured_mile_speed_mph, is_record_attempt=False
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
        target = next_historical_target(
            campaign.current_year, campaign.completed_historical_record_ids
        )
        if target and target_completed(target, measured_mile_speed_mph):
            completed_ids = set(campaign.completed_historical_record_ids)
            newly_completed_record_ids = [
                record_id
                for record_id in record_ids_achieved_by_speed(
                    measured_mile_speed_mph
                )
                if record_id not in completed_ids
            ]
            campaign.completed_historical_record_ids.extend(
                newly_completed_record_ids
            )
            reputation_gain += len(newly_completed_record_ids)
            campaign.world.headlines.append(
                f"RECORD BEATEN: {campaign.team.name} exceeds the {target.year} "
                f"{target.vehicle} mark at {measured_mile_speed_mph:.1f} mph."
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
