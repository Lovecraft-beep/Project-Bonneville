"""Chassis definitions for the vehicle designer."""

from dataclasses import dataclass

from research import CHASSIS_TECHNOLOGY_TREE


@dataclass(frozen=True)
class Chassis:
    chassis_id: str
    name: str
    description: str
    mass_kg: float
    drag_coefficient: float
    frontal_area_m2: float
    tyre_grip_factor: float
    wheel_radius_m: float
    cost_gbp: float
    required_technology: str | None = None


# Stat ranges spanning the whole 25-tier lineage, from an 1890s wooden
# carriage to a next-generation composite chassis.
_MASS_KG_RANGE = (2_200.0, 400.0)
_DRAG_COEFFICIENT_RANGE = (0.60, 0.12)
_FRONTAL_AREA_M2_RANGE = (2.8, 1.2)
_TYRE_GRIP_FACTOR_RANGE = (0.55, 0.98)
_WHEEL_RADIUS_M_RANGE = (0.45, 0.33)


def _interpolate(start, end, fraction):
    return start + (end - start) * fraction


def _interpolate_exponential(start, end, fraction):
    return start * (end / start) ** fraction


def _construction_cost_gbp(tier_number):
    """Escalate construction cost across the 25-tier lineage."""
    era_index, tier_index = divmod(tier_number, 5)
    base = 2_000.0 * (1.8 ** era_index)
    return round(base * (1.15 ** tier_index) / 100) * 100


def _build_catalog():
    tier_count = len(CHASSIS_TECHNOLOGY_TREE)
    catalog = [
        Chassis(
            "improvised_chassis",
            "Improvised Chassis",
            "A crude, unresearched frame bolted together from whatever is on hand.",
            mass_kg=_MASS_KG_RANGE[0] * 1.1,
            drag_coefficient=_DRAG_COEFFICIENT_RANGE[0] * 1.1,
            frontal_area_m2=_FRONTAL_AREA_M2_RANGE[0] * 1.05,
            tyre_grip_factor=_TYRE_GRIP_FACTOR_RANGE[0] * 0.9,
            wheel_radius_m=_WHEEL_RADIUS_M_RANGE[0] * 1.05,
            cost_gbp=3_000.0,
        )
    ]
    for tier_number, node in enumerate(CHASSIS_TECHNOLOGY_TREE):
        fraction = tier_number / (tier_count - 1)
        catalog.append(
            Chassis(
                node.technology_id,
                node.name,
                f"A {node.era} chassis technology.",
                mass_kg=round(_interpolate_exponential(*_MASS_KG_RANGE, fraction), 1),
                drag_coefficient=round(
                    _interpolate_exponential(*_DRAG_COEFFICIENT_RANGE, fraction), 3
                ),
                frontal_area_m2=round(
                    _interpolate(*_FRONTAL_AREA_M2_RANGE, fraction), 2
                ),
                tyre_grip_factor=round(
                    _interpolate(*_TYRE_GRIP_FACTOR_RANGE, fraction), 2
                ),
                wheel_radius_m=round(
                    _interpolate(*_WHEEL_RADIUS_M_RANGE, fraction), 2
                ),
                cost_gbp=_construction_cost_gbp(tier_number),
                required_technology=node.technology_id,
            )
        )
    return tuple(catalog)


CHASSIS_CATALOG = _build_catalog()

CHASSIS_BY_ID = {chassis.chassis_id: chassis for chassis in CHASSIS_CATALOG}

# Retired chassis IDs from earlier iterations of the tech tree, kept
# resolvable so vehicles already saved to a garage don't break.
LEGACY_CHASSIS_ALIASES = {
    "lightweight_streamliner": "advanced_edwardian_racing_frame",
    "balanced_racer": "reinforced_ladder_frame",
    "heavy_duty_racer": "heavy_duty_racing_ladder",
    "chassis_steel_rail_1": "carriage_frame",
    "chassis_steel_rail_2": "reinforced_ladder_frame",
    "chassis_steel_rail_3": "heavy_duty_racing_ladder",
    "chassis_spaceframe_1": "pressed_steel_ladder_frame",
    "chassis_spaceframe_2": "advanced_edwardian_racing_frame",
    "chassis_composite_1": "braced_box_section_frame",
    "chassis_composite_2": "underslung_racing_chassis",
}
for legacy_id, replacement_id in LEGACY_CHASSIS_ALIASES.items():
    CHASSIS_BY_ID[legacy_id] = CHASSIS_BY_ID[replacement_id]


def is_chassis_unlocked(chassis, researched_technologies):
    """Return whether a chassis's required technology has been researched."""
    return (
        chassis.required_technology is None
        or chassis.required_technology in researched_technologies
    )


def available_chassis(researched_technologies):
    """Return catalogue chassis unlocked by the given researched technologies."""
    return tuple(
        chassis
        for chassis in CHASSIS_CATALOG
        if is_chassis_unlocked(chassis, researched_technologies)
    )


def select_chassis(researched_technologies=()):
    print("\n=== SELECT CHASSIS ===")
    chassis_choices = available_chassis(researched_technologies)
    for number, chassis in enumerate(chassis_choices, start=1):
        print(f"{number}. {chassis.name} (GBP {chassis.cost_gbp:,.0f})")
        print(f"   {chassis.description}")

    choice = input("Choose a chassis: ").strip()
    try:
        return chassis_choices[int(choice) - 1]
    except (ValueError, IndexError):
        print(f"Invalid choice. Using {chassis_choices[0].name}.")
        return chassis_choices[0]
