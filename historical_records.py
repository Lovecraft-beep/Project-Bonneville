"""Data-backed historical land-speed targets for Career Mode."""

import json
from dataclasses import dataclass
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


def next_historical_target(current_year, completed_record_ids):
    """Return the next sequential record from the historical progression.

    ``current_year`` is retained for compatibility with saved campaign logic;
    a campaign goal is visible even when its historical year is still ahead.
    """
    completed = set(completed_record_ids)
    for target in HISTORICAL_TARGETS:
        if target.record_id not in completed:
            return target
    return None


def target_completed(target, measured_mile_speed_mph):
    """Return whether a measured-mile run matches or beats a target."""
    return measured_mile_speed_mph >= target.speed_mph


def record_ids_achieved_by_speed(measured_mile_speed_mph):
    """Return historical records already beaten by a legacy campaign best."""
    return [
        target.record_id
        for target in HISTORICAL_TARGETS
        if measured_mile_speed_mph >= target.speed_mph
    ]