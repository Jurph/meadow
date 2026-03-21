# meadow

[![CircleCI](https://circleci.com/gh/Jurph/meadow.svg?style=svg)](https://circleci.com/gh/Jurph/meadow)
[![Codecov](https://codecov.io/gh/Jurph/meadow/branch/main/graph/badge.svg)](https://codecov.io/gh/Jurph/meadow)

`meadow` is an in-progress terrarium sim about plant life under pressure.

The long-term idea is a hex-grid hillside where plants act like characters: they compete for light,
water, and nutrients, reproduce into nearby space when conditions favor them, mutate across
generations, and feed the soil again when they die and decay. The environment exists to stress the
plants in interesting ways and let evolution do visible work.

## Status

This repository is currently scaffolding.

The janitorial setup is in place:
- Python project structure and local dev tooling
- CI checks and Codecov upload hooks
- issue templates and starter issue labels
- a public project README and a dev-facing `TODO.md`

The simulation, Panda3D renderer, and terrarium UI are still ahead of us.

## Planned first experience

The first real milestone is a primitive but usable GUI terrarium:
- a hex-grid world on a tilted hillside
- one plant anchored per hex
- light, water, and nutrients as the first live environmental pressures
- room to add pests and pollinators later

If you want the working notes instead of the public pitch, start with `TODO.md`.

## Development setup

Dependencies for this project are defined in `pyproject.toml`.

If you are using `uv`:

```bash
uv sync --extra dev
```

On Windows, this repo includes wrappers that keep uv's cache and managed Python inside the
repository instead of relying on user-level AppData paths:

```bat
.\scripts\uvw.cmd sync --extra dev
.\scripts\uvw.cmd run --extra dev pytest
```

The first `sync` may still need normal network access to download Python or wheels. After that,
the wrapper keeps the repo self-contained.
For `run`, the wrapper also injects `--locked` so verification commands fail fast if `uv.lock`
falls behind `pyproject.toml` instead of rewriting the lockfile during a test or lint pass.

The wrapper intentionally does **not** override `TMP` or `TEMP`. On this machine, Python's
`tempfile.mkdtemp()` and `TemporaryDirectory()` can create Windows directories that immediately
reject child files and folders. If you need repo-local scratch space, use a normal directory such
as `.scratch/` created with `Path.mkdir()` and a unique name, not the `tempfile` directory APIs.

If you are using `pip`:

```bash
python -m venv .venv
```

Then activate it:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (cmd.exe)
.venv\Scripts\activate
```

Then install the project and development dependencies:

```bash
pip install -e .[dev]
```

## Standard verification commands

```bash
uv run --locked --extra dev pytest
uv run --locked --extra dev ruff check --no-cache src tests
uv run --locked --extra dev ruff format --check src tests
uv run --locked --extra dev mypy src
```

## CI and coverage

CircleCI runs tests, Ruff, and mypy on pushes. Coverage upload is wired for Codecov and will start
reporting once `CODECOV_TOKEN` is configured in the CircleCI project environment and the first
upload lands on `main`.

The repo still keeps one small GitHub-native workflow for syncing issue labels from
`.github/labels.json`, because label automation has to run inside GitHub.

If Codecov gets stuck in its half-initialized state during setup, run the helper from the repo
root:

```bash
uv run python scripts/bootstrap_codecov.py
```

## Contributing

This repo is intentionally early. If you want to help, the best starting points are:
- read `TODO.md`
- open or refine issues against the current roadmap
- keep new work small, testable, and easy to reason about
