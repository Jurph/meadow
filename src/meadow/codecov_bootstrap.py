"""One-shot helper for nudging a newly configured Codecov repo into life."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

GITHUB_REMOTE_RE = re.compile(
    r"^(?:https://github\.com/|git@github\.com:)(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
)


@dataclass(frozen=True)
class CodecovLocation:
    """Repository coordinates for Codecov bootstrap operations."""

    owner: str
    repo: str
    branch: str
    sha: str
    git_service: str = "github"
    api_service: str = "gh"

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def repo_url(self) -> str:
        return f"https://api.codecov.io/api/v2/{self.api_service}/{self.owner}/repos/{self.repo}/"

    @property
    def commits_url(self) -> str:
        return f"{self.repo_url}commits/?branch={self.branch}"

    @property
    def branches_url(self) -> str:
        return f"{self.repo_url}branches/"

    @property
    def badge_url(self) -> str:
        return (
            f"https://codecov.io/gh/{self.owner}/{self.repo}/branch/{self.branch}/graph/badge.svg"
        )


@dataclass(frozen=True)
class CodecovBootstrapState:
    """Publicly visible Codecov state for a repository."""

    repo_active: bool
    repo_activated: bool
    repo_totals: dict[str, Any] | None
    commits_count: int
    branches_count: int
    first_commit_totals: dict[str, Any] | None
    badge_unknown: bool


@dataclass(frozen=True)
class BootstrapVerdict:
    """Result of classifying whether Codecov needs a bootstrap nudge."""

    state_name: str
    should_bootstrap: bool
    reason: str


def parse_remote_slug(remote_url: str) -> tuple[str, str]:
    """Extract the GitHub owner/repo slug from a remote URL."""
    match = GITHUB_REMOTE_RE.match(remote_url.strip())
    if not match:
        msg = (
            "Could not parse a GitHub owner/repo slug from the origin remote. "
            "Pass --owner and --repo explicitly."
        )
        raise ValueError(msg)
    return match.group("owner"), match.group("repo")


def classify_bootstrap_state(state: CodecovBootstrapState) -> BootstrapVerdict:
    """Decide whether a repo is configured, healthy, or stuck in Codecov limbo."""
    if not state.repo_active or not state.repo_activated:
        return BootstrapVerdict(
            state_name="configure_needed",
            should_bootstrap=False,
            reason=(
                "Codecov still thinks this repo needs the normal configure step. "
                "Finish the setup flow before running the bootstrap helper."
            ),
        )

    if state.repo_totals is not None or state.first_commit_totals is not None:
        return BootstrapVerdict(
            state_name="healthy",
            should_bootstrap=False,
            reason="Codecov already has coverage totals for this repo.",
        )

    return BootstrapVerdict(
        state_name="half_initialized",
        should_bootstrap=True,
        reason=(
            "Codecov looks half-initialized: "
            "the repo is active, but coverage totals are still missing. "
            "Running the bootstrap nudge should create the missing repo state."
        ),
    )


def build_bootstrap_commands(location: CodecovLocation, token: str) -> list[list[str]]:
    """Build the minimal Codecov CLI wake-up commands."""
    base = [
        "uvx",
        "--from",
        "codecov-cli",
        "codecovcli",
    ]
    return [
        [
            *base,
            "create-commit",
            "--sha",
            location.sha,
            "--branch",
            location.branch,
            "--git-service",
            location.git_service,
            "--slug",
            location.slug,
            "--token",
            token,
            "--fail-on-error",
        ],
        [
            *base,
            "create-report",
            "--sha",
            location.sha,
            "--git-service",
            location.git_service,
            "--slug",
            location.slug,
            "--token",
            token,
            "--fail-on-error",
        ],
    ]


def load_json(url: str) -> dict[str, Any]:
    """Fetch JSON from a public Codecov endpoint."""
    request = Request(url, headers={"User-Agent": "jurph-project-template-codecov-bootstrap"})
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:  # pragma: no cover - network error path
        raise RuntimeError(f"Codecov returned HTTP {exc.code} for {url}") from exc
    except URLError as exc:  # pragma: no cover - network error path
        raise RuntimeError(f"Could not reach Codecov at {url}") from exc


def load_text(url: str) -> str:
    """Fetch plain text from a public Codecov endpoint."""
    request = Request(url, headers={"User-Agent": "jurph-project-template-codecov-bootstrap"})
    try:
        with urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except HTTPError as exc:  # pragma: no cover - network error path
        raise RuntimeError(f"Codecov returned HTTP {exc.code} for {url}") from exc
    except URLError as exc:  # pragma: no cover - network error path
        raise RuntimeError(f"Could not reach Codecov at {url}") from exc


def fetch_public_state(location: CodecovLocation) -> CodecovBootstrapState:
    """Read the public repo/commit/branch state that Codecov exposes."""
    repo_payload = load_json(location.repo_url)
    commits_payload = load_json(location.commits_url)
    branches_payload = load_json(location.branches_url)
    badge_svg = load_text(location.badge_url)

    first_commit = commits_payload.get("results", [None])[0] or {}
    return CodecovBootstrapState(
        repo_active=bool(repo_payload.get("active")),
        repo_activated=bool(repo_payload.get("activated")),
        repo_totals=repo_payload.get("totals"),
        commits_count=int(commits_payload.get("count", 0)),
        branches_count=int(branches_payload.get("count", 0)),
        first_commit_totals=first_commit.get("totals"),
        badge_unknown=">unknown<" in badge_svg,
    )


def bootstrap_acknowledged(state: CodecovBootstrapState) -> bool:
    """Treat commit and branch records as evidence that Codecov accepted the nudge."""
    return (
        state.repo_active
        and state.repo_activated
        and state.commits_count > 0
        and state.branches_count > 0
    )


def run_command(command: list[str]) -> None:
    """Run a subprocess and fail loudly if it does not succeed."""
    subprocess.run(command, check=True)


def read_git_output(*args: str) -> str:
    """Read a simple git command from the current repository."""
    result = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def discover_location(args: argparse.Namespace) -> CodecovLocation:
    """Infer repo coordinates from git unless the user overrides them."""
    owner = args.owner
    repo = args.repo
    if not owner or not repo:
        remote = read_git_output("remote", "get-url", "origin")
        inferred_owner, inferred_repo = parse_remote_slug(remote)
        owner = owner or inferred_owner
        repo = repo or inferred_repo

    branch = args.branch or read_git_output("branch", "--show-current")
    if not branch:
        branch = read_git_output("rev-parse", "--abbrev-ref", "HEAD")

    sha = args.sha or read_git_output("rev-parse", "HEAD")
    return CodecovLocation(owner=owner, repo=repo, branch=branch, sha=sha)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface for the setup helper."""
    parser = argparse.ArgumentParser(
        description=(
            "Nudge a newly configured Codecov repo out of the half-initialized state "
            "that can leave the UI saying 'Deactivated' or the badge stuck at 'unknown'."
        )
    )
    parser.add_argument(
        "--owner", help="GitHub owner or organization name. Defaults to origin remote."
    )
    parser.add_argument("--repo", help="GitHub repo name. Defaults to origin remote.")
    parser.add_argument("--branch", help="Branch to check. Defaults to the current branch.")
    parser.add_argument("--sha", help="Commit SHA to bootstrap. Defaults to HEAD.")
    parser.add_argument(
        "--token",
        help="Codecov upload token. Defaults to the CODECOV_TOKEN environment variable.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=180,
        help="How long to poll Codecov after the bootstrap commands run.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=10,
        help="How often to recheck public Codecov state after the bootstrap commands run.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run the bootstrap commands even if the public state already looks healthy.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the one-shot Codecov bootstrap helper."""
    parser = build_parser()
    args = parser.parse_args(argv)

    token = args.token or os.environ.get("CODECOV_TOKEN")
    if not token:
        print("Missing Codecov upload token. Set CODECOV_TOKEN or pass --token.", file=sys.stderr)
        return 2

    location = discover_location(args)
    state = fetch_public_state(location)
    verdict = classify_bootstrap_state(state)

    print(f"Codecov repo: {location.slug}")
    print(f"Branch: {location.branch}")
    print(f"Commit: {location.sha}")
    print(verdict.reason)

    if not verdict.should_bootstrap and not args.force:
        return 0

    for command in build_bootstrap_commands(location, token):
        print(f"Running: {' '.join(command)}")
        run_command(command)

    deadline = time.monotonic() + args.timeout_seconds
    while time.monotonic() < deadline:
        state = fetch_public_state(location)
        if bootstrap_acknowledged(state):
            print("Codecov acknowledged the bootstrap nudge.")
            if state.repo_totals is None and state.badge_unknown:
                print(
                    "Commit and branch records are present, "
                    "but public coverage totals are still warming up. "
                    "Codecov's UI may need a little longer to catch up."
                )
            return 0

        print("Codecov still looks sleepy; polling again soon...")
        time.sleep(args.poll_interval_seconds)

    print(
        "Timed out waiting for Codecov to acknowledge the bootstrap nudge. "
        "Check the repo page, badge, and CircleCI upload logs."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
