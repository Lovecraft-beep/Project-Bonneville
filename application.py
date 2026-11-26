"""UI-independent application boundary for campaign operations."""

from pathlib import Path

import management
from management import CampaignState, load_campaign, reset_campaign, save_campaign
from research import (
    AERODYNAMICS_TECHNOLOGY_TREE,
    BRAKE_TECHNOLOGY_TREE,
    CHASSIS_TECHNOLOGY_TREE,
    ENGINE_TECHNOLOGY_TREE,
    GEARBOX_TECHNOLOGY_TREE,
    TYRE_TECHNOLOGY_TREE,
    TECHNOLOGY_NAME_BY_ID,
)


class CampaignApplication:
    """Own the current campaign and expose application-level operations."""

    def __init__(self, save_path=management.CAMPAIGN_FILE):
        self.save_path = Path(save_path)
        self.campaign: CampaignState = load_campaign(self.save_path)

    def new_campaign(self):
        """Replace the current campaign with a fresh one."""
        self.campaign = reset_campaign(self.save_path)
        return self.campaign

    def load(self):
        """Load the campaign from the configured save path."""
        self.campaign = load_campaign(self.save_path)
        return self.campaign

    def save(self):
        """Persist the current campaign to the configured save path."""
        save_campaign(self.campaign, self.save_path)

    def advance_turn(self, days=None):
        """Advance and persist the campaign, returning completed research IDs."""
        completed = management.advance_turn(self.campaign, days=days)
        self.save()
        return completed

    def summary(self):
        """Return a JSON-serialisable snapshot of the campaign overview."""
        record = management.standing_world_record(self.campaign)
        if record is None:
            record_speed, record_holder, record_year = None, None, None
        else:
            record_speed, record_holder, record_year = record

        return {
            "campaign_id": self.campaign.campaign_id,
            "turn_number": self.campaign.turn_number,
            "current_year": self.campaign.current_year,
            "current_day_of_year": self.campaign.current_day_of_year,
            "current_season": self.campaign.current_season,
            "current_era": self.campaign.current_era,
            "team": {
                "name": self.campaign.team.name,
                "cash": self.campaign.team.cash,
                "reputation": self.campaign.team.reputation,
                "engineers": self.campaign.team.engineers,
                "mechanics": self.campaign.team.mechanics,
                "workshop_level": self.campaign.team.workshop_level,
            },
            "world_record": {
                "speed_mph": record_speed,
                "holder": record_holder,
                "year": record_year,
            },
            "headlines": list(self.campaign.world.headlines),
            "reactions": list(self.campaign.world.reactions),
        }

    def select_development_program(self, program_id):
        """Select and persist the major development programme for the current era."""
        result = management.select_development_program(
            self.campaign,
            program_id,
        )
        self.save()
        return result

    def research_summary(self):
        """Return a read-only, JSON-serialisable snapshot of research."""
        research = self.campaign.research
        branches = {
            "Engine": (
                ENGINE_TECHNOLOGY_TREE,
                "engine_technology",
                ("chassis_technology", "aerodynamics_technology"),
                "engine",
            ),
            "Chassis": (
                CHASSIS_TECHNOLOGY_TREE,
                "chassis_technology",
                ("aerodynamics_technology",),
                "chassis",
            ),
            "Aerodynamics": (
                AERODYNAMICS_TECHNOLOGY_TREE,
                "aerodynamics_technology",
                ("chassis_technology",),
                "aerodynamics",
            ),
            "Gearbox": (
                GEARBOX_TECHNOLOGY_TREE,
                "gearbox_technology",
                ("chassis_technology",),
                "gearbox",
            ),
            "Tyres": (
                TYRE_TECHNOLOGY_TREE,
                "tyre_technology",
                ("chassis_technology",),
                "tyre",
            ),
            "Brakes": (
                BRAKE_TECHNOLOGY_TREE,
                "brake_technology",
                ("chassis_technology",),
                "brake",
            ),
        }
        active_projects = {
            project.technology_id: project
            for project in self.campaign.engineering_projects
        }
        branch_summaries = {}
        for branch_name, (
            tree,
            researched_attribute,
            shared_attributes,
            branch_key,
        ) in branches.items():
            researched = set(getattr(research, researched_attribute))
            combined_researched = set(researched)
            for attribute in shared_attributes:
                combined_researched.update(getattr(research, attribute))

            technologies = []
            for technology in tree:
                project = active_projects.get(technology.technology_id)
                prerequisites_met = set(technology.prerequisites).issubset(
                    combined_researched
                )
                if technology.technology_id in researched:
                    status = "COMPLETE"
                elif project is not None:
                    status = "IN PROGRESS"
                elif (
                    technology.era == self.campaign.current_era
                    and technology.era not in self.campaign.development_programs
                    and prerequisites_met
                ):
                    status = "PROGRAM REQUIRED"
                elif (
                    prerequisites_met
                    and not (
                        technology.era == self.campaign.current_era
                        and technology.era
                        not in self.campaign.development_programs
                    )
                ):
                    status = "AVAILABLE"
                else:
                    status = "LOCKED"

                project_cost, project_turns = management.engineering_project_terms(
                    self.campaign, branch_key, technology
                )
                technologies.append(
                    {
                        "technology_id": technology.technology_id,
                        "name": technology.name,
                        "era": technology.era,
                        "description": technology.description,
                        "status": status,
                        "effective_project_cost": project_cost,
                        "effective_project_turns": project_turns,
                        "engineers_required": technology.engineers_required,
                    }
                )
            branch_summaries[branch_name] = {"technologies": technologies}

        return {
            "current_era": self.campaign.current_era,
            "available_engineers": self.campaign.available_engineers,
            "total_engineers": self.campaign.team.engineers,
            "cash": self.campaign.team.cash,
            "selected_development_program": self.campaign.development_programs.get(
                self.campaign.current_era
            ),
            "development_programs": [
                {
                    "program_id": program_id,
                    "name": program["name"],
                    "description": program["description"],
                }
                for program_id, program in management.DEVELOPMENT_PROGRAMS.items()
            ],
            "active_engineering_projects": [
                {
                    "branch": project.branch,
                    "technology_id": project.technology_id,
                    "name": TECHNOLOGY_NAME_BY_ID[project.technology_id],
                    "turns_total": project.turns_total,
                    "turns_remaining": project.turns_remaining,
                    "engineers_required": project.engineers_required,
                    "specialists": list(project.specialists),
                }
                for project in self.campaign.engineering_projects
            ],
            "branches": branch_summaries,
        }
