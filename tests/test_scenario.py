"""Szenarien: Generatoren sind deterministisch, erzeugen gültige Graphen und treffen ihre Zielgrößen; Gewichte."""

import math
import random

import pytest

import mxc_algorithm as A
import mxc_constants as C
import mxc_scenario as S


def _valid(g):
    assert len(g.adj) == g.n == len(g.positions) == len(g.labels)
    for v in range(g.n):
        assert v not in g.adj[v]
        for w in g.adj[v]:
            assert v in g.adj[w]


@pytest.mark.parametrize("gt", list(C.GRAPH_TYPES))
@pytest.mark.parametrize("density", [C.DENSITY_MIN, 50, C.DENSITY_MAX])
def test_every_graph_type_is_a_valid_graph_at_the_slider_edges(gt, density):
    for n in (C.N_MIN, C.N_MAX):
        _valid(S.build_graph(gt, n, density, 7))


@pytest.mark.parametrize("gt", list(C.GRAPH_TYPES))
def test_same_seed_same_graph_different_seed_different_graph(gt):
    a, b, c = S.build_graph(gt, 20, 50, 3), S.build_graph(gt, 20, 50, 3), S.build_graph(gt, 20, 50, 4)
    assert a.adj == b.adj and a.adj != c.adj


def test_random_graph_density_is_close_to_the_target_on_average():
    for d in (10, 50, 90):
        mean = sum(S.random_graph(30, d, s).m for s in range(40)) / 40 / (30 * 29 / 2)
        assert abs(mean - d / 100) < 0.03, d


def test_window_length_formula_matches_the_overlap_probability():
    for d in (10, 30, 50, 90):
        ell = S.window_length(d)
        assert math.isclose(1 - (1 - ell) ** 2, d / 100)
    mean = sum(S.window_graph(40, 30, s).m for s in range(40)) / 40 / (40 * 39 / 2)
    assert abs(mean - 0.30) < 0.05            # Randeffekt: Starts nahe 1 haben keine Nachbarn rechts, die Dichte liegt knapp unter dem Ziel


def test_class_graph_vertices_of_the_same_class_have_the_same_neighbours_outside_their_class():
    g = S.class_graph(30, 50, 11)
    classes = [int(label.split("Klasse ")[1]) for label in g.labels]
    twins = {}
    for v in range(30):
        twins.setdefault(classes[v], []).append(frozenset(g.adj[v] - {w for w in range(30) if classes[w] == classes[v]}))
    for members in twins.values():
        assert len(set(members)) == 1


def test_moon_moser_graph_shape_and_clique_number():
    g = S.moon_moser_graph(4)
    assert g.n == 12 and g.m == 12 * 11 // 2 - 4 * 3 and all(len(a) == 9 for a in g.adj)
    assert A.largest_clique(g.adj, (1,) * 12).value == 4


def test_tree_grid_scale_free_sizes():
    assert S.tree_graph(50, 1).m == 49
    g = S.grid_graph(6)
    assert g.n == 36 and g.m == 2 * 6 * 5
    sf = S.scale_free_graph(200, 3, 1)
    assert sf.n == 200 and sf.m == 3 * (200 - 3) and max(len(a) for a in sf.adj) > 10


def test_complement_is_an_involution_and_complete_when_empty():
    g = S.random_graph(12, 40, 2)
    assert S.complement(S.complement(g.adj)) == g.adj
    assert all(len(a) == 4 for a in S.complement(S.adjacency_from_edges(5, [])))


def test_adjacency_from_edges_ignores_loops_and_duplicates():
    assert S.adjacency_from_edges(3, [(0, 1), (1, 0), (1, 1), (0, 1)]) == (frozenset({1}), frozenset({0}), frozenset())


def test_circle_positions_are_on_the_unit_circle_and_distinct():
    pos = S.circle_positions(list(range(9)))
    assert len(set(pos)) == 9 and all(math.isclose(x * x + y * y, 1.0, abs_tol=1e-5) for x, y in pos)


def test_unknown_graph_type_raises():
    with pytest.raises(ValueError):
        S.build_graph("nope", 10, 50, 1)


# --- Gewichte --------------------------------------------------------------------------------------------------------------------------------

def test_size_objective_gives_weight_one_everywhere():
    assert S.make_weights(7, 3, "size") == (1,) * 7


def test_value_objective_gives_integers_in_range_deterministically_and_independent_of_the_graph_stream():
    w = S.make_weights(60, 5, "value")
    assert w == S.make_weights(60, 5, "value") and w != S.make_weights(60, 6, "value")
    assert all(C.W_MIN <= x <= C.W_MAX and isinstance(x, int) for x in w) and len(set(w)) > 3
    assert S.random_graph(20, 50, 5).adj == S.random_graph(20, 50, 5).adj                       # der Graph hängt nicht von den Gewichten ab
    rng = random.Random(5 * 7919 + 13)
    assert w[:10] == tuple(rng.randint(C.W_MIN, C.W_MAX) for _ in range(10))
