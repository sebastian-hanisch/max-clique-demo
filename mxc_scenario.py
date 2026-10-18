"""Szenarien: der Verträglichkeitsgraph einer Sammelladung und die Vergleichsgraphen (Moon–Moser, Baum, Gitter, skalenfrei).

Ein Graph ist eine Adjazenzliste `adj` (Tupel von Mengen; Knoten 0 .. n-1, ungerichtet, ohne Schleifen) plus Anzeige-Positionen.
Kante = zwei Sendungen dürfen zusammen verladen werden (Verträglichkeitsgraph). Der Konfliktgraph ist das Komplement."""

import math
import random
from dataclasses import dataclass

import mxc_constants as C


@dataclass(frozen=True)
class Graph:
    n: int
    adj: tuple          # adj[v] = frozenset der Nachbarn von v
    positions: tuple    # (x, y) je Knoten, Kreisanordnung in sinnvoller Reihenfolge
    labels: tuple       # Hover-Text je Knoten
    kind: str           # "random", "windows", "classes", "moon_moser", "tree", "grid", "scale_free"

    @property
    def m(self):
        return sum(len(a) for a in self.adj) // 2

    def edges(self):
        return [(u, v) for u in range(self.n) for v in sorted(self.adj[u]) if u < v]


def _freeze(adj_lists, n):
    return tuple(frozenset(a) for a in adj_lists[:n])


def adjacency_from_edges(n, edges):
    """Adjazenzliste aus ungerichteten Kanten; Schleifen und doppelte Kanten werden ignoriert."""
    adj = [set() for _ in range(n)]
    for u, v in edges:
        if u != v:
            adj[u].add(v)
            adj[v].add(u)
    return _freeze(adj, n)


def circle_positions(order):
    """Knoten in der gegebenen Reihenfolge auf einen Kreis (Radius 1, Start oben)."""
    n = len(order)
    pos = [None] * n
    for slot, v in enumerate(order):
        angle = math.pi / 2 - 2 * math.pi * slot / max(n, 1)
        pos[v] = (round(math.cos(angle), 6), round(math.sin(angle), 6))
    return tuple(pos)


def complement(adj):
    """Das Komplement: u und v sind benachbart genau dann, wenn sie es in `adj` NICHT sind."""
    n = len(adj)
    return tuple(frozenset(w for w in range(n) if w != v and w not in adj[v]) for v in range(n))


def random_graph(n, density_pct, seed):
    """G(n, p) mit p = density_pct / 100: jedes Paar ist unabhängig mit Wahrscheinlichkeit p verträglich."""
    rng = random.Random(seed)
    p = density_pct / 100.0
    edges = [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < p]
    adj = adjacency_from_edges(n, edges)
    labels = tuple(f"Sendung {i + 1}" for i in range(n))
    return Graph(n, adj, circle_positions(list(range(n))), labels, "random")


def window_length(density_pct):
    """Fensterlänge l (Anteil der Zeitachse), bei der zwei gleichverteilte Fenster mit Wahrscheinlichkeit density_pct/100 überlappen: 1 - (1 - l)^2 = d."""
    d = min(max(density_pct / 100.0, 0.0), 1.0)
    return 1.0 - math.sqrt(1.0 - d)


def window_graph(n, density_pct, seed):
    """Zeitfenster [s, s + l] mit gleichverteiltem Start s in [0, 1] und fester Länge l; verträglich heißt: die Fenster überlappen. Knoten nach Start sortiert."""
    rng = random.Random(seed)
    length = window_length(density_pct)
    starts = sorted(rng.random() for _ in range(n))
    edges = [(i, j) for i in range(n) for j in range(i + 1, n) if starts[j] - starts[i] <= length]
    adj = adjacency_from_edges(n, edges)
    labels = tuple(f"Sendung {i + 1}: Fenster {s:.2f} bis {s + length:.2f}" for i, s in enumerate(starts))
    return Graph(n, adj, circle_positions(list(range(n))), labels, "windows")


def class_graph(n, density_pct, seed, n_classes=C.N_CLASSES):
    """Jede Sendung gehört zu einer von n_classes Klassen; jedes Klassenpaar (auch Klasse mit sich selbst) ist mit Wahrscheinlichkeit density_pct/100 verträglich.
    Zwei Sendungen sind verträglich, wenn ihre Klassen es sind. Knoten nach Klasse gruppiert, damit die Blockstruktur sichtbar wird."""
    rng = random.Random(seed)
    p = density_pct / 100.0
    cls = [rng.randrange(n_classes) for _ in range(n)]
    ok = {}
    for a in range(n_classes):
        for b in range(a, n_classes):
            ok[(a, b)] = rng.random() < p
    edges = [(i, j) for i in range(n) for j in range(i + 1, n) if ok[(min(cls[i], cls[j]), max(cls[i], cls[j]))]]
    adj = adjacency_from_edges(n, edges)
    order = sorted(range(n), key=lambda v: (cls[v], v))
    labels = tuple(f"Sendung {i + 1}, Klasse {cls[i] + 1}" for i in range(n))
    return Graph(n, adj, circle_positions(order), labels, "classes")


def moon_moser_graph(k):
    """Vollständig multipartit mit k Teilen zu je 3 Knoten (n = 3k): der Graph mit den meisten maximalen Cliquen, nämlich 3^k (Moon und Moser 1965)."""
    n = 3 * k
    edges = [(i, j) for i in range(n) for j in range(i + 1, n) if i // 3 != j // 3]
    adj = adjacency_from_edges(n, edges)
    labels = tuple(f"Knoten {i + 1}, Teil {i // 3 + 1}" for i in range(n))
    return Graph(n, adj, circle_positions(list(range(n))), labels, "moon_moser")


def tree_graph(n, seed):
    """Zufälliger Baum: Knoten i >= 1 hängt an einem gleichverteilt gewählten früheren Knoten."""
    rng = random.Random(seed)
    edges = [(i, rng.randrange(i)) for i in range(1, n)]
    adj = adjacency_from_edges(n, edges)
    return Graph(n, adj, circle_positions(list(range(n))), tuple(f"Knoten {i + 1}" for i in range(n)), "tree")


def grid_graph(side):
    """Gitter side x side (Straßenraster, Kreuzungen als Knoten)."""
    n = side * side
    edges = []
    for r in range(side):
        for c in range(side):
            v = r * side + c
            if c + 1 < side:
                edges.append((v, v + 1))
            if r + 1 < side:
                edges.append((v, v + side))
    adj = adjacency_from_edges(n, edges)
    return Graph(n, adj, circle_positions(list(range(n))), tuple(f"Kreuzung {i + 1}" for i in range(n)), "grid")


def scale_free_graph(n, m, seed):
    """Preferential Attachment (Barabási–Albert): jeder neue Knoten hängt sich an m verschiedene frühere, gewählt proportional zum Grad."""
    rng = random.Random(seed)
    edges = []
    targets = list(range(m))
    repeated = []
    for v in range(m, n):
        edges.extend((v, t) for t in targets)
        repeated.extend(targets)
        repeated.extend([v] * m)
        chosen = set()
        while len(chosen) < m:
            chosen.add(repeated[rng.randrange(len(repeated))])
        targets = sorted(chosen)
    adj = adjacency_from_edges(n, edges)
    return Graph(n, adj, circle_positions(list(range(n))), tuple(f"Knoten {i + 1}" for i in range(n)), "scale_free")


def build_graph(graph_type, n, density_pct, seed):
    """Der Graph der Hauptansicht."""
    if graph_type == "random":
        return random_graph(n, density_pct, seed)
    if graph_type == "windows":
        return window_graph(n, density_pct, seed)
    if graph_type == "classes":
        return class_graph(n, density_pct, seed)
    raise ValueError(f"unbekannter Graphtyp: {graph_type}")


def make_weights(n, seed, objective):
    """Wert je Sendung: bei „size“ überall 1 (die Fuhre zählt Sendungen), bei „value“ ganzzahlig gleichverteilt in [W_MIN, W_MAX] aus einem eigenen Generator (der Graph bleibt beim selben Seed unverändert)."""
    if objective == "size":
        return tuple([1] * n)
    rng = random.Random(seed * 7919 + 13)
    return tuple(rng.randint(C.W_MIN, C.W_MAX) for _ in range(n))
