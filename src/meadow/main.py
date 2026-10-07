"""Command-line entry point for running Meadow simulations."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from meadow.sim import Simulation, SimulationConfig


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="meadow",
        description="Run the Meadow plant simulation.",
    )
    commands = parser.add_subparsers(dest="command")
    simulate = commands.add_parser(
        "simulate",
        help="run deterministic ticks and write a renderer snapshot",
    )
    simulate.add_argument("--width", type=_positive_int, default=7)
    simulate.add_argument("--height", type=_positive_int, default=7)
    simulate.add_argument("--ticks", type=_non_negative_int, default=10)
    simulate.add_argument("--seed", type=int, default=42)
    simulate.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run a CLI command and return its process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "simulate":
        config = SimulationConfig(
            width=args.width,
            height=args.height,
            weather_seed=args.seed,
        )
        snapshot = Simulation(config).run(args.ticks)
        output: Path = args.output
        try:
            output.write_text(f"{snapshot.to_json()}\n", encoding="utf-8")
        except OSError as error:
            parser.error(f"cannot write snapshot to {output}: {error}")
        print(output)
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
