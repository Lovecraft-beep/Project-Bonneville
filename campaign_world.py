"""Deterministic rivals, headlines, historical events, and world reactions."""

from dataclasses import dataclass, field

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


@dataclass(frozen=True)
class HistoricalEvent:
    event_id: str
    year: int
    headline: str
    reaction: str


RIVAL_CATALOG = (
    RivalState(
        "continental_union",
        "Continental Union Auto Club",
        "France",
        "early streamliners",
        0.91,
    ),
    RivalState(
        "american_speed syndicate".replace(" ", "_"),
        "American Speed Syndicate",
        "United States",
        "high-power specials",
        0.96,
    ),
    RivalState(
        "british_racing_association",
        "British Racing Association",
        "United Kingdom",
        "aerodynamic refinement",
        0.94,
    ),
    RivalState(
        "aerospace_research_division",
        "Aerospace Research Division",
        "International",
        "jet and rocket propulsion",
        0.89,
    ),
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


def _latest_historical_speed(year):
    available = [target for target in HISTORICAL_TARGETS if target.year <= year]
    return max((target.speed_mph for target in available), default=0.0)


def _remember(items, message, limit=8):
    items.append(message)
    del items[:-limit]


def advance_world(campaign):
    """Advance rival standings and create the new season's world report."""
    world = campaign.world
    world.headlines = []
    world.reactions = []
    latest_speed = _latest_historical_speed(campaign.current_year)

    for rival in world.rivals:
        rival_speed = round(latest_speed * rival.performance_multiplier, 1)
        if rival_speed <= rival.best_speed_mph:
            continue
        rival.best_speed_mph = rival_speed
        _remember(
            world.headlines,
            f"{rival.name} reports a {rival_speed:.1f} mph benchmark.",
        )

    for event in HISTORICAL_EVENTS:
        if event.year != campaign.current_year or event.event_id in world.historical_events_seen:
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