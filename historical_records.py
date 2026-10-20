"""Data-backed historical land-speed targets for Career Mode."""

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


RECORDS_FILE = Path(__file__).with_name("major_historical_land_speed_records.json")


@dataclass(frozen=True)
class HistoricalTarget:
    record_id: str
    date: str
    era: int
    driver: str
    vehicle: str
    location: str
    propulsion: str
    record_basis: str
    speed_mph: float
    speed_kph: float
    milestone: str

    @property
    def year(self):
        return int(self.date[:4])


def load_historical_targets(path=RECORDS_FILE):
    """Load the curated historical progression from its JSON data file."""
    with path.open("r", encoding="utf-8") as records_file:
        data = json.load(records_file)
    return tuple(HistoricalTarget(**record) for record in data["records"])


HISTORICAL_TARGETS = load_historical_targets()


def next_historical_target(current_year, completed_record_ids, current_day_of_year=None):
    """Return the standing record, or the next faster uncompleted record.

    When a campaign day is supplied, only records reached by that date count as
    the standing mark. The next goal remains visible even if it is still ahead.
    """
    completed = set(completed_record_ids)
    if current_day_of_year is None:
        standing = current_world_record(current_year)
    else:
        campaign_date = date(current_year, 1, 1) + timedelta(
            days=current_day_of_year - 1
        )
        standing = max(
            (
                target
                for target in HISTORICAL_TARGETS
                if target.date <= campaign_date.isoformat()
            ),
            key=lambda target: target.speed_mph,
            default=None,
        )
    if standing and standing.record_id not in completed:
        return standing

    for target in HISTORICAL_TARGETS:
        if (
            target.record_id not in completed
            and (standing is None or target.speed_mph > standing.speed_mph)
        ):
            return target
    return None


def current_world_record(year):
    """Return the fastest historical record set on or before the given year."""
    standing = [target for target in HISTORICAL_TARGETS if target.year <= year]
    return max(standing, key=lambda target: target.speed_mph, default=None)


def required_record_runs(year):
    """Return the official pass count under the rules effective that year."""
    return 1 if year <= 1923 else 2


def average_record_speed(speeds_mph):
    """Return the arithmetic mean speed for a completed record attempt."""
    if not speeds_mph:
        raise ValueError("a record attempt needs at least one measured pass")
    return sum(speeds_mph) / len(speeds_mph)


def target_completed(target, measured_mile_speed_mph):
    """Return whether a measured-mile run matches or beats a target."""
    if getattr(target, "record_id", None) == "inaugural_record":
        return measured_mile_speed_mph > 0
    return measured_mile_speed_mph >= target.speed_mph


def record_ids_achieved_by_speed(measured_mile_speed_mph):
    """Return historical records already beaten by a legacy campaign best."""
    return [
        target.record_id
        for target in HISTORICAL_TARGETS
        if measured_mile_speed_mph >= target.speed_mph
    ]