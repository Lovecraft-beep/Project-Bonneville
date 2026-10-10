"""Deterministic rivals, headlines, historical events, and world reactions."""

from dataclasses import dataclass, field
from datetime import date, timedelta

from historical_records import HISTORICAL_TARGETS


@dataclass
class RivalState:
    rival_id: str
    name: str
    home: str
    specialty: str
    performance_multiplier: float
    best_speed_mph: float = 0.0


@dataclass
class WorldState:
    rivals: list[RivalState] = field(default_factory=list)
    headlines: list[str] = field(default_factory=list)
    reactions: list[str] = field(default_factory=list)
    historical_events_seen: list[str] = field(default_factory=list)
    historical_attempts_seen: list[str] = field(default_factory=list)
    record_speed_mph: float = 0.0
    record_holder: str = ""
    record_year: int = 0


@dataclass(frozen=True)
class HistoricalEvent:
    event_id: str
    year: int
    headline: str
    reaction: str


RIVAL_CATALOG = tuple(
    RivalState(
        driver,
        f"{driver} Team",
        next(target.location.rsplit(", ", 1)[-1] for target in HISTORICAL_TARGETS if target.driver == driver),
        next(target.propulsion for target in HISTORICAL_TARGETS if target.driver == driver),
        1.0,
    )
    for driver in dict.fromkeys(target.driver for target in HISTORICAL_TARGETS)
)


HISTORICAL_EVENTS = (
    HistoricalEvent(
        "electric_record_1899",
        1899,
        "La Jamais Contente breaks the 100 km/h barrier.",
        "Electric power is no longer a curiosity; every workshop is reconsidering its assumptions.",
    ),
    HistoricalEvent(
        "first_american_record_1904",
        1904,
        "America claims the land-speed record on a frozen lake.",
        "American backers begin looking for teams willing to trade elegance for horsepower.",
    ),
    HistoricalEvent(
        "pendine_era_1927",
        1927,
        "The Pendine streamliner era reaches its dramatic peak.",
        "Crowds now expect a record attempt to look as spectacular as it is fast.",
    ),
    HistoricalEvent(
        "bonneville_300_1935",
        1935,
        "The record crosses 300 mph at Bonneville Salt Flats.",
        "Bonneville becomes the center of the speed world, and sponsors demand bigger ambitions.",
    ),
    HistoricalEvent(
        "jet_age_1963",
        1963,
        "Thrust-powered cars enter the absolute record contest.",
        "Engineers stop asking how to transmit power to the wheels and start asking how to survive thrust.",
    ),
    HistoricalEvent(
        "supersonic_record_1997",
        1997,
        "ThrustSSC claims the first supersonic land-speed record.",
        "The world treats land speed as aerospace engineering, and public scrutiny rises with the speed.",
    ),
)


def create_world_state():
    """Create fresh rival standings and an empty campaign news feed."""
    return WorldState(
        rivals=[RivalState(**vars(rival)) for rival in RIVAL_CATALOG],
        headlines=["The new season begins. The record books are still open."],
    )


def synchronize_rivals(world):
    """Migrate anonymous rivals and add historical teams missing from older saves."""
    existing = {rival.rival_id: rival for rival in world.rivals}
    world.rivals = [
        existing.get(rival.rival_id, RivalState(**vars(rival)))
        for rival in RIVAL_CATALOG
    ]


def rival_standings(campaign):
    """Return teams that have competed, ordered by their best official speed."""
    return sorted(
        (rival for rival in campaign.world.rivals if rival.best_speed_mph > 0),
        key=lambda rival: (-rival.best_speed_mph, rival.name),
    )


def historical_record_at(campaign):
    """Return the historical baseline reached on the campaign's current date."""
    campaign_date = date(campaign.current_year, 1, 1) + timedelta(
        days=campaign.current_day_of_year - 1
    )
    return max(
        (target for target in HISTORICAL_TARGETS if target.date <= campaign_date.isoformat()),
        key=lambda target: target.speed_mph,
        default=None,
    )


def _remember(items, message, limit=8):
    items.append(message)
    del items[:-limit]


def advance_world(campaign):
    """Advance rival standings and create the new season's world report."""
    world = campaign.world
    world.headlines = []
    world.reactions = []
    synchronize_rivals(world)
    rivals = {rival.rival_id: rival for rival in world.rivals}
    campaign_date = date(campaign.current_year, 1, 1) + timedelta(
        days=campaign.current_day_of_year - 1
    )
    credited_speed = max(
        (target.speed_mph for target in HISTORICAL_TARGETS
         if target.record_id in campaign.completed_historical_record_ids),
        default=0.0,
    )
    standing_speed = max(world.record_speed_mph, campaign.official_record_mph, credited_speed)

    for target in sorted(HISTORICAL_TARGETS, key=lambda item: item.date):
        if target.date > campaign_date.isoformat() or target.record_id in world.historical_attempts_seen:
            continue
        world.historical_attempts_seen.append(target.record_id)
        rival = rivals[target.driver]
        rival.best_speed_mph = max(rival.best_speed_mph, target.speed_mph)
        if target.speed_mph > standing_speed:
            standing_speed = target.speed_mph
            world.record_speed_mph = target.speed_mph
            world.record_holder = rival.name
            world.record_year = target.year
            message = (
                f"WORLD RECORD: {rival.name} takes the record at {target.speed_mph:.2f} mph "
                f"in {target.vehicle} ({target.year})."
            )
        else:
            message = (
                f"{rival.name} runs {target.speed_mph:.2f} mph in {target.vehicle} "
                f"({target.year}); the standing record survives."
            )
        _remember(
            world.headlines,
            message,
        )

    for event in HISTORICAL_EVENTS:
        if event.year > campaign.current_year or event.event_id in world.historical_events_seen:
            continue
        world.historical_events_seen.append(event.event_id)
        _remember(world.headlines, f"HISTORICAL EVENT: {event.headline}")
        _remember(world.reactions, event.reaction)

    if campaign.best_measured_mile_speed_mph:
        rival_leader = max(
            (rival.best_speed_mph for rival in world.rivals), default=0.0
        )
        if campaign.best_measured_mile_speed_mph > rival_leader:
            _remember(
                world.reactions,
                "The press calls your team the pace-setter of the new season.",
            )
        elif rival_leader > campaign.best_measured_mile_speed_mph:
            _remember(
                world.reactions,
                "Your rivals have the initiative. Sponsors want an answer on the salt.",
            )

    if not world.headlines:
        _remember(world.headlines, "A quiet season: workshops prepare their next attempts.")