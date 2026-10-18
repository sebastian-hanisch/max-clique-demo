"""Zweig-Tests (Nullspalten-Lehre): jede Schranke, jede Startordnung, die Vorverarbeitung und die Gewichte weichen auf mindestens einer Instanz
von ihrer Nachbarvariante ab; die Invarianten der Schranken gelten auf jedem Knoten; die Rechengrenzen greifen."""

import mxc_algorithm as A
import mxc_constants as C
import mxc_evaluation as ev
import mxc_scenario as S


def _g(n=30, d=50, seed=2):
    g = S.random_graph(n, d, seed)
    return g.adj, (1,) * n


def test_the_colour_bound_differs_from_the_simple_bound_on_a_dense_graph():
    adj, w = _g(25, 70)
    assert A.largest_clique(adj, w, "color").nodes < A.largest_clique(adj, w, "simple").nodes


def test_each_start_order_differs_from_the_others_on_at_least_one_instance():
    for bound in ("simple", "color"):
        seen = {o: [A.largest_clique(*_g(30, 60, s), bound, o).nodes for s in range(12)] for o in C.ORDERS}
        assert seen["index"] != seen["degree"] and seen["degree"] != seen["degeneracy"] and seen["index"] != seen["degeneracy"], bound


def test_the_weighted_search_differs_from_the_unweighted_one():
    g = S.random_graph(30, 60, 4)
    ones = (1,) * 30
    w = S.make_weights(30, 4, "value")
    a, b = A.largest_clique(g.adj, ones, "color"), A.largest_clique(g.adj, w, "color")
    assert a.value != b.value and (a.nodes, a.lookups) != (b.nodes, b.lookups)


def test_the_weighted_colour_bound_prunes_more_than_the_unweighted_count_would():
    """Die gewichtete Schranke (Summe der Klassenmaxima) ist höchstens so groß wie das Gesamtgewicht und bei Gewichten > 1 oft deutlich kleiner als Klassenzahl mal größtes Gewicht."""
    g = S.random_graph(25, 60, 3)
    w = S.make_weights(25, 3, "value")
    order, numbers, _ = A.greedy_color_classes(list(range(25)), g.adj)
    bound = A.color_prefix_bounds(order, numbers, w)[-1]
    assert bound <= sum(w) and bound < max(numbers) * max(w)


def test_pruning_removes_vertices_on_a_window_graph_and_proves_the_greedy_clique_on_a_tree():
    g = S.window_graph(100, 50, 100000)
    r = A.largest_clique(g.adj, (1,) * 100, "color", "degeneracy", prune=True)
    assert r.kept < 100 and r.value == A.largest_clique(g.adj, (1,) * 100, "color", "degeneracy").value
    t = S.tree_graph(200, 1)
    rt = A.largest_clique(t.adj, (1,) * 200, "color", "degeneracy", prune=True)
    assert rt.proven_by_prune and rt.nodes == 0 and rt.value == 2


def test_pruning_keeps_every_vertex_of_a_dense_random_graph_and_still_finds_the_optimum():
    adj, w = _g(30, 70)
    r = A.largest_clique(adj, w, "color", "degree", prune=True)
    assert r.kept == 30 and not r.proven_by_prune and r.value == A.largest_clique(adj, w).value


def test_the_greedy_tie_break_on_weights_is_effective():
    adj = S.adjacency_from_edges(4, [(0, 1), (2, 3)])
    assert A.greedy_clique(adj, (1, 1, 1, 5))[0] != A.greedy_clique(adj, (5, 1, 1, 1))[0]


def test_bound_invariant_at_every_node_the_event_bound_is_at_least_the_best_clique_inside_the_subtree():
    """Auf jedem Aufruf-Ereignis gilt: Schranke >= Wert von R plus Wert der besten Clique innerhalb der Kandidaten P (mit Brute Force an kleinen Instanzen geprüft)."""
    for seed in range(12):
        g = S.random_graph(12, 55, seed)
        w = S.make_weights(12, seed, "value")
        for bound in ("simple", "color"):
            res = A.largest_clique(g.adj, w, bound, "degree", trace_limit=400)
            for e in res.trace:
                if e.kind != "call":
                    continue
                best_ext = max([sum(w[x] for x in c) for c in _cliques_within(g.adj, e.P)] + [0])
                assert e.bound >= A.clique_value(w, e.R) + best_ext, (seed, bound, e.R)


def _cliques_within(adj, vertices):
    """Alle Cliquen innerhalb von `vertices` (Aufzählen aller Teilmengen, nur für kleine Mengen)."""
    vs = list(vertices)
    out = []
    for mask in range(1 << len(vs)):
        members = [vs[i] for i in range(len(vs)) if mask >> i & 1]
        if A.is_clique(adj, members):
            out.append(members)
    return out


def test_the_colour_bound_never_exceeds_the_simple_bound_at_the_root():
    for seed in range(20):
        g = S.random_graph(8 + seed % 20, 20 + 10 * (seed % 7), seed)
        w = S.make_weights(g.n, seed, "value")
        assert A.root_color_bound(g.adj, w, "degree") <= A.simple_bound(0, list(range(g.n)), w)


def test_the_node_budget_aborts_the_simple_bound_on_a_dense_graph_but_not_the_colour_bound():
    g = S.random_graph(C.N_MAX, C.DENSITY_MAX, 35)
    w = (1,) * C.N_MAX
    simple = A.largest_clique(g.adj, w, "simple", "degree", budget=C.NODE_BUDGET)
    assert simple.aborted and simple.nodes == C.NODE_BUDGET + 1 and A.is_clique(g.adj, simple.clique) and simple.value >= 1
    assert not A.largest_clique(g.adj, w, "color", "degree", budget=C.NODE_BUDGET).aborted


def test_analysis_takes_the_value_from_a_finished_variant_when_the_chosen_one_aborted():
    a = ev.analyse(ev.Settings(n=C.N_MAX, density=C.DENSITY_MAX, bound="simple"))
    assert a.result.aborted and a.complete and a.value == a.color.value


def test_trace_limit_applies_in_the_analysis_and_every_event_kind_occurs():
    a = ev.analyse(ev.Settings(n=40, density=70, bound="simple"))
    assert len(a.result.trace) == C.TRACE_LIMIT and a.result.trace_truncated
    kinds = {e.kind for e in A.largest_clique(*_g(14, 50, 3), "color", "degree", trace_limit=400).trace}
    assert kinds >= {"call", "cut", "improve"}
    kinds_simple = set()
    for seed in range(10):
        kinds_simple |= {e.kind for e in A.largest_clique(*_g(14, 50, seed), "simple", "index", trace_limit=400).trace}
    assert kinds_simple >= {"call", "cut", "improve", "leaf"}


def test_sweep_marks_aborted_runs_and_uses_the_budget_as_a_lower_bound():
    rows = ev.density_sweep("windows", seeds=(1, 2), densities=(90,), budget=500)
    assert rows[0]["aborted"]["simple"] == 2 and rows[0]["nodes"]["simple"] == 501 and rows[0]["aborted"]["color"] == 0


def test_every_configuration_runs_on_every_graph_type_at_the_slider_edges():
    for gt in C.GRAPH_TYPES:
        for n in (C.N_MIN, C.N_MAX):
            for d in (C.DENSITY_MIN, C.DENSITY_MAX):
                for objective in C.OBJECTIVES:
                    a = ev.analyse(ev.Settings(graph_type=gt, n=n, density=d, objective=objective, prune=True))
                    assert a.complete and not a.color.aborted and not a.pruned.aborted, (gt, n, d, objective)
