"""Kern gegen Handrechnung (Mini-Instanzen) und Brute Force: jede Einheit einzeln, dann die Komposition."""

import pytest

import mxc_algorithm as A
import mxc_scenario as S

W_VALUE = (1, 1, 1, 9, 1)          # die Sendung 3 ist neun Mal so viel wert: {2, 3} (Wert 10) schlägt {0, 1, 2} (Wert 3)


# --- Einheiten ------------------------------------------------------------------------------------------------------------------------------

def test_core_decomposition_by_hand(mini):
    order, core, d = A.core_decomposition(mini)
    assert order == [4, 3, 0, 1, 2] and core == [2, 2, 2, 1, 0] and d == 2


def test_core_decomposition_of_known_families():
    assert A.core_decomposition(S.tree_graph(30, 1).adj)[2] == 1
    assert A.core_decomposition(S.grid_graph(5).adj)[2] == 2
    assert A.core_decomposition(S.moon_moser_graph(4).adj)[2] == 9
    assert A.core_decomposition(S.adjacency_from_edges(4, []))[2] == 0


def test_start_order_rules_by_hand(mini):
    removal, _, _ = A.core_decomposition(mini)
    assert A.start_order(mini, "index", removal) == [0, 1, 2, 3, 4]
    assert A.start_order(mini, "degree", removal) == [2, 0, 1, 3, 4]         # Grade 2, 2, 3, 1, 0
    assert A.start_order(mini, "degeneracy", removal) == [2, 1, 0, 3, 4]     # umgekehrte Entfernungsreihenfolge [4, 3, 0, 1, 2]
    with pytest.raises(ValueError):
        A.start_order(mini, "magic", removal)


def test_greedy_clique_by_hand(mini, ones):
    assert A.greedy_clique(mini, ones) == ((0, 1, 2), 3, 14)               # Kosten: 8 + 5 + 1 Abfragen
    assert A.greedy_clique(mini, W_VALUE)[:2] == ((0, 1, 2), 3)              # das Gewicht 9 an Knoten 3 entscheidet nur Gleichstände der Nachbarzahl; hier gewinnt Knoten 0 (1 Nachbar im Rest) gegen 3 (0): Greedy verfehlt den Optimalwert 10


def test_greedy_clique_prefers_the_heavier_vertex_on_ties():
    adj = S.adjacency_from_edges(4, [(0, 1), (2, 3)])                     # zwei Kanten, gleiche Nachbarzahl
    assert A.greedy_clique(adj, (1, 1, 1, 5))[0] == (2, 3)
    assert A.greedy_clique(adj, (5, 1, 1, 1))[0] == (0, 1)


def test_core_keep_needs_core_number_at_least_lower_bound_over_wmax(mini, ones):
    _, core, _ = A.core_decomposition(mini)
    assert A.core_keep(core, ones, 3) == []                                 # eine Clique der Größe 4 bräuchte Kernzahl >= 3
    assert A.core_keep(core, ones, 2) == [0, 1, 2]                          # Größe 3 braucht Kernzahl >= 2
    assert A.core_keep(core, ones, 0) == [0, 1, 2, 3, 4]
    assert A.core_keep(core, (1, 1, 1, 9, 1), 3) == [0, 1, 2, 3, 4]         # Gewicht 9: schon ein einzelner Knoten kann Wert > 3 haben
    assert A.core_keep(core, (1, 1, 1, 9, 1), 9) == [0, 1, 2, 3]             # Wert > 9 braucht mindestens 2 Knoten (9 // 9 + 1), also Kernzahl >= 1: nur der isolierte Knoten 4 fällt weg


def test_greedy_color_classes_by_hand(mini):
    order, numbers, lookups = A.greedy_color_classes([2, 0, 1, 3, 4], mini)
    assert order == [2, 4, 0, 3, 1] and numbers == [1, 1, 2, 2, 3] and lookups == 6


def test_greedy_color_classes_are_independent_sets_and_cover_everything():
    g = S.random_graph(25, 50, 3)
    order, numbers, _ = A.greedy_color_classes(list(range(25)), g.adj)
    assert sorted(order) == list(range(25))
    assert numbers == sorted(numbers)
    for c in set(numbers):
        members = [v for v, k in zip(order, numbers) if k == c]
        assert all(b not in g.adj[a] for a in members for b in members if a != b)


def test_color_prefix_bounds_by_hand(mini, ones):
    order, numbers = [2, 4, 0, 3, 1], [1, 1, 2, 2, 3]
    assert A.color_prefix_bounds(order, numbers, ones) == [1, 1, 2, 2, 3]
    assert A.color_prefix_bounds(order, numbers, W_VALUE) == [1, 1, 2, 10, 11]


def test_simple_bound_adds_the_weights_of_all_candidates(mini, ones):
    assert A.simple_bound(0, [0, 1, 2, 3, 4], ones) == 5
    assert A.simple_bound(2, [3], W_VALUE) == 11


def test_is_clique_and_value(mini):
    assert A.is_clique(mini, (0, 1, 2)) and not A.is_clique(mini, (0, 1, 3)) and A.is_clique(mini, ())
    assert A.clique_value(W_VALUE, (2, 3)) == 10


# --- Komposition auf den Mini-Instanzen -------------------------------------------------------------------------------------------------------

def test_mini_color_with_degree_order_by_hand(mini, ones):
    r = A.largest_clique(mini, ones, "color", "degree")
    assert r.clique == (0, 1, 2) and r.value == 3
    assert (r.nodes, r.lookups, r.prep_lookups) == (3, 12, 0)


def test_mini_simple_with_index_order_by_hand(mini, ones):
    r = A.largest_clique(mini, ones, "simple", "index")
    assert r.clique == (0, 1, 2) and r.value == 3
    assert (r.nodes, r.lookups) == (6, 8)


def test_mini_prune_proves_the_greedy_clique_without_any_search(mini, ones):
    r = A.largest_clique(mini, ones, "color", "degree", prune=True)
    assert r.proven_by_prune and r.kept == 0 and r.nodes == 0
    assert r.clique == (0, 1, 2) and r.value == 3
    assert r.prep_lookups == 14 + 8 and r.lookups == 22                    # Greedy 14 plus 2m = 8 für die Kernzahlen


def test_weighted_mini_prefers_the_heavy_pair(mini):
    for bound in ("simple", "color"):
        for order in ("index", "degree", "degeneracy"):
            r = A.largest_clique(mini, W_VALUE, bound, order)
            assert r.clique == (2, 3) and r.value == 10, (bound, order)


def test_pentagon_has_clique_number_two_but_the_color_bound_stays_at_three(pentagon):
    ones = (1,) * 5
    assert A.largest_clique(pentagon, ones).value == 2
    assert A.root_color_bound(pentagon, ones, "index") == 3
    assert A.root_color_bound(pentagon, (1, 1, 1, 1, 1), "degree") == 3


def test_complete_graph_k4_is_found_without_branching_on_the_exclusion_side(k4):
    r = A.largest_clique(k4, (1,) * 4, "color", "index")
    assert r.value == 4 and r.clique == (0, 1, 2, 3) and r.nodes == 4


def test_history_is_increasing_and_ends_with_the_value(mini, ones):
    r = A.largest_clique(mini, ones, "simple", "index")
    values = [v for _, v in r.history]
    assert values == sorted(set(values)) and values[-1] == r.value


def test_prune_starts_the_history_with_the_greedy_value():
    g = S.random_graph(30, 60, 2)
    ones = (1,) * 30
    r = A.largest_clique(g.adj, ones, "color", "degree", prune=True)
    assert r.history[0] == (0, r.greedy_value)


def test_trace_events_and_limits(mini, ones):
    r = A.largest_clique(mini, ones, "color", "degree", trace_limit=50)
    kinds = [e.kind for e in r.trace]
    assert kinds.count("improve") == 1 and "call" in kinds and "cut" in kinds
    first = r.trace[0]
    assert first.kind == "call" and first.R == () and first.P == (2, 4, 0, 3, 1) and first.classes == (1, 1, 2, 2, 3) and first.bound == 3
    short = A.largest_clique(mini, ones, "simple", "index", trace_limit=3)
    assert len(short.trace) == 3 and short.trace_truncated


def test_budget_aborts_and_keeps_the_best_found(mini, ones):
    r = A.largest_clique(mini, ones, "simple", "index", budget=2)
    assert r.aborted and r.nodes == 3
    assert r.value >= 1 and A.is_clique(mini, r.clique)
    assert not A.largest_clique(mini, ones, "simple", "index", budget=6).aborted


def test_empty_graph_and_single_vertex():
    e = A.largest_clique(S.adjacency_from_edges(0, []), ())
    assert e.clique == () and e.value == 0 and e.nodes == 0
    for bound in ("simple", "color"):
        one = A.largest_clique(S.adjacency_from_edges(1, []), (1,), bound)
        assert one.clique == (0,) and one.value == 1
        three = A.largest_clique(S.adjacency_from_edges(3, []), (1, 1, 1), bound, "index")
        assert three.value == 1 and len(three.clique) == 1


def test_invalid_arguments_raise(mini, ones):
    with pytest.raises(ValueError):
        A.largest_clique(mini, ones, "magic")
    with pytest.raises(ValueError):
        A.largest_clique(mini, ones, "color", "magic")


# --- Brute Force als Referenz -----------------------------------------------------------------------------------------------------------------

def test_brute_force_on_mini(mini, ones):
    assert A.brute_force_max_clique(mini, ones) == (3, [(0, 1, 2)])
    assert A.brute_force_max_clique(mini, W_VALUE) == (10, [(2, 3)])
    assert A.brute_force_max_independent_set(mini, ones) == 3                # {0, 3, 4}
    assert A.brute_force_max_independent_set(S.complement(mini), ones) == 3  # = ω


@pytest.mark.parametrize("seed", range(30))
def test_all_configurations_equal_brute_force_on_random_graphs(seed):
    n = 3 + seed % 11
    g = S.random_graph(n, 20 + 15 * (seed % 5), seed)
    for objective in ("size", "value"):
        w = S.make_weights(n, seed, objective)
        value, optimal = A.brute_force_max_clique(g.adj, w)
        for bound in ("simple", "color"):
            for order in ("index", "degree", "degeneracy"):
                for prune in (False, True):
                    r = A.largest_clique(g.adj, w, bound, order, prune)
                    assert r.value == value, (seed, objective, bound, order, prune)
                    assert A.is_clique(g.adj, r.clique) and A.clique_value(w, r.clique) == r.value
                    assert r.clique in optimal
