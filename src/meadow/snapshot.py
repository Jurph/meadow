"""Immutable renderer/save snapshot for the Meadow simulation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import cast

from meadow.hex import HexCell, surface
from meadow.plant import PlantPopulation, TraitBundle
from meadow.resources import (
    AssimilateAllocation,
    PlantBalanceSheet,
    ResourceFlux,
    ResourceVector,
)
from meadow.world import SIM_API_VERSION
from meadow.world_state import WorldState

SNAPSHOT_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class CellAddress:
    q: int
    r: int
    z: int


@dataclass(frozen=True)
class WorldShape:
    width: int
    height: int
    min_z: int
    max_z: int


@dataclass(frozen=True)
class TileSnapshot:
    q: int
    r: int
    moisture: float
    nutrients: float
    light: float
    drainage: float
    slope_q: float
    slope_r: float
    occupant_id: int | None


@dataclass(frozen=True)
class ResourceSnapshot:
    water: float
    minerals: float
    assimilate: float

    @classmethod
    def from_vector(cls, resources: ResourceVector) -> ResourceSnapshot:
        return cls(
            water=resources.water,
            minerals=resources.minerals,
            assimilate=resources.assimilate,
        )


@dataclass(frozen=True)
class AssimilateAllocationSnapshot:
    root: float
    leaf: float
    stem: float
    reproduce: float

    @classmethod
    def from_model(
        cls,
        allocation: AssimilateAllocation,
    ) -> AssimilateAllocationSnapshot:
        return cls(
            root=allocation.root,
            leaf=allocation.leaf,
            stem=allocation.stem,
            reproduce=allocation.reproduce,
        )


@dataclass(frozen=True)
class ResourceFluxSnapshot:
    potential: ResourceSnapshot
    actual: ResourceSnapshot
    limiting_factors: tuple[str, ...]

    @classmethod
    def from_flux(cls, flux: ResourceFlux) -> ResourceFluxSnapshot:
        return cls(
            potential=ResourceSnapshot.from_vector(flux.potential),
            actual=ResourceSnapshot.from_vector(flux.actual),
            limiting_factors=tuple(sorted(flux.limiting_factors)),
        )


@dataclass(frozen=True)
class OrganCountSnapshot:
    organ_type: str
    count: int


@dataclass(frozen=True)
class PlantBalanceSheetSnapshot:
    tick: int
    opening: ResourceSnapshot
    root_uptake: ResourceFluxSnapshot
    photosynthesis: ResourceFluxSnapshot
    photosynthesis_water: float
    construction_potential: ResourceSnapshot
    organ_proposals: tuple[OrganCountSnapshot, ...]
    construction: ResourceSnapshot
    organs_constructed: tuple[OrganCountSnapshot, ...]
    construction_limiting_factors: tuple[str, ...]
    closing: ResourceSnapshot

    @classmethod
    def from_balance_sheet(
        cls,
        balance_sheet: PlantBalanceSheet,
    ) -> PlantBalanceSheetSnapshot:
        return cls(
            tick=balance_sheet.tick,
            opening=ResourceSnapshot.from_vector(balance_sheet.opening),
            root_uptake=ResourceFluxSnapshot.from_flux(balance_sheet.root_uptake),
            photosynthesis=ResourceFluxSnapshot.from_flux(balance_sheet.photosynthesis),
            photosynthesis_water=balance_sheet.photosynthesis_water,
            construction_potential=ResourceSnapshot.from_vector(
                balance_sheet.construction_potential
            ),
            organ_proposals=tuple(
                OrganCountSnapshot(organ_type=organ_type, count=count)
                for organ_type, count in sorted(balance_sheet.organ_proposals.items())
            ),
            construction=ResourceSnapshot.from_vector(balance_sheet.construction),
            organs_constructed=tuple(
                OrganCountSnapshot(organ_type=organ_type, count=count)
                for organ_type, count in sorted(balance_sheet.organs_constructed.items())
            ),
            construction_limiting_factors=tuple(
                sorted(balance_sheet.construction_limiting_factors)
            ),
            closing=ResourceSnapshot.from_vector(balance_sheet.closing),
        )


@dataclass(frozen=True)
class TraitSnapshot:
    number_of_lobes: float
    lobe_aspect_ratio: float
    lobe_length: float
    root_reach: float
    alloc_root: float
    alloc_leaf: float
    alloc_stem: float
    alloc_reproduce: float
    basal_length: float
    branch_spacing: float
    apical_length: float
    max_root_length: float
    branch_probability: float
    gravitropism_weight: float
    hydrotropism_weight: float
    gsa_root: float
    root_construction_cost: ResourceSnapshot
    stem_construction_cost: ResourceSnapshot
    leaf_construction_cost: ResourceSnapshot

    @classmethod
    def from_bundle(cls, traits: TraitBundle) -> TraitSnapshot:
        return cls(
            number_of_lobes=traits.number_of_lobes,
            lobe_aspect_ratio=traits.lobe_aspect_ratio,
            lobe_length=traits.lobe_length,
            root_reach=traits.root_reach,
            alloc_root=traits.alloc_root,
            alloc_leaf=traits.alloc_leaf,
            alloc_stem=traits.alloc_stem,
            alloc_reproduce=traits.alloc_reproduce,
            basal_length=traits.basal_length,
            branch_spacing=traits.branch_spacing,
            apical_length=traits.apical_length,
            max_root_length=traits.max_root_length,
            branch_probability=traits.branch_probability,
            gravitropism_weight=traits.gravitropism_weight,
            hydrotropism_weight=traits.hydrotropism_weight,
            gsa_root=traits.gsa_root,
            root_construction_cost=ResourceSnapshot.from_vector(traits.root_construction_cost),
            stem_construction_cost=ResourceSnapshot.from_vector(traits.stem_construction_cost),
            leaf_construction_cost=ResourceSnapshot.from_vector(traits.leaf_construction_cost),
        )


@dataclass(frozen=True)
class SegmentSnapshot:
    id: int
    parent_id: int | None
    segment_type: str
    start: CellAddress
    end: CellAddress
    diameter: float
    order: int
    accumulated_length: float


@dataclass(frozen=True)
class LeafSnapshot:
    id: int
    attachment_segment_id: int | None
    cell: CellAddress
    area: float
    health: float


@dataclass(frozen=True)
class PlantSnapshot:
    id: int
    home: CellAddress | None
    resources: ResourceSnapshot
    assimilate_allocation: AssimilateAllocationSnapshot
    balance_sheet: PlantBalanceSheetSnapshot | None
    traits: TraitSnapshot
    segments: tuple[SegmentSnapshot, ...]
    leaves: tuple[LeafSnapshot, ...]


@dataclass(frozen=True)
class WorldSnapshot:
    schema_version: int
    sim_api_version: int
    tick: int
    world: WorldShape
    tiles: tuple[TileSnapshot, ...]
    plants: tuple[PlantSnapshot, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible deep copy of this immutable snapshot."""
        return cast(dict[str, object], asdict(self))

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize deterministically for renderers, saves, and replays."""
        return json.dumps(
            self.to_dict(),
            allow_nan=False,
            indent=indent,
            sort_keys=True,
        )


def _cell_address(cell: HexCell) -> CellAddress:
    return CellAddress(q=cell.q, r=cell.r, z=cell.z)


def build_world_snapshot(
    *, tick: int, world: WorldState, population: PlantPopulation
) -> WorldSnapshot:
    """Copy mutable simulation state into the immutable snapshot contract."""
    grid = world.grid
    tiles: list[TileSnapshot] = []
    for column in grid:
        index = column.q * grid.height + column.r
        cell = surface(column)
        tiles.append(
            TileSnapshot(
                q=column.q,
                r=column.r,
                moisture=world.moisture_at(cell),
                nutrients=world.nutrients_at(cell),
                light=world.light_at(cell),
                drainage=float(world.drainage[index]),
                slope_q=float(world.slope_q[index]),
                slope_r=float(world.slope_r[index]),
                occupant_id=world.occupant_id_at(column),
            )
        )

    plants: list[PlantSnapshot] = []
    for plant in population:
        body = plant.body
        segments: tuple[SegmentSnapshot, ...] = ()
        leaves: tuple[LeafSnapshot, ...] = ()
        if body is not None:
            segments = tuple(
                SegmentSnapshot(
                    id=segment.id,
                    parent_id=segment.parent_id,
                    segment_type=segment.segment_type.name,
                    start=_cell_address(segment.start),
                    end=_cell_address(segment.end),
                    diameter=segment.diameter,
                    order=segment.order,
                    accumulated_length=segment.accumulated_length,
                )
                for segment in sorted(
                    body.graph.segments.values(),
                    key=lambda item: item.id,
                )
            )
            leaves = tuple(
                LeafSnapshot(
                    id=leaf.id,
                    attachment_segment_id=leaf.attachment_segment_id,
                    cell=_cell_address(leaf.cell),
                    area=leaf.area,
                    health=leaf.health,
                )
                for leaf in sorted(
                    body.graph.leaves.values(),
                    key=lambda item: item.id,
                )
            )
        plants.append(
            PlantSnapshot(
                id=plant.id,
                home=_cell_address(body.home) if body is not None else None,
                resources=ResourceSnapshot.from_vector(plant.reserves.snapshot()),
                assimilate_allocation=AssimilateAllocationSnapshot.from_model(
                    plant.assimilate_allocation
                ),
                balance_sheet=(
                    PlantBalanceSheetSnapshot.from_balance_sheet(plant.balance_sheet)
                    if plant.balance_sheet is not None
                    else None
                ),
                traits=TraitSnapshot.from_bundle(plant.traits),
                segments=segments,
                leaves=leaves,
            )
        )

    return WorldSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        sim_api_version=SIM_API_VERSION,
        tick=tick,
        world=WorldShape(
            width=grid.width,
            height=grid.height,
            min_z=grid.min_z,
            max_z=grid.max_z,
        ),
        tiles=tuple(tiles),
        plants=tuple(plants),
    )
