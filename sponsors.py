"""Sponsorship definitions for Project Bonneville."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Sponsor:
    sponsor_id: str
    name: str
    description: str
    reputation_required: float = 0.0
    signing_bonus_gbp: float = 0.0
    income_per_turn_gbp: float = 0.0
    reliability_bonus: float = 0.0


SPONSOR_CATALOG = (
    Sponsor(
        "local_investor",
        "Local Investor",
        "A regional backer eager to attach their name to a record attempt.",
        signing_bonus_gbp=10_000.0,
    ),
    Sponsor(
        "castrol",
        "Castrol",
        "Lubricant partnership improves engine reliability.",
        signing_bonus_gbp=3_000.0,
        reliability_bonus=0.03,
    ),
    Sponsor(
        "dunlop",
        "Dunlop",
        "Tyre technology partnership reduces mechanical risk.",
        reputation_required=5.0,
        signing_bonus_gbp=2_000.0,
        reliability_bonus=0.04,
    ),
    Sponsor(
        "shell",
        "Shell",
        "Fuel partnership funds operations and reduces misfire risk.",
        reputation_required=5.0,
        signing_bonus_gbp=5_000.0,
        income_per_turn_gbp=500.0,
        reliability_bonus=0.02,
    ),
    Sponsor(
        "napier",
        "Napier",
        "Close technical support from the engine manufacturer.",
        reputation_required=10.0,
        reliability_bonus=0.05,
    ),
    Sponsor(
        "government_grant",
        "Government Grant",
        "State backing for a national land-speed record campaign.",
        reputation_required=15.0,
        signing_bonus_gbp=20_000.0,
        income_per_turn_gbp=1_000.0,
    ),
)

SPONSOR_BY_ID = {sponsor.sponsor_id: sponsor for sponsor in SPONSOR_CATALOG}


def available_sponsors(reputation, active_sponsor_ids):
    """Return sponsors the team can sign given its reputation."""
    active_ids = set(active_sponsor_ids)
    return tuple(
        sponsor
        for sponsor in SPONSOR_CATALOG
        if sponsor.sponsor_id not in active_ids
        and reputation >= sponsor.reputation_required
    )
