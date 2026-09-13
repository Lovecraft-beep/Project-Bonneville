"""Historically inspired engine definitions for Project Bonneville."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Engine:
    name: str
    power_hp: float
    torque_nm: float
    max_rpm: int
    mass_kg: float
    reliability: float
    configuration: str = ""
    displacement_litres: float | None = None
    era: str = ""


NAPIER_LION_VIIA = Engine(
    name="Napier Lion VIIA",
    power_hp=900.0,
    torque_nm=1_900.0,
    max_rpm=2_800,
    mass_kg=430.0,
    reliability=0.85,
    configuration="24-litre W12",
    displacement_litres=23.9,
    era="1920s",
)


AVAILABLE_ENGINES = {
    NAPIER_LION_VIIA.name: NAPIER_LION_VIIA,
}