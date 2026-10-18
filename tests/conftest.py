"""Gemeinsame Fixtures: die Mini-Instanzen, an denen jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mxc_scenario import adjacency_from_edges  # noqa: E402


@pytest.fixture
def mini():
    """5 Sendungen: das Dreieck {0, 1, 2}, der Pendelknoten 3 an 2, der isolierte Knoten 4. Größte Clique {0, 1, 2} (ω = 3)."""
    return adjacency_from_edges(5, [(0, 1), (0, 2), (1, 2), (2, 3)])


@pytest.fixture
def ones():
    return (1, 1, 1, 1, 1)


@pytest.fixture
def pentagon():
    """Das Fünfeck: ω = 2, aber die gierige Färbung braucht 3 Farben (die Färbungsschranke ist hier nicht scharf)."""
    return adjacency_from_edges(5, [(i, (i + 1) % 5) for i in range(5)])


@pytest.fixture
def k4():
    return adjacency_from_edges(4, [(i, j) for i in range(4) for j in range(i + 1, 4)])
