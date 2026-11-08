"""The world data, including the held-out queries, is pinned by fingerprint before any agent or
evaluation code exists. Development never scores the held-out queries; scripts/heldout.py checks the pin, runs once and
logs it."""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def files() -> list[Path]:
    return sorted(p for p in (ROOT / "data").rglob("*") if p.is_file())


def fingerprint() -> str:
    h = hashlib.sha256()
    for f in files():
        h.update(str(f.relative_to(ROOT)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def pinned() -> str:
    return (ROOT / "config" / "heldout.sha256").read_text().split()[0]


def check() -> None:
    if fingerprint() != pinned():
        raise RuntimeError("the world data changed after the held-out set was pinned")
