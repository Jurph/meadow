"""Immutable renderer/save snapshot for the Meadow simulation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import cast

from meadow.hex import HexCell, surface
from meadow.plant import PlantPopulation, TraitBundle
from meadow.world import SIM_API_VERSION
from meadow.world_state import WorldState

SNAPSHOT_SCHEMA_VERSION = 1


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
    cellulose_per_segment: float

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
            cellulose_per_segment=traits.cellulose_per_segment,
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
class PlantSnapshot:
    id: int
    home: CellAddress | None
    moisture_reserve: float
    nutrient_reserve: float
    cellulose: float
    traits: TraitSnapshot
    segments: tuple[SegmentSnapshot, ...]


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
        graph = body.graph if body is not None else None
        segments: tuple[SegmentSnapshot, ...] = ()
        if graph is not None:
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
                for segment in sorted(graph.segments.values(), key=lambda item: item.id)
            )
        plants.append(
            PlantSnapshot(
                id=plant.id,
                home=_cell_address(body.home) if body is not None else None,
                moisture_reserve=plant.moisture_reserve,
                nutrient_reserve=plant.nutrient_reserve,
                cellulose=plant.cellulose,
                traits=TraitSnapshot.from_bundle(plant.traits),
                segments=segments,
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
