"""UI-independent application boundary for campaign operations."""

from pathlib import Path

import management
from management import CampaignState, load_campaign, reset_campaign, save_campaign


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
