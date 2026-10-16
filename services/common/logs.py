"""Plain, single-line log format shared by the services. Never log key material or request bodies."""

from __future__ import annotations

import logging


def configure(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True,
    )
