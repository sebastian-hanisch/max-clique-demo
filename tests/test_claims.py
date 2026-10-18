"""Jede Zahl aus README und App wird hier nachgerechnet (DEMO-PLAYBOOK §4: erst messen, dann Text schreiben).
Alle Zählwerte (Knoten, Adjazenzabfragen) sind ganzzahlig und plattformunabhängig exakt; Verhältnisse mit enger Toleranz (Rundung)."""

import math

import pytest

import mxc_algorithm as A
import mxc_constants as C
import mxc_evaluation as ev
import mxc_scenario as S


def _preset(name):
    p = C.PRESETS[name]
    return ev.analyse(ev.Settings(graph_type=p["type"], n=p["n"], density=p["density"], seed=p["seed"], bound=p["bound"], order=p["order"], prune=p["prune"], objective=p["objective"]))


# --- Standardfall: 24 Sendungen, 50 %, Zufallsregeln, Seed 35, Färbung, Startordnung Grad -------------------------------------------------------

def test_default_case_numbers():
    a = ev.analyse(ev.Settings())
    assert a.value == 6 and a.result.clique == (11, 14, 19, 20, 21, 23)
    assert (a.color.nodes, a.color.lookups) == (12, 405) and (a.simple.nodes, a.simple.lookups) == (374, 1502)
    assert (a.pruned.nodes, a.pruned.lookups, a.pruned.kept, a.pruned.prep_lookups) == (7, 1441, 24, 1067)
    assert a.result.greedy_value == 6 and a.result.degeneracy == 10 and a.root_bound == 8
    assert math.isclose(ev.factor(a.simple.nodes, a.color.nodes), 31.17, abs_tol=0.01) and math.isclose(ev.factor(a.simple.lookups, a.color.lookups), 3.71, abs_tol=0.01)


# --- Presets ----------------------------------------------------------------------------------------------------------------------------------

def test_preset_numbers():
    a = _preset("Lehrbeispiel (klein)")
    assert a.value == 4 and (a.simple.nodes, a.simple.lookups, a.color.nodes, a.color.lookups) == (21, 59, 4, 40)
    a = _preset("Dicht: die Färbung rettet")
    assert a.value == 13 and (a.simple.nodes, a.simple.lookups, a.color.nodes, a.color.lookups) == (28507, 179551, 88, 8612)
    assert math.isclose(ev.factor(28507, 88), 323.94, abs_tol=0.01) and math.isclose(ev.factor(179551, 8612), 20.85, abs_tol=0.01)
    a = _preset("Dünn: kaum Suche nötig")
    assert a.value == 4 and (a.simple.nodes, a.color.nodes, a.color.lookups) == (253, 9, 1184) and a.result.greedy_value == 3
    a = _preset("Zeitfenster mit Vorverarbeitung")
    assert a.value == 23 and a.pruned.proven_by_prune and (a.pruned.nodes, a.pruned.lookups, a.pruned.kept) == (0, 13496, 0)
    assert (a.color.nodes, a.color.lookups) == (23, 6848) and (a.simple.nodes, a.simple.lookups) == (96, 3486)
    a = _preset("Klassenregeln mit Wert")
    assert a.value == 58 and (a.simple.nodes, a.color.nodes) == (3710, 44) and a.result.greedy_value == 58


# --- Experiment 1: Dichte-Sweep ---------------------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def sweeps():
    return {gt: ev.density_sweep(gt) for gt in C.GRAPH_TYPES}


def test_sweep_verdicts(sweeps):
    expected = {"random": (20, 20.36, 90, 1250.02, 2.0, 99.12), "windows": (20, 13.89, 90, 1875.03, 1.89, 98.92), "classes": (10, 55.0, 80, 2000.03, 2.73, 204.67)}
    for gt, (wd, wf, bd, bf, wl, bl) in expected.items():
        v = ev.sweep_verdict(sweeps[gt])
        assert (v["worst_density"], v["best_density"]) == (wd, bd), gt
        assert math.isclose(v["worst_node_factor"], wf, abs_tol=0.01) and math.isclose(v["best_node_factor"], bf, abs_tol=0.01), gt
        assert math.isclose(v["worst_lookup_factor"], wl, abs_tol=0.01) and math.isclose(v["best_lookup_factor"], bl, abs_tol=0.01), gt
        assert v["any_aborted"] is True


def test_random_sweep_selected_rows(sweeps):
    by = {r["density"]: r for r in sweeps["random"]}
    assert by[10]["nodes"]["simple"] == 133 and by[10]["nodes"]["color"] == 4 and (by[10]["lookups"]["simple"], by[10]["lookups"]["color"]) == (896, 448)
    assert by[90]["nodes"]["simple"] == C.SWEEP_BUDGET + 1 and by[90]["aborted"]["simple"] == 5 and by[90]["nodes"]["color"] == 48
    assert (by[90]["lookups"]["simple"], by[90]["lookups"]["color"]) == (446317, 4503)
    assert [r["omega"] for r in sweeps["random"]] == [3, 4, 5, 6, 7, 8, 10, 13, 18]
    assert (by[50]["nodes"]["color_index"], by[50]["nodes"]["color"], by[50]["nodes"]["color_degeneracy"]) == (28, 26, 32)       # die Startordnung ändert wenig und uneinheitlich


def test_the_colour_bound_needs_fewer_lookups_than_the_simple_bound_at_every_density(sweeps):
    losses = [(gt, r["density"]) for gt, rows in sweeps.items() for r in rows if r["lookups"]["color"] > r["lookups"]["simple"]]
    assert losses == []
    windows90 = next(r for r in sweeps["windows"] if r["density"] == 90)
    assert (windows90["lookups"]["color_index"], windows90["lookups"]["color"]) == (6044, 6174)       # die Startordnung ändert die Abfragen mäßig, nicht einheitlich


def test_only_the_simple_bound_ever_hits_the_budget_in_the_sweeps(sweeps):
    for rows in sweeps.values():
        for r in rows:
            assert r["aborted"]["color"] == r["aborted"]["color_index"] == r["aborted"]["color_degeneracy"] == 0
    assert all(r["aborted"]["simple"] == 0 for r in sweeps["random"] if r["density"] <= 70)


# --- Experiment 2: Strukturen ----------------------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def structures():
    return {r["name"]: r for r in ev.structure_rows()}


def test_structure_table_numbers(structures):
    s = structures
    dense = s["Zufall dicht, n = 60, 70 %"]
    assert (dense["omega"], dense["degeneracy"], dense["nodes"]["simple"], dense["nodes"]["color"]) == (12, 34, 48470, 213)
    assert (dense["lookups"]["simple"], dense["lookups"]["color"], dense["aborted"]) == (318629, 26322, 1)
    sparse = s["Zufall sehr dünn, n = 1500, 1 %"]
    assert (sparse["omega"], sparse["degeneracy"], sparse["nodes"]["simple"], sparse["nodes"]["color"]) == (3, 10, 19492, 791)
    assert (sparse["lookups"]["simple"], sparse["lookups"]["color"], sparse["aborted"]) == (1191416, 1292933, 0)
    tree, sf = s["Baum, n = 500"], s["skalenfrei, n = 2000, m = 5"]
    assert (tree["lookups"]["simple"], tree["lookups"]["color"]) == (125324, 77257) and (sf["lookups"]["simple"], sf["lookups"]["color"]) == (2146461, 1102258)
    mm = s["Moon–Moser, n = 30"]
    assert (mm["omega"], mm["nodes"]["color"], mm["lookups"]["color"], mm["aborted"]) == (10, 10, 815, 3)


def test_lookup_changes_in_percent_and_the_single_structure_where_colour_costs_more(structures):
    expected = {"Zufall dicht, n = 60, 70 %": -91.7, "Zeitfenster, n = 100, 50 %": -98.0, "Klassenregeln, n = 80, 50 %": -98.8, "Moon–Moser, n = 30": -99.4,
                "Baum, n = 500": -38.4, "skalenfrei, n = 2000, m = 5": -48.6, "Zufall dünn, n = 500, 5 %": -9.3, "Zufall sehr dünn, n = 1500, 1 %": 8.5}
    assert set(structures) == set(expected)
    for name, value in expected.items():
        assert math.isclose(ev.lookup_change(structures[name]), value, abs_tol=0.05), name
    assert [n for n, r in structures.items() if ev.lookup_change(r) > 0] == ["Zufall sehr dünn, n = 1500, 1 %"]
    assert math.isclose(ev.factor(19492, 791), 24.64, abs_tol=0.01)
    thin = structures["Zufall dünn, n = 500, 5 %"]
    assert (thin["nodes"]["simple"], thin["nodes"]["color"]) == (10945, 288) and math.isclose(ev.factor(10945, 288), 38.0, abs_tol=0.05)


# --- Experiment 3: Kernzahl-Vorverarbeitung ---------------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def core():
    return {r["name"]: r for r in ev.core_rows()}


def test_core_table_numbers(core):
    expect = {"Zufall, n = 40, 50 %": (7, 14, 8, 6, 40, 0, 3839, 2365), "Zufall dicht, n = 60, 70 %": (12, 34, 23, 11, 60, 0, 34320, 26483),
              "Zeitfenster, n = 100, 50 %": (36, 35, 0, 34, 56, 0, 67415, 25955), "Klassenregeln, n = 80, 50 %": (24, 30, 7, 24, 67, 1, 38189, 9684),
              "Baum, n = 500": (2, 1, 0, 2, 0, 3, 2026, 83473), "skalenfrei, n = 2000, m = 5": (5, 5, 1, 5, 2000, 0, 785451, 1197605),
              "Zufall dünn, n = 500, 5 %": (4, 18, 15, 3, 500, 0, 192925, 179204), "Zufall sehr dünn, n = 1500, 1 %": (3, 10, 8, 3, 1500, 0, 1325821, 1302598)}
    assert set(core) == set(expect)
    for name, (omega, d, gap, greedy, kept, proven, with_, without) in expect.items():
        r = core[name]
        assert (r["omega"], r["degeneracy"], r["gap"], r["greedy"], r["kept"], r["proven"], r["lookups_with"], r["lookups_without"]) == (omega, d, gap, greedy, kept, proven, with_, without), name


def test_the_filter_removes_vertices_only_where_the_gap_is_at_most_seven_and_not_everywhere_there(core):
    removed = {n for n, r in core.items() if r["kept"] < r["n"]}
    assert removed == {"Zeitfenster, n = 100, 50 %", "Klassenregeln, n = 80, 50 %", "Baum, n = 500"}
    assert max(core[n]["gap"] for n in removed) == 7
    assert all(core[n]["gap"] >= 8 for n in core if n not in removed and n != "skalenfrei, n = 2000, m = 5")
    assert core["skalenfrei, n = 2000, m = 5"]["gap"] == 1 and core["skalenfrei, n = 2000, m = 5"]["kept"] == 2000


def test_the_preprocessing_lowers_the_lookups_in_only_two_structures(core):
    assert sorted(n for n, r in core.items() if r["lookups_with"] < r["lookups_without"]) == ["Baum, n = 500", "skalenfrei, n = 2000, m = 5"]
    tree, windows = core["Baum, n = 500"], core["Zeitfenster, n = 100, 50 %"]
    assert math.isclose(tree["lookups_without"] / tree["lookups_with"], 41.2, abs_tol=0.05)
    assert math.isclose(windows["lookups_with"] / windows["lookups_without"], 2.6, abs_tol=0.05)


# --- Experiment 4: Greedy und Gewichte ---------------------------------------------------------------------------------------------------------

def test_greedy_rows():
    rows = {r["name"]: r for r in ev.greedy_rows()}
    expect = {"Zufall, n = 40, 50 %": (12, 0.4, 1), "Zufall, n = 60, 70 %": (4, 1.2, 2), "Zeitfenster, n = 80, 50 %": (6, 1.3, 4),
              "Klassenregeln, n = 80, 50 %": (11, 3.4, 18), "skalenfrei, n = 500, m = 5": (18, 0.1, 1)}
    assert set(rows) == set(expect)
    for name, (exact, mean_gap, max_gap) in expect.items():
        r = rows[name]
        assert r["runs"] == 20 and r["exact"] == exact and r["max_gap"] == max_gap and math.isclose(r["mean_gap"], mean_gap, abs_tol=0.05), name


def test_weighted_rows():
    rows = {(r["n"], r["density"]): r for r in ev.weighted_rows()}
    assert (rows[(30, 50)]["simple"], rows[(30, 50)]["color"]) == (449, 59) and (rows[(30, 70)]["simple"], rows[(30, 70)]["color"]) == (1325, 72)
    assert (rows[(40, 50)]["simple"], rows[(40, 50)]["color"]) == (936, 68) and (rows[(40, 70)]["simple"], rows[(40, 70)]["color"]) == (4094, 174)
    assert all(r["aborted"] == 0 and r["color_lookups"] < r["simple_lookups"] for r in rows.values())
    assert math.isclose(ev.factor(4094, 174), 23.53, abs_tol=0.01) and math.isclose(ev.factor(449, 59), 7.61, abs_tol=0.01)


def test_greedy_misses_the_weighted_optimum_on_the_mini_instance(mini):
    w = (1, 1, 1, 9, 1)
    assert A.greedy_clique(mini, w)[1] == 3 and A.largest_clique(mini, w).value == 10


# --- Brücke -------------------------------------------------------------------------------------------------------------------------------------

def test_complement_bridge_on_the_default_small_instance():
    cc = ev.complement_check(ev.Settings())
    assert (cc["n"], cc["omega"], cc["alpha_conflict"], cc["omega_conflict"], cc["alpha"]) == (14, 4, 4, 5, 5) and cc["equal"] and cc["equal_back"]


# --- Rechengrenzen --------------------------------------------------------------------------------------------------------------------------------

def test_budgets_and_limits_as_documented():
    assert (C.NODE_BUDGET, C.SWEEP_BUDGET, C.TRACE_LIMIT, C.SWEEP_N, C.CHECK_N) == (200_000, 60_000, 400, 40, 14)
    assert (C.N_MIN, C.N_MAX, C.DENSITY_MIN, C.DENSITY_MAX, C.W_MIN, C.W_MAX) == (6, 60, 5, 95, 1, 9)
    g = S.random_graph(60, 95, 35)
    assert A.largest_clique(g.adj, (1,) * 60, "simple", "degree", budget=C.NODE_BUDGET).aborted
