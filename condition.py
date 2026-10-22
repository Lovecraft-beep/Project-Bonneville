"""Persistent vehicle wear and speed-sensitive incident damage rules."""

from dataclasses import dataclass


def condition_state(wear, damage):
    if damage >= 100:
        return "Destroyed"
    if damage >= 60:
        return "Heavily Damaged"
    if damage > 0:
        return "Damaged"
    return "Worn" if wear >= 10 else "Pristine"


def condition_performance_factor(wear, damage):
    return max(0.5, 1.0 - wear * 0.0005 - damage * 0.002)


def condition_failure_multiplier(wear, damage):
    return 1.0 + wear / 200.0 + damage / 100.0


@dataclass(frozen=True)
class IncidentDamage:
    damage: float
    description: str


def assess_incident_damage(failure_type, speed_mph):
    severity = {
        "misfire": (0.0, 0.0),
        "oil_leak": (2.0, 8.0),
        "gear_failure": (8.0, 42.0),
        "tyre_burst": (15.0, 85.0),
        "brake_fade": (5.0, 65.0),
        "steering_vibration": (3.0, 60.0),
        "wheel_lock": (12.0, 90.0),
    }
    base, speed_damage = severity[failure_type.failure_id]
    damage = round(min(100.0, base + speed_damage * (max(0.0, speed_mph) / 400.0) ** 2), 2)
    return IncidentDamage(
        damage,
        f"{failure_type.name} at assessed speed {speed_mph:.1f} mph (run peak): +{damage:.1f} damage",
    )