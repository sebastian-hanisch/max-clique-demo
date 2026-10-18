"""Figuren: jede lässt sich für jeden Schritt bauen, die Zustandsfarben stimmen, alle Achsen sind fest."""

import mxc_algorithm as A
import mxc_constants as C
import mxc_evaluation as ev
import mxc_scenario as S
import mxc_visualization as V


def _node_trace(fig):
    return next(t for t in fig.data if t.mode == "markers+text")


def _all_axes_fixed(fig):
    return fig.layout.xaxis.fixedrange and fig.layout.yaxis.fixedrange


def test_graph_figure_builds_for_every_event_of_both_bounds_and_both_objectives():
    for bound in ("simple", "color"):
        for objective in ("size", "value"):
            a = ev.analyse(ev.Settings(n=10, bound=bound, objective=objective))
            for e in a.result.trace:
                fig = V.build_graph_figure(a.graph, a.weights, event=e, best=e.best_clique)
                assert len(_node_trace(fig).x) == a.graph.n and _all_axes_fixed(fig)


def test_node_colours_follow_r_classes_and_best_clique(mini):
    g = S.Graph(5, mini, S.circle_positions(list(range(5))), tuple(str(i) for i in range(5)), "random")
    res = A.largest_clique(mini, (1,) * 5, "color", "degree", trace_limit=20)
    first = res.trace[0]                                          # P = [2, 4, 0, 3, 1] in den Klassen 1, 1, 2, 2, 3
    colors = list(_node_trace(V.build_graph_figure(g, event=first)).marker.color)
    assert colors[2] == colors[4] == V.class_color(1) and colors[0] == colors[3] == V.class_color(2) and colors[1] == V.class_color(3)
    improve = next(e for e in res.trace if e.kind == "improve")
    fig = V.build_graph_figure(g, event=improve, best=improve.best_clique)
    colors = list(_node_trace(fig).marker.color)
    assert colors[0] == colors[1] == colors[2] == C.COLOR_R and colors[3] == colors[4] == C.COLOR_IDLE
    assert list(_node_trace(fig).marker.line.color)[:3] == [C.COLOR_BEST] * 3


def test_simple_bound_candidates_have_one_colour(mini):
    g = S.Graph(5, mini, S.circle_positions(list(range(5))), tuple(str(i) for i in range(5)), "random")
    res = A.largest_clique(mini, (1,) * 5, "simple", "index", trace_limit=20)
    colors = list(_node_trace(V.build_graph_figure(g, event=res.trace[0])).marker.color)
    assert colors == [C.COLOR_P] * 5


def test_class_colours_cycle_beyond_the_palette():
    assert V.class_color(1) == V.class_color(len(C.CLASS_PALETTE) + 1)


def test_static_figure_highlights_the_best_clique(mini):
    g = S.Graph(5, mini, S.circle_positions(list(range(5))), tuple(str(i) for i in range(5)), "random")
    fig = V.build_graph_figure(g, best=(0, 1, 2))
    assert list(_node_trace(fig).marker.line.color)[:3] == [C.COLOR_BEST] * 3


def test_history_figure_for_a_run_with_and_without_improvement(mini):
    res = A.largest_clique(mini, (1,) * 5, "simple", "index")
    fig = V.build_history_figure(res)
    assert _all_axes_fixed(fig) and len(fig.data) == 2
    assert len(V.build_history_figure(A.largest_clique(S.adjacency_from_edges(0, []), ())).data) == 0


def test_experiment_figures_build_and_lock_their_axes():
    sweep = ev.density_sweep("random", densities=(10, 90), seeds=(1,))
    figs = [V.build_sweep_figure(sweep, "nodes"), V.build_sweep_figure(sweep, "lookups"), V.build_structure_figure(ev.structure_rows(seeds=(1,))),
            V.build_core_figure(ev.core_rows(seeds=(1,))), V.build_prep_cost_figure(ev.core_rows(seeds=(1,))), V.build_greedy_figure(ev.greedy_rows(seeds=range(3)))]
    assert all(_all_axes_fixed(f) for f in figs)


def test_sweep_figure_marks_aborted_medians():
    rows = ev.density_sweep("windows", densities=(90,), seeds=(1, 2), budget=300)
    fig = V.build_sweep_figure(rows, "nodes")
    assert any(t.marker is not None and t.marker.symbol == "square-open" for t in fig.data)
