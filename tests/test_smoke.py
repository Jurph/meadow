"""Basic smoke tests for the template project."""

from meadow.main import main


def test_main_runs(capsys) -> None:
    """The starter CLI should print a placeholder message."""
    main()
    captured = capsys.readouterr()
    assert "meadow scaffolding placeholder" in captured.out
