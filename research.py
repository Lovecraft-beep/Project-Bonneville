"""Research and development definitions for Project Bonneville.

Chassis is the primary technology tree: it is the one continuous structural
lineage running through five historical eras, from wooden pioneer carriages
to next-generation composite chassis. Each era contributes five chassis
tiers and a couple of named engine archetypes; each engine tier requires
the previous engine tier plus a matching chassis tier, so structural
capability always gates how much power a car can be built to handle.
Future branches (gearboxes, tyres, aerodynamics, safety) can hang off the
same chassis tiers using this pattern.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TechnologyNode:
    technology_id: str
    name: str
    era: str
    prerequisites: tuple[str, ...] = ()
    cost_gbp: float = 5_000.0
    engineers_required: int = 1


@dataclass(frozen=True)
class Era:
    name: str
    year_start: int
    year_end: int | None
    theme: str
    technology_themes: tuple[str, ...] = ()
    challenges: tuple[str, ...] = ()

    @property
    def year_range_label(self):
        return (
            f"{self.year_start}-{self.year_end}"
            if self.year_end
            else f"{self.year_start}+"
        )


def _slugify(name):
    return "_".join(name.replace("-", " ").lower().split())


def _tier_cost_gbp(era_index, tier_index):
    """Escalate research cost by era (doubling) and by tier within an era."""
    base = 5_000.0 * (2**era_index)
    return round(base * (1.25**tier_index) / 500) * 500


def _tier_engineers_required(era_index, tier_index):
    return min(6, 1 + era_index + tier_index // 2)


# Five eras of land-speed-record history. Each contributes five ascending
# chassis tiers and five ascending engine tiers.
ERA_DEFINITIONS = (
    {
        "name": "Pioneers",
        "year_start": 1895,
        "year_end": 1914,
        "theme": "The birth of high-speed motoring.",
        "technology_themes": (
            "Mechanical ignition",
            "Carburettors",
            "Chain drive",
            "Primitive brakes",
            "Wooden wheels",
            "Early pneumatic tyres",
        ),
        "challenges": (
            "Frequent breakdowns",
            "Dangerous handling",
            "Poor roads",
            "Limited materials science",
            "High driver mortality",
        ),
        "chassis_tiers": (
            "Carriage Frame",
            "Reinforced Ladder Frame",
            "Heavy-Duty Racing Ladder",
            "Pressed-Steel Ladder Frame",
            "Advanced Edwardian Racing Frame",
        ),
        "engine_tiers": (
            "Pioneer Engines",
            "Edwardian Giants",
        ),
    },
    {
        "name": "The Interwar Years",
        "year_start": 1915,
        "year_end": 1939,
        "theme": "Aviation engineering and streamlining transform the record car.",
        "technology_themes": (
            "Supercharging",
            "Aluminium pistons",
            "Fuel injection prototypes",
            "Aircraft engine conversions",
            "Streamlined bodywork",
            "Hydraulic brakes",
        ),
        "challenges": (
            "Tyre technology limits",
            "Aerodynamic instability at high speed",
            "Engine overheating",
            "Inconsistent fuel quality",
            "Depression-era funding pressure",
        ),
        "chassis_tiers": (
            "Braced Box-Section Frame",
            "Underslung Racing Chassis",
            "Twin-Rail Streamliner Frame",
            "Riveted Aircraft-Alloy Frame",
            "Full-Envelope Streamliner Chassis",
        ),
        "engine_tiers": (
            "Aircraft Conversions",
            "Supercharged Aero Engines",
        ),
    },
    {
        "name": "The Jet Age",
        "year_start": 1940,
        "year_end": 1969,
        "theme": "Turbojet and rocket propulsion redefine the record.",
        "technology_themes": (
            "Turbojet propulsion",
            "Parachute braking",
            "Radio telemetry",
            "Heat-resistant materials",
            "Multi-wheel stability",
            "Rocket assist",
        ),
        "challenges": (
            "Sonic shockwaves",
            "Tyre failure at extreme speed",
            "Track length limitations",
            "Extreme heat management",
            "Pilot safety at supersonic speed",
        ),
        "chassis_tiers": (
            "Riveted Aluminium Monocoque",
            "Multi-Wheel Stabilised Frame",
            "Jet-Intake Structural Frame",
            "Rocket-Ready Reinforced Frame",
            "Supersonic Stability Frame",
        ),
        "engine_tiers": (
            "Specialised LSR Engines",
            "Gas Turbines",
        ),
    },
    {
        "name": "The Professional Era",
        "year_start": 1970,
        "year_end": 1999,
        "theme": "Dedicated teams and computer-aided design push into pure rocket power.",
        "technology_themes": (
            "Computer-aided design",
            "Carbon fibre composites",
            "Digital telemetry",
            "Advanced airbrake and parachute systems",
            "Staged rocket propulsion",
            "Wind tunnel testing",
        ),
        "challenges": (
            "Supersonic shockwave management",
            "Precision navigation",
            "Track surface certification",
            "Extreme project cost",
            "Catastrophic failure risk",
        ),
        "chassis_tiers": (
            "Tubular Steel Spaceframe",
            "Computer-Optimised Spaceframe",
            "Composite-Panelled Spaceframe",
            "Carbon-Kevlar Monocoque",
            "Advanced Aerospace Composite Chassis",
        ),
        "engine_tiers": (
            "Turbojets",
            "Afterburning Turbojets",
        ),
    },
    {
        "name": "Modern and Future Speed",
        "year_start": 2000,
        "year_end": None,
        "theme": "Electric, hybrid, and exotic propulsion push into uncharted territory.",
        "technology_themes": (
            "Electric powertrains",
            "Active aerodynamics",
            "Data-driven engineering",
            "Autonomous safety systems",
            "Sustainable fuels",
            "Smart materials",
        ),
        "challenges": (
            "Battery energy density",
            "Thermal management at extreme speed",
            "Regulatory certification",
            "Environmental considerations",
            "Public safety scrutiny",
        ),
        "chassis_tiers": (
            "Full Carbon-Fibre Monocoque",
            "Active-Aero Composite Chassis",
            "Hybrid-Structural Battery Chassis",
            "Adaptive Smart-Material Chassis",
            "Next-Generation Autonomous Speed Chassis",
        ),
        "engine_tiers": (
            "Rocket Propulsion",
            "Modern Turbofans",
        ),
    },
)


def _build_trees(era_definitions):
    """Build the chassis and engine trees from the era definitions.

    Chassis tiers form one continuous chain of five tiers per era (each
    requires the previous tier, regardless of era). Engine tiers form a
    shorter parallel chain per era; each engine tier requires the previous
    engine tier plus whichever chassis tier in the same era is at the same
    relative position (e.g. the first engine tier needs the era's first
    chassis tier, the last engine tier needs the era's last chassis tier).
    """
    eras = []
    chassis_tree = []
    engine_tree = []
    previous_chassis_id = None
    previous_engine_id = None

    for era_index, definition in enumerate(era_definitions):
        era = Era(
            name=definition["name"],
            year_start=definition["year_start"],
            year_end=definition["year_end"],
            theme=definition["theme"],
            technology_themes=definition["technology_themes"],
            challenges=definition["challenges"],
        )
        eras.append(era)

        era_chassis_ids = []
        for tier_index in range(5):
            cost_gbp = _tier_cost_gbp(era_index, tier_index)
            engineers_required = _tier_engineers_required(era_index, tier_index)

            chassis_name = definition["chassis_tiers"][tier_index]
            chassis_id = _slugify(chassis_name)
            chassis_prerequisites = (
                (previous_chassis_id,) if previous_chassis_id else ()
            )
            chassis_tree.append(
                TechnologyNode(
                    chassis_id,
                    chassis_name,
                    era.name,
                    chassis_prerequisites,
                    cost_gbp,
                    engineers_required,
                )
            )
            previous_chassis_id = chassis_id
            era_chassis_ids.append(chassis_id)

        engine_tiers = definition["engine_tiers"]
        for engine_tier_index, engine_name in enumerate(engine_tiers):
            if len(engine_tiers) > 1:
                chassis_index = round(
                    engine_tier_index
                    * (len(era_chassis_ids) - 1)
                    / (len(engine_tiers) - 1)
                )
            else:
                chassis_index = 0
            required_chassis_id = era_chassis_ids[chassis_index]
            cost_gbp = _tier_cost_gbp(era_index, chassis_index)
            engineers_required = _tier_engineers_required(era_index, chassis_index)

            engine_id = _slugify(engine_name)
            engine_prerequisites = tuple(
                prerequisite
                for prerequisite in (previous_engine_id, required_chassis_id)
                if prerequisite
            )
            engine_tree.append(
                TechnologyNode(
                    engine_id,
                    engine_name,
                    era.name,
                    engine_prerequisites,
                    cost_gbp,
                    engineers_required,
                )
            )
            previous_engine_id = engine_id

    return tuple(chassis_tree), tuple(engine_tree), tuple(eras)


def _build_branch_tree(era_definitions, branch_key):
    """Build a branch whose tiers are anchored to the matching chassis era."""
    branch_tree = []
    previous_id = None

    for era_index, definition in enumerate(era_definitions):
        era_chassis_ids = [_slugify(name) for name in definition["chassis_tiers"]]
        tier_names = definition[branch_key]
        for tier_index, technology_name in enumerate(tier_names):
            chassis_index = (
                round(tier_index * (len(era_chassis_ids) - 1) / (len(tier_names) - 1))
                if len(tier_names) > 1
                else 0
            )
            prerequisites = tuple(
                prerequisite
                for prerequisite in (previous_id, era_chassis_ids[chassis_index])
                if prerequisite
            )
            technology_id = _slugify(technology_name)
            if era_index:
                technology_id = f"{technology_id}_{era_index}"
            branch_tree.append(
                TechnologyNode(
                    technology_id,
                    technology_name,
                    definition["name"],
                    prerequisites,
                    _tier_cost_gbp(era_index, chassis_index),
                    _tier_engineers_required(era_index, chassis_index),
                )
            )
            previous_id = technology_id

    return tuple(branch_tree)


for _definition in ERA_DEFINITIONS:
    _definition["aerodynamics_tiers"] = (
        "Basic Streamlining",
        "Racing Streamlining",
        "Advanced Aerodynamics",
    )
    _definition["tyre_tiers"] = (
        "Pneumatic Racing Tyres",
        "High-Speed Tyres",
        "Specialised Record Tyres",
    )
    _definition["brake_tiers"] = (
        "Mechanical Drum Brakes",
        "Hydraulic Disc Brakes",
        "High-Temperature Brakes",
    )


CHASSIS_TECHNOLOGY_TREE, ENGINE_TECHNOLOGY_TREE, ERAS = _build_trees(ERA_DEFINITIONS)
AERODYNAMICS_TECHNOLOGY_TREE = _build_branch_tree(ERA_DEFINITIONS, "aerodynamics_tiers")
TYRE_TECHNOLOGY_TREE = _build_branch_tree(ERA_DEFINITIONS, "tyre_tiers")
BRAKE_TECHNOLOGY_TREE = _build_branch_tree(ERA_DEFINITIONS, "brake_tiers")
GEARBOX_TECHNOLOGY_TREE = (
    TechnologyNode(
        "computer_optimised_gear_ratios",
        "Computer-Optimised Gear Ratios",
        "The Professional Era",
        ("computer_optimised_spaceframe",),
        35_000.0,
        4,
    ),
)

CHASSIS_TECHNOLOGY_BY_ID = {
    node.technology_id: node for node in CHASSIS_TECHNOLOGY_TREE
}
ENGINE_TECHNOLOGY_BY_ID = {node.technology_id: node for node in ENGINE_TECHNOLOGY_TREE}
AERODYNAMICS_TECHNOLOGY_BY_ID = {
    node.technology_id: node for node in AERODYNAMICS_TECHNOLOGY_TREE
}
TYRE_TECHNOLOGY_BY_ID = {node.technology_id: node for node in TYRE_TECHNOLOGY_TREE}
BRAKE_TECHNOLOGY_BY_ID = {node.technology_id: node for node in BRAKE_TECHNOLOGY_TREE}
GEARBOX_TECHNOLOGY_BY_ID = {
    node.technology_id: node for node in GEARBOX_TECHNOLOGY_TREE
}
ERA_BY_NAME = {era.name: era for era in ERAS}
ERA_ORDER = tuple(era.name for era in ERAS)


def era_technologies(tree, era):
    """Return all technology nodes in the given tree belonging to an era."""
    return tuple(node for node in tree if node.era == era)


def is_era_complete(tree, era, researched):
    """Return whether every technology in an era has been researched."""
    researched_ids = set(researched)
    return all(
        node.technology_id in researched_ids for node in era_technologies(tree, era)
    )


def unlocked_eras(tree, researched):
    """Return eras open for research, stopping after the first incomplete era."""
    unlocked = []
    for era in ERA_ORDER:
        unlocked.append(era)
        if not is_era_complete(tree, era, researched):
            break
    return tuple(unlocked)


def current_era(tree, researched):
    """Return the earliest era in the tree that is not yet fully researched."""
    for era in ERA_ORDER:
        if not is_era_complete(tree, era, researched):
            return era
    return ERA_ORDER[-1]


def available_chassis_technologies(researched):
    """Return chassis technologies whose prerequisites and era are unlocked.

    Chassis is the primary tree: it alone uses era-completion gating, since
    it is the game's single progression clock.
    """
    researched_ids = set(researched)
    open_eras = set(unlocked_eras(CHASSIS_TECHNOLOGY_TREE, researched_ids))
    return tuple(
        node
        for node in CHASSIS_TECHNOLOGY_TREE
        if node.technology_id not in researched_ids
        and node.era in open_eras
        and set(node.prerequisites).issubset(researched_ids)
    )


def current_chassis_era(researched):
    return current_era(CHASSIS_TECHNOLOGY_TREE, researched)


def available_engine_technologies(engine_researched, chassis_researched):
    """Return engine technologies unlocked by engine and chassis progress.

    Unlike the chassis tree, engine technologies have no era gate of their
    own: they open purely once their prerequisites (which reference the
    previous engine tier and the matching chassis tier) have been researched.
    """
    all_researched = set(engine_researched) | set(chassis_researched)
    return tuple(
        node
        for node in ENGINE_TECHNOLOGY_TREE
        if node.technology_id not in engine_researched
        and set(node.prerequisites).issubset(all_researched)
    )


def available_branch_technologies(tree, branch_researched, chassis_researched):
    """Return branch technologies unlocked by their branch and chassis anchors."""
    all_researched = set(branch_researched) | set(chassis_researched)
    return tuple(
        node
        for node in tree
        if node.technology_id not in branch_researched
        and set(node.prerequisites).issubset(all_researched)
    )


def available_aerodynamics_technologies(aerodynamics_researched, chassis_researched):
    return available_branch_technologies(
        AERODYNAMICS_TECHNOLOGY_TREE,
        aerodynamics_researched,
        chassis_researched,
    )


def available_tyre_technologies(tyre_researched, chassis_researched):
    return available_branch_technologies(
        TYRE_TECHNOLOGY_TREE, tyre_researched, chassis_researched
    )


def available_brake_technologies(brake_researched, chassis_researched):
    return available_branch_technologies(
        BRAKE_TECHNOLOGY_TREE, brake_researched, chassis_researched
    )
