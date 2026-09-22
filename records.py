"""Persistent historical run records for Project Bonneville."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

RECORDS_FILE = Path(__file__).with_name("historical_records.json")


@dataclass
class HistoricalRecord:
    recorded_at: str
    campaign_id: str
    car_name: str
    car_year: int | None
    engine_name: str
    gearbox_name: str
    brakes_name: str
    track_name: str
    peak_speed_mph: float
    average_acceleration_g: float
    average_deceleration_g: float
    full_throttle_seconds: float
    measured_mile_speed_mph: float


def create_record(vehicle, track, result, campaign):
    return HistoricalRecord(
        recorded_at=datetime.now().isoformat(timespec="seconds"),
        campaign_id=campaign.campaign_id,
        car_name=vehicle.name,
        car_year=vehicle.model_year,
        engine_name=vehicle.engine.name,
        gearbox_name=vehicle.gearbox.name,
        brakes_name=vehicle.brakes.name,
        track_name=track.name,
        peak_speed_mph=result.peak_speed_mph,
        average_acceleration_g=result.average_acceleration_g,
        average_deceleration_g=result.average_deceleration_g,
        full_throttle_seconds=result.full_throttle_seconds,
        measured_mile_speed_mph=result.measured_mile_speed_mph,
    )


def load_records():
    if not RECORDS_FILE.exists():
        return []
    try:
        return json.loads(RECORDS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_record(record):
    records = load_records()
    records.append(asdict(record))
    RECORDS_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")


def display_records(records, campaign_id, limit=10):
    print("\n=== CAMPAIGN RECORDS ===")
    campaign_records = [
        record for record in records if record.get("campaign_id") == campaign_id
    ]
    if not campaign_records:
        print("No recorded runs yet this campaign.")
        return
    ranked_records = sorted(
        campaign_records,
        key=lambda record: record["measured_mile_speed_mph"],
        reverse=True,
    )
    for number, record in enumerate(ranked_records[:limit], start=1):
        print(
            f"{number}. {record['recorded_at']} | "
            f"{record['car_name']} | {record['track_name']}"
        )
        print(
            f"   Engine: {record['engine_name']} | "
            f"Gearbox: {record['gearbox_name']} | "
            f"Brakes: {record['brakes_name']}"
        )
        print(
            f"   Peak: {record['peak_speed_mph']:.1f} mph | "
            f"Average Accel: {record['average_acceleration_g']:.3f} G | "
            f"Average Decel: {record['average_deceleration_g']:.3f} G | "
            f"Full Throttle: {record['full_throttle_seconds']:.1f} s | "
            f"Measured Mile: {record['measured_mile_speed_mph']:.1f} mph"
        )
