"""Orakel-Test max-clique-demo: Branch-and-Bound gegen networkx.max_weight_clique, gegen eine zweite unabhängige Formulierung (OR-Tools CP-SAT) und gegen Brute Force.

Orakel 1: `networkx.max_weight_clique` (eigene Implementierung der Bibliothek, mit und ohne Gewichte). Orakel 2: CP-SAT mit je einer Entscheidungsvariablen je Sendung und
„höchstens eine von zwei“-Nebenbedingungen je Nichtkante (ein anderer Rechenweg als Suchbaum mit Schranken). Orakel 3: Aufzählen aller Teilmengen (n <= 16).
Verglichen wird der WERT der besten Clique (Cliquen sind nicht eindeutig); die gemeldete Clique wird zusätzlich als Clique mit genau diesem Wert geprüft.
Alle Schranken, Startordnungen und die Vorverarbeitung müssen denselben Wert liefern."""

import pytest

import mxc_algorithm as A
import mxc_scenario as S

nx = pytest.importorskip("networkx")
cp_model = pytest.importorskip("ortools.sat.python.cp_model")

CONFIGS = [(b, o, p) for b in ("simple", "color") for o in ("index", "degree", "degeneracy") for p in (False, True)]


def _nx_value(adj, weights):
    G = nx.Graph()
    G.add_nodes_from(range(len(adj)))
    G.add_edges_from((u, v) for u in range(len(adj)) for v in adj[u] if u < v)
    for v in G.nodes:
        G.nodes[v]["w"] = weights[v]
    _, value = nx.max_weight_clique(G, weight="w")
    return value


def _cpsat_value(adj, weights):
    n = len(adj)
    model = cp_model.CpModel()
    x = [model.NewBoolVar(f"x{v}") for v in range(n)]
    for u in range(n):
        for v in range(u + 1, n):
            if v not in adj[u]:
                model.Add(x[u] + x[v] <= 1)
    model.Maximize(sum(weights[v] * x[v] for v in range(n)))
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)
    assert status == cp_model.OPTIMAL
    return round(solver.ObjectiveValue())


def _instances():
    """> 300 feste Instanzen: Zufall, Zeitfenster, Klassenregeln und Sonderfälle, je mit Anzahl- und Wertziel."""
    out = []
    for seed in range(100):
        n = 4 + seed % 20
        out.append(("random", S.random_graph(n, 10 + 10 * (seed % 9), seed).adj, seed))
    for seed in range(60):
        n = 5 + seed % 22
        out.append(("windows", S.window_graph(n, 10 + 10 * (seed % 8), seed).adj, seed))
    for seed in range(60):
        n = 5 + seed % 22
        out.append(("classes", S.class_graph(n, 10 + 10 * (seed % 8), seed).adj, seed))
    for n in range(1, 10):
        out.append(("empty", S.adjacency_from_edges(n, []), n))
        out.append(("complete", S.adjacency_from_edges(n, [(i, j) for i in range(n) for j in range(i + 1, n)]), n))
        out.append(("star", S.adjacency_from_edges(n, [(0, i) for i in range(1, n)]), n))
    for n in range(3, 10):
        out.append(("cycle", S.adjacency_from_edges(n, [(i, (i + 1) % n) for i in range(n)]), n))
    out.append(("two components", S.adjacency_from_edges(8, [(0, 1), (1, 2), (0, 2), (4, 5), (5, 6), (6, 7), (4, 7), (4, 6), (5, 7)]), 0))
    return out


INSTANCES = _instances()


def test_there_are_more_than_300_instances_and_two_objectives():
    assert len(INSTANCES) * 2 > 300


def test_every_configuration_equals_networkx_on_every_instance():
    for name, adj, seed in INSTANCES:
        for objective in ("size", "value"):
            w = S.make_weights(len(adj), seed, objective)
            ref = _nx_value(adj, w)
            for bound, order, prune in CONFIGS:
                r = A.largest_clique(adj, w, bound, order, prune)
                assert r.value == ref, (name, len(adj), objective, bound, order, prune)
                assert A.is_clique(adj, r.clique) and A.clique_value(w, r.clique) == r.value, (name, objective)


def test_default_configuration_equals_cpsat_on_every_third_instance():
    for name, adj, seed in INSTANCES[::3]:
        for objective in ("size", "value"):
            w = S.make_weights(len(adj), seed, objective)
            assert A.largest_clique(adj, w).value == _cpsat_value(adj, w), (name, len(adj), objective)


def test_equal_brute_force_on_small_instances():
    checked = 0
    for name, adj, seed in INSTANCES:
        if len(adj) > 12:
            continue
        for objective in ("size", "value"):
            w = S.make_weights(len(adj), seed, objective)
            value, optimal = A.brute_force_max_clique(adj, w)
            for bound, order, prune in CONFIGS[::3]:
                r = A.largest_clique(adj, w, bound, order, prune)
                assert r.value == value and r.clique in optimal, (name, objective, bound, order, prune)
            checked += 1
    assert checked >= 200


@pytest.mark.parametrize("k", range(1, 7))
def test_moon_moser_clique_number_is_k(k):
    g = S.moon_moser_graph(k)
    for bound in ("simple", "color"):
        assert A.largest_clique(g.adj, (1,) * g.n, bound).value == k


def test_tree_clique_number_is_two_and_complete_graph_is_n():
    t = S.tree_graph(60, 3)
    assert A.largest_clique(t.adj, (1,) * 60).value == 2
    n = 9
    assert A.largest_clique(S.adjacency_from_edges(n, [(i, j) for i in range(n) for j in range(i + 1, n)]), (1,) * n).value == n


def test_window_graph_clique_number_equals_the_largest_number_of_windows_open_at_the_same_time():
    """Unabhängig berechnet: die Starts mit demselben Zufallsstrom neu ziehen und per Sweep die größte Zahl Fenster zählen, die an einem Anfang gleichzeitig offen sind."""
    import random
    for seed in range(15):
        n = 30
        g = S.window_graph(n, 40, seed)
        ell = S.window_length(40)
        rng = random.Random(seed)
        starts = sorted(rng.random() for _ in range(n))
        best = max(sum(1 for t in starts if s0 <= t <= s0 + ell) for s0 in starts)
        r = A.largest_clique(g.adj, (1,) * n, "color", "degree")
        assert r.value == best and A.is_clique(g.adj, r.clique)


def test_cliques_of_the_complement_are_independent_sets_alpha_equals_omega():
    for seed in range(20):
        g = S.random_graph(5 + seed % 8, 20 + 10 * (seed % 6), seed)
        ones = (1,) * g.n
        omega = A.largest_clique(g.adj, ones).value
        assert A.brute_force_max_independent_set(S.complement(g.adj), ones) == omega
        alpha = A.largest_clique(S.complement(g.adj), ones).value
        assert alpha == A.brute_force_max_independent_set(g.adj, ones)


def test_bounds_are_valid_upper_bounds_at_the_root():
    for seed in range(30):
        g = S.random_graph(6 + seed % 10, 30 + 10 * (seed % 6), seed)
        w = S.make_weights(g.n, seed, "value")
        value, _ = A.brute_force_max_clique(g.adj, w)
        assert A.root_color_bound(g.adj, w, "degree") >= value
        assert A.simple_bound(0, list(range(g.n)), w) >= A.root_color_bound(g.adj, w, "degree")
