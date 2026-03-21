"""Tests for the one-shot Codecov bootstrap helper."""

from __future__ import annotations

from meadow.codecov_bootstrap import (
    CodecovBootstrapState,
    CodecovLocation,
    build_bootstrap_commands,
    classify_bootstrap_state,
    parse_remote_slug,
)


def test_parse_remote_slug_accepts_https_github_remote() -> None:
    """HTTPS remotes should parse into the owner/repo slug."""
    assert parse_remote_slug("https://github.com/Jurph/fast-foto-forensics.git") == (
        "Jurph",
        "fast-foto-forensics",
    )


def test_parse_remote_slug_accepts_ssh_github_remote() -> None:
    """SSH remotes should parse into the owner/repo slug."""
    assert parse_remote_slug("git@github.com:Jurph/fast-foto-forensics.git") == (
        "Jurph",
        "fast-foto-forensics",
    )


def test_classify_bootstrap_state_detects_half_initialized_repo() -> None:
    """An active repo with missing totals should trigger the bootstrap nudge."""
    state = CodecovBootstrapState(
        repo_active=True,
        repo_activated=True,
        repo_totals=None,
        commits_count=1,
        branches_count=1,
        first_commit_totals=None,
        badge_unknown=True,
    )

    verdict = classify_bootstrap_state(state)

    assert verdict.should_bootstrap is True
    assert "half-initialized" in verdict.reason


def test_classify_bootstrap_state_leaves_unconfigured_repo_alone() -> None:
    """A repo that still needs configuration should not run the wake-up commands."""
    state = CodecovBootstrapState(
        repo_active=False,
        repo_activated=False,
        repo_totals=None,
        commits_count=0,
        branches_count=0,
        first_commit_totals=None,
        badge_unknown=True,
    )

    verdict = classify_bootstrap_state(state)

    assert verdict.should_bootstrap is False
    assert "configure" in verdict.reason.lower()


def test_build_bootstrap_commands_uses_create_commit_and_report() -> None:
    """The bootstrap helper should nudge Codecov with commit and report creation."""
    location = CodecovLocation(
        owner="Jurph",
        repo="fast-foto-forensics",
        branch="main",
        sha="ae75c54cf721e0fb9a01627ae266f97cd80ab1ce",
    )

    commands = build_bootstrap_commands(location, token="repo-token")

    assert commands == [
        [
            "uvx",
            "--from",
            "codecov-cli",
            "codecovcli",
            "create-commit",
            "--sha",
            "ae75c54cf721e0fb9a01627ae266f97cd80ab1ce",
            "--branch",
            "main",
            "--git-service",
            "github",
            "--slug",
            "Jurph/fast-foto-forensics",
            "--token",
            "repo-token",
            "--fail-on-error",
        ],
        [
            "uvx",
            "--from",
            "codecov-cli",
            "codecovcli",
            "create-report",
            "--sha",
            "ae75c54cf721e0fb9a01627ae266f97cd80ab1ce",
            "--git-service",
            "github",
            "--slug",
            "Jurph/fast-foto-forensics",
            "--token",
            "repo-token",
            "--fail-on-error",
        ],
    ]
