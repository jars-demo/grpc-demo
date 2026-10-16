"""Integration tests against the running Docker Compose stack.

    python scripts/tasks.py up
    uv run pytest -m integration tests/integration

Each smoke-test check becomes one test, so a failure names exactly what broke.
"""

from __future__ import annotations

import pytest

from scripts.smoke_test import CHECKS, Check

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("check", CHECKS, ids=lambda c: c.name)
def test_stack(check: Check) -> None:
    check.run()
