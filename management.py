"""Campaign management state for Project Bonneville."""

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from diagnostics import reset_vehicle_log
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

    def add_engine_technology(self, technology_id):
        """Record a technology once its research action is implemented."""
        if technology_id not in ENGINE_TECHNOLOGY_BY_ID:
            raise ValueError(f"unknown engine technology: {technology_id}")
        if technology_id not in self.engine_technology:
            self.engine_technology.append(technology_id)

    @property
    def chassis_technology_level(self):
        return len(self.chassis_technology)

    def has_chassis_technology(self, technology_id):
        return technology_id in self.chassis_technology

    def add_chassis_technology(self, technology_id):
        if technology_id not in CHASSIS_TECHNOLOGY_BY_ID:
            raise ValueError(f"unknown chassis technology: {technology_id}")
        if technology_id not in self.chassis_technology:
            self.chassis_technology.append(technology_id)

    def has_aerodynamics_technology(self, technology_id):
        return technology_id in self.aerodynamics_technology

    def add_aerodynamics_technology(self, technology_id):
        if technology_id not in AERODYNAMICS_TECHNOLOGY_BY_ID:
            raise ValueError(f"unknown aerodynamics technology: {technology_id}")
        if technology_id not in self.aerodynamics_technology:
            self.aerodynamics_technology.append(technology_id)

    def has_tyre_technology(self, technology_id):
        return technology_id in self.tyre_technology

    def add_tyre_technology(self, technology_id):
        if technology_id not in TYRE_TECHNOLOGY_BY_ID:
            raise ValueError(f"unknown tyre technology: {technology_id}")
        if technology_id not in self.tyre_technology:
            self.tyre_technology.append(technology_id)

    def has_brake_technology(self, technology_id):
        return technology_id in self.brake_technology

    def add_brake_technology(self, technology_id):
        if technology_id not in BRAKE_TECHNOLOGY_BY_ID:
            raise ValueError(f"unknown brake technology: {technology_id}")
        if technology_id not in self.brake_technology:
            self.brake_technology.append(technology_id)

    def has_gearbox_technology(self, technology_id):
        return technology_id in self.gearbox_technology

    def add_gearbox_technology(self, technology_id):
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


@dataclass
class Garage:
    """Custom vehicles built by the team and available for future runs."""

    vehicles: list[GarageVehicle] = field(default_factory=list)


@dataclass
class CampaignState:
    team: Team = field(default_factory=Team)
    research: ResearchState = field(default_factory=ResearchState)
    sponsorship: SponsorshipState = field(default_factory=SponsorshipState)
    garage: Garage = field(default_factory=Garage)
    campaign_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    current_year: int = STARTING_YEAR
    turn_number: int = 1
    completed_runs: int = 0
    failed_runs: int = 0
    best_measured_mile_speed_mph: float = 0.0

    @property
    def funds_gbp(self):
        """Compatibility view of the team's available cash."""
        return self.team.cash

    @funds_gbp.setter
    def funds_gbp(self, value):
        self.team.cash = value


def calculate_run_cost(vehicle, track):
    """Return the total setup cost for a vehicle and track combination."""
    return round(
        vehicle.engine.purchase_cost_gbp
        + vehicle.gearbox.cost_gbp
        + track.event_cost_gbp
    )


def load_campaign(path=CAMPAIGN_FILE):
    """Load campaign state, creating a fresh campaign when none exists."""
    if not path.exists():
        return CampaignState()

    with path.open("r", encoding="utf-8") as campaign_file:
        data = json.load(campaign_file)

    if "team" in data:
        data["team"] = Team(**data["team"])
        data["research"] = ResearchState(**data.get("research", {}))
        data["sponsorship"] = SponsorshipState(**data.get("sponsorship", {}))
        garage_data = data.get("garage", {})
        data["garage"] = Garage(
            vehicles=[
                GarageVehicle(**vehicle) for vehicle in garage_data.get("vehicles", [])
            ]
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


def complete_run(campaign, run_cost_gbp, measured_mile_speed_mph):
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
    campaign.team.reputation = round(
        campaign.team.reputation + (2.0 if is_new_record else 1.0), 2
    )


def complete_failed_run(campaign, run_cost_gbp):
    """Charge a run that failed and could not be repaired trackside."""
    if run_cost_gbp > campaign.funds_gbp:
        raise ValueError("campaign does not have enough funds for this run")

    campaign.funds_gbp = round(campaign.funds_gbp - run_cost_gbp, 2)
    campaign.failed_runs += 1


def advance_turn(campaign):
    """Move the campaign to the next annual planning turn."""
    campaign.team.cash = round(
        campaign.team.cash + campaign.sponsorship.income_per_turn_gbp, 2
    )
    campaign.turn_number += 1
    campaign.current_year += 1


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


def research_engine_technology(campaign, technology_id):
    """Spend cash and engineer time to unlock an engine technology."""
    technology = ENGINE_TECHNOLOGY_BY_ID.get(technology_id)
    if technology is None:
        raise ValueError(f"unknown engine technology: {technology_id}")
    if campaign.research.has_engine_technology(technology_id):
        raise ValueError(f"{technology.name} has already been researched")
    researched = set(campaign.research.engine_technology) | set(
        campaign.research.chassis_technology
    )
    if not set(technology.prerequisites).issubset(researched):
        raise ValueError(
            f"chassis or engine prerequisites not met for {technology.name}"
        )
    if campaign.team.cash < technology.cost_gbp:
        raise ValueError("insufficient funds for this research project")
    if campaign.team.engineers < technology.engineers_required:
        raise ValueError("not enough engineers available for this research project")

    campaign.team.cash = round(campaign.team.cash - technology.cost_gbp, 2)
    campaign.research.add_engine_technology(technology_id)


def research_chassis_technology(campaign, technology_id):
    """Spend cash and engineer time to unlock a chassis technology."""
    technology = CHASSIS_TECHNOLOGY_BY_ID.get(technology_id)
    if technology is None:
        raise ValueError(f"unknown chassis technology: {technology_id}")
    if campaign.research.has_chassis_technology(technology_id):
        raise ValueError(f"{technology.name} has already been researched")
    if not set(technology.prerequisites).issubset(campaign.research.chassis_technology):
        raise ValueError(f"prerequisites not met for {technology.name}")
    if campaign.team.cash < technology.cost_gbp:
        raise ValueError("insufficient funds for this research project")
    if campaign.team.engineers < technology.engineers_required:
        raise ValueError("not enough engineers available for this research project")

    campaign.team.cash = round(campaign.team.cash - technology.cost_gbp, 2)
    campaign.research.add_chassis_technology(technology_id)


def _research_branch_technology(campaign, technology_id, tree_by_id, researched, add):
    technology = tree_by_id.get(technology_id)
    if technology is None:
        raise ValueError(f"unknown technology: {technology_id}")
    if technology_id in researched:
        raise ValueError(f"{technology.name} has already been researched")
    available_research = set(researched) | set(campaign.research.chassis_technology)
    if not set(technology.prerequisites).issubset(available_research):
        raise ValueError(
            f"chassis or branch prerequisites not met for {technology.name}"
        )
    if campaign.team.cash < technology.cost_gbp:
        raise ValueError("insufficient funds for this research project")
    if campaign.team.engineers < technology.engineers_required:
        raise ValueError("not enough engineers available for this research project")

    campaign.team.cash = round(campaign.team.cash - technology.cost_gbp, 2)
    add(technology_id)


def research_aerodynamics_technology(campaign, technology_id):
    _research_branch_technology(
        campaign,
        technology_id,
        AERODYNAMICS_TECHNOLOGY_BY_ID,
        campaign.research.aerodynamics_technology,
        campaign.research.add_aerodynamics_technology,
    )


def research_tyre_technology(campaign, technology_id):
    _research_branch_technology(
        campaign,
        technology_id,
        TYRE_TECHNOLOGY_BY_ID,
        campaign.research.tyre_technology,
        campaign.research.add_tyre_technology,
    )


def research_brake_technology(campaign, technology_id):
    _research_branch_technology(
        campaign,
        technology_id,
        BRAKE_TECHNOLOGY_BY_ID,
        campaign.research.brake_technology,
        campaign.research.add_brake_technology,
    )


def research_gearbox_technology(campaign, technology_id):
    _research_branch_technology(
        campaign,
        technology_id,
        GEARBOX_TECHNOLOGY_BY_ID,
        campaign.research.gearbox_technology,
        campaign.research.add_gearbox_technology,
    )


def build_vehicle(campaign, garage_entry, cost_gbp, vehicle=None):
    """Pay the construction cost and save a new vehicle to the garage."""
    if campaign.team.cash < cost_gbp:
        raise ValueError("insufficient funds to build this vehicle")

    campaign.team.cash = round(campaign.team.cash - cost_gbp, 2)
    campaign.garage.vehicles.append(garage_entry)
    if vehicle is not None:
        reset_vehicle_log(vehicle)
