"""Every challenge scenario fails as shipped and passes with its intended fix, against real
servers. Insecure "fixes" are rejected even when the call itself would succeed."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import challenge.__main__ as runner
from challenge.scenarios import SCENARIOS
from tests.conftest import Servers

FIXES = {
    "01": [("rogue-ca.crt", "ca.crt")],
    "02": [("127.0.0.1", "localhost")],
    "03": [
        (
            "deadline_seconds",
            'cert = "certs/out/client.crt"\nkey = "certs/out/client.key"\ndeadline_seconds',
        )
    ],
    "04": [("rogue-client", "client")],
    "05": [("/client.", "/admin.")],
    "06": [("deadline_seconds = 0.3", "deadline_seconds = 2")],
}


@pytest.fixture
def workspace(
    tmp_path: Path, certs_dir: Path, servers: Servers, monkeypatch: pytest.MonkeyPatch
) -> Path:
    shutil.copytree(certs_dir, tmp_path / "certs" / "out")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner, "WORK", tmp_path / "work")
    runner.start(force=True)
    for profile in (tmp_path / "work").glob("*.toml"):
        text = (
            profile.read_text()
            .replace(":50051", f":{servers.tls}")
            .replace(":50052", f":{servers.mtls}")
        )
        profile.write_text(text)
    return tmp_path / "work"


def apply(work: Path, number: str, edits: list[tuple[str, str]]) -> None:
    profile = work / f"{number}.toml"
    text = profile.read_text()
    for old, new in edits:
        assert old in text, (number, old)
        text = text.replace(old, new)
    profile.write_text(text)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: f"{s.number}-{s.slug}")
def test_scenario_fails_as_shipped(workspace: Path, scenario) -> None:  # type: ignore[no-untyped-def]
    assert runner.check(scenario) is False


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: f"{s.number}-{s.slug}")
def test_scenario_passes_with_intended_fix(workspace: Path, scenario) -> None:  # type: ignore[no-untyped-def]
    apply(workspace, scenario.number, FIXES[scenario.number])

    assert runner.check(scenario) is True


def test_dropping_the_ca_is_rejected(workspace: Path) -> None:
    apply(workspace, "01", [('ca = "certs/out/rogue-ca.crt"', 'ca = ""')])

    assert runner.check(SCENARIOS[0]) is False


def test_unbounded_deadline_is_rejected_even_though_the_call_succeeds(workspace: Path) -> None:
    apply(workspace, "06", [("deadline_seconds = 0.3", "deadline_seconds = 60")])

    assert runner.check(SCENARIOS[5]) is False


def test_plaintext_is_rejected(workspace: Path) -> None:
    apply(workspace, "02", [("deadline_seconds", "plaintext = true\ndeadline_seconds")])

    assert runner.check(SCENARIOS[1]) is False
