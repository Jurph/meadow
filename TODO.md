# TODO

`meadow` is scaffolding right now. This file is the working note for the next developers who show
up and need to understand where the project is headed.

## Vision

Build a plant-evolution terrarium on a hex grid.

The current mental model:
- plants are the main agents
- the environment exists to wash over them with pressure
- success at gathering resources should let plants grow, reproduce, and shift their lineage traits
- mutations should move trait ranges instead of only flipping binary flags

## Current simulation picture

- one plant is anchored in each hex in the early revisions
- plants can extend roots into neighboring hexes and compete there for water and nutrients
- each plant gets light in its own hex, modified by the height of nearby plants
- reproduction should happen automatically once a plant crosses the right threshold
- dead plants should return nutrients to the soil over time through a decay state or ghost layer

## World pressures we expect to model

- global or mostly-global changes in light, water, and nutrient availability
- terrain slope so rain events move water downhill
- prevailing winds as part of how stress distributes across the meadow
- nutrient injections from decay, waste, spoor, or carcass-like events

## UI direction

- Panda3D is the chosen rendering stack
- the long-term view is 3D, not flat 2D
- the world should read like a tilted or isometric hillside with plants growing upward
- development builds should expose a debug-heavy inspector before we simplify it later

## First useful implementation steps

- replace the placeholder CLI with a Panda3D app bootstrap
- decide how the hex world, plant agents, and decay layer are represented in code
- define the first environmental controls and how they map to simulation state
- get a basic hillside scene on screen before chasing visual polish
- keep the first plant model primitive if needed; correctness beats beauty here

## Repo setup that should already be done

- [x] project scaffold copied from the default template
- [x] public-facing README written for `meadow`
- [x] CI workflow present
- [x] Codecov upload hooks present
- [x] issue templates present
- [x] starter label definitions present

## Repo chores to check after the first push

- [ ] confirm CircleCI runs on `main`
- [ ] confirm the label-sync workflow creates the starter labels
- [ ] add `CODECOV_TOKEN` if Codecov should be active immediately
- [ ] verify README badges resolve after the first CI run

## Guardrails

- keep the simulation core testable without Panda3D
- let rendering observe sim state rather than own it
- avoid a god-file for the world update loop
- keep ecology rules and presentation concerns separate from the start
