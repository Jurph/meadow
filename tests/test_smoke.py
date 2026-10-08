"""CLI behavior tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from meadow.main import main


def test_simulate_command_writes_renderer_snapshot(tmp_path: Path, capsys) -> None:
    output = tmp_path / "meadow.json"

    result = main(
        [
            "simulate",
            "--width",
            "7",
            "--height",
            "7",
            "--ticks",
            "10",
            "--seed",
            "42",
            "--output",
            str(output),
        ]
    )

    assert result == 0
    assert capsys.readouterr().out.strip() == str(output)
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 2
    assert payload["tick"] == 10
    assert payload["world"]["width"] == 7
    assert payload["world"]["height"] == 7
    assert len(payload["plants"]) == 1
    plant = payload["plants"][0]
    assert set(plant["resources"]) == {"water", "minerals", "assimilate"}
    assert plant["balance_sheet"]["tick"] == 9
    assert len(plant["leaves"]) > 1
    assert {segment["segment_type"] for segment in payload["plants"][0]["segments"]} == {
        "ROOT",
        "STEM",
    }


def test_simulate_command_reports_output_errors(tmp_path: Path, capsys) -> None:
    output = tmp_path / "missing" / "meadow.json"

    with pytest.raises(SystemExit) as exit_info:
        main(["simulate", "--output", str(output)])

    assert exit_info.value.code == 2
    assert "cannot write snapshot" in capsys.readouterr().err
