"""Tests for repo-level scaffolding choices."""

from pathlib import Path


def test_circleci_config_exists_for_ci() -> None:
    """The scaffold should use CircleCI for the main CI pipeline."""
    assert Path(".circleci/config.yml").is_file()


def test_github_actions_ci_workflow_is_not_used() -> None:
    """The repo should not keep a competing GitHub Actions CI workflow."""
    assert not Path(".github/workflows/ci.yml").exists()


def test_readme_points_ci_language_at_circleci() -> None:
    """The README should describe CircleCI as the CI provider."""
    text = Path("README.md").read_text(encoding="utf-8")

    assert "CircleCI" in text
    assert "GitHub Actions runs tests" not in text
