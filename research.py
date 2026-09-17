"""Research and development definitions for Project Bonneville."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TechnologyNode:
    technology_id: str
    name: str
    era: str
    prerequisites: tuple[str, ...] = ()
    cost_gbp: float = 5_000.0
    engineers_required: int = 1


ENGINE_TECHNOLOGY_TREE = (
    TechnologyNode("basic_engines", "Basic Engines", "Basic Engines", cost_gbp=5_000.0),
    TechnologyNode(
        "multi_cylinder",
        "Multi Cylinder",
        "Basic Engines",
        ("basic_engines",),
        cost_gbp=8_000.0,
    ),
    TechnologyNode(
        "aluminium_pistons",
        "Aluminium Pistons",
        "Basic Engines",
        ("basic_engines",),
        cost_gbp=8_000.0,
    ),
    TechnologyNode(
        "supercharging",
        "Supercharging",
        "Basic Engines",
        ("basic_engines",),
        cost_gbp=10_000.0,
        engineers_required=2,
    ),
    TechnologyNode(
        "fuel_injection",
        "Fuel Injection",
        "Basic Engines",
        ("basic_engines",),
        cost_gbp=10_000.0,
        engineers_required=2,
    ),
    TechnologyNode(
        "aircraft_engine_conversion",
        "Aircraft Engine Conversion",
        "Basic Engines",
        ("basic_engines",),
        cost_gbp=15_000.0,
        engineers_required=2,
    ),
)

ENGINE_TECHNOLOGY_BY_ID = {
    node.technology_id: node for node in ENGINE_TECHNOLOGY_TREE
}


def available_engine_technologies(researched):
    """Return technologies whose prerequisites have been researched."""
    researched_ids = set(researched)
    return tuple(
        node
        for node in ENGINE_TECHNOLOGY_TREE
        if node.technology_id not in researched_ids
        and set(node.prerequisites).issubset(researched_ids)
    )