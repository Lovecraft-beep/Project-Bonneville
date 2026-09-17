"""Reliability and trackside failure resolution for test runs."""

import random
from dataclasses import dataclass


MIN_SPEED_FACTOR = 0.25
REFERENCE_SPEED_MPH = 250.0
MIN_TEAM_SKILL_MODIFIER = 0.5
REQUIRED_ENGINEERS_FOR_REPAIR = 1
REQUIRED_MECHANICS_FOR_REPAIR = 2


@dataclass(frozen=True)
class FailureType:
    failure_id: str
    name: str


MISFIRE = FailureType("misfire", "Misfire")
OIL_LEAK = FailureType("oil_leak", "Oil leak")
GEAR_FAILURE = FailureType("gear_failure", "Gear failure")
TYRE_BURST = FailureType("tyre_burst", "Tyre burst")
BRAKE_FADE = FailureType("brake_fade", "Brake fade")
STEERING_VIBRATION = FailureType("steering_vibration", "Steering vibration")


@dataclass(frozen=True)
class RunOutcome:
    failure_probability: float
    failed: bool
    repaired: bool
    failure_type: FailureType | None = None

    @property
    def successful(self):
        return not self.failed


def calculate_speed_factor(peak_speed_mph):
    """Scale reliability risk with speed while keeping a minimum exposure."""
    return max(MIN_SPEED_FACTOR, peak_speed_mph / REFERENCE_SPEED_MPH)


def calculate_team_skill_modifier(team, sponsor_reliability_bonus=0.0):
    """Reduce failure risk as engineers, mechanics, and sponsors are added."""
    staff_skill = 0.08 * team.engineers + 0.04 * team.mechanics + sponsor_reliability_bonus
    return max(MIN_TEAM_SKILL_MODIFIER, 1.0 - staff_skill)


def calculate_failure_probability(engine, peak_speed_mph, team, sponsor_reliability_bonus=0.0):
    """Return the engine failure probability for a completed simulation."""
    speed_factor = calculate_speed_factor(peak_speed_mph)
    team_skill_modifier = calculate_team_skill_modifier(team, sponsor_reliability_bonus)
    return min(
        1.0,
        max(
            0.0,
            (1.0 - engine.reliability)
            * speed_factor
            * team_skill_modifier,
        ),
    )


def can_repair_trackside(team):
    """Return whether the team can repair a failure at the track."""
    return (
        team.engineers >= REQUIRED_ENGINEERS_FOR_REPAIR
        and team.mechanics >= REQUIRED_MECHANICS_FOR_REPAIR
    )


def resolve_run_failure(
    engine,
    peak_speed_mph,
    team,
    random_value=None,
    gearbox=None,
    brake_fade=False,
    sponsor_reliability_bonus=0.0,
):
    """Resolve a named failure and whether the team can repair it trackside."""
    engine_failure_probability = calculate_failure_probability(
        engine,
        peak_speed_mph,
        team,
        sponsor_reliability_bonus,
    )
    speed_factor = calculate_speed_factor(peak_speed_mph)
    team_skill_modifier = calculate_team_skill_modifier(team, sponsor_reliability_bonus)
    failure_events = [
        (MISFIRE, engine_failure_probability * 0.45),
        (OIL_LEAK, engine_failure_probability * 0.25),
        (
            GEAR_FAILURE,
            (1.0 - gearbox.reliability) * speed_factor * team_skill_modifier
            if gearbox is not None
            else 0.0,
        ),
        (TYRE_BURST, 0.02 * speed_factor * team_skill_modifier),
        (
            BRAKE_FADE,
            (0.20 if brake_fade else 0.01)
            * speed_factor
            * team_skill_modifier,
        ),
        (STEERING_VIBRATION, 0.015 * speed_factor * team_skill_modifier),
    ]
    failure_probability = min(1.0, sum(probability for _, probability in failure_events))
    sample = random.random() if random_value is None else random_value
    failed = sample < failure_probability
    failure_type = None
    if failed:
        event_sample = sample / failure_probability
        cumulative_probability = 0.0
        for candidate, probability in failure_events:
            cumulative_probability += probability / failure_probability
            if event_sample < cumulative_probability:
                failure_type = candidate
                break
    repaired = failed and can_repair_trackside(team)
    return RunOutcome(failure_probability, failed, repaired, failure_type)