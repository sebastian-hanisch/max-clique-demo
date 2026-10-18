"""Auswertung: Einstellungen, Analyse der Hauptansicht, Sweeps und Vergleichstabellen (alle Zahlen kommen aus diesen Funktionen, nie von Hand)."""

import statistics
from dataclasses import dataclass

import mxc_algorithm as A
import mxc_constants as C
import mxc_scenario as S


@dataclass(frozen=True)
class Settings:
    """Alle Regler der Seitenleiste. Immer mit Schlüsselwörtern bauen (ein eingefügtes Feld verschob früher still Werte)."""
    graph_type: str = C.DEFAULT_TYPE
    n: int = C.DEFAULT_N
    density: int = C.DEFAULT_DENSITY
    seed: int = C.DEFAULT_SEED
    bound: str = C.DEFAULT_BOUND
    order: str = C.DEFAULT_ORDER
    prune: bool = False
    objective: str = C.DEFAULT_OBJECTIVE


@dataclass(frozen=True)
class Analysis:
    settings: Settings
    graph: S.Graph
    weights: tuple
    result: A.Result            # die gewählte Konfiguration, mit Schritt-Trace
    simple: A.Result            # Vergleich: einfache Schranke, gleiche Startordnung, ohne Vorverarbeitung
    color: A.Result             # Vergleich: Färbungsschranke, gleiche Startordnung, ohne Vorverarbeitung
    pruned: A.Result            # Vergleich: Färbungsschranke mit Vorverarbeitung
    value: int                  # größter Wert (aus einem fertig gelaufenen Verfahren), None wenn keines fertig wurde
    complete: bool
    root_bound: int             # Färbungsschranke an der Wurzel (alle Sendungen gefärbt)


def build_instance(settings):
    g = S.build_graph(settings.graph_type, settings.n, settings.density, settings.seed)
    return g, S.make_weights(g.n, settings.seed, settings.objective)


def analyse(settings, node_budget=C.NODE_BUDGET):
    g, w = build_instance(settings)
    chosen = A.largest_clique(g.adj, w, settings.bound, settings.order, settings.prune, budget=node_budget, trace_limit=C.TRACE_LIMIT)
    simple = A.largest_clique(g.adj, w, "simple", settings.order, False, budget=node_budget)
    color = A.largest_clique(g.adj, w, "color", settings.order, False, budget=node_budget)
    pruned = A.largest_clique(g.adj, w, "color", settings.order, True, budget=node_budget)
    finished = [r for r in (chosen, color, pruned, simple) if not r.aborted]
    value = finished[0].value if finished else None
    return Analysis(settings, g, w, chosen, simple, color, pruned, value, bool(finished), A.root_color_bound(g.adj, w, settings.order))


def factor(a, b):
    """Wie viel mal so viel a gegenüber b (b = 0: unendlich)."""
    return a / b if b else float("inf")


def med(xs):
    return statistics.median(xs)


# --- Experiment 1: Dichte-Sweep ---------------------------------------------------------------------------------------------------------------

SWEEP_CONFIGS = (("simple", "simple", "degree"), ("color_index", "color", "index"), ("color", "color", "degree"), ("color_degeneracy", "color", "degeneracy"))


def density_sweep(graph_type, n=C.SWEEP_N, densities=C.SWEEP_DENSITIES, seeds=C.SWEEP_SEEDS, budget=C.SWEEP_BUDGET):
    """Je Dichte der Median über die festen Instanzen: Knoten und Adjazenzabfragen der einfachen Schranke (Startordnung Grad) und der Färbungsschranke mit drei Startordnungen.
    `aborted[k]` = in wie vielen Instanzen die Konfiguration das Budget erreicht hat (dann zählt der Lauf mit dem Budget als Untergrenze)."""
    rows = []
    for d in densities:
        nodes = {k: [] for k, _, _ in SWEEP_CONFIGS}
        looks = {k: [] for k, _, _ in SWEEP_CONFIGS}
        aborted = {k: 0 for k, _, _ in SWEEP_CONFIGS}
        omegas = []
        for seed in seeds:
            g = S.build_graph(graph_type, n, d, seed)
            w = (1,) * g.n
            ref = None
            for key, bound, order in SWEEP_CONFIGS:
                r = A.largest_clique(g.adj, w, bound, order, False, budget=budget)
                nodes[key].append(r.nodes)
                looks[key].append(r.lookups)
                aborted[key] += int(r.aborted)
                if not r.aborted and ref is None:
                    ref = r.value
            omegas.append(ref if ref is not None else 0)
        rows.append({"density": d, "omega": med(omegas), "aborted": aborted,
                     "nodes": {k: med(v) for k, v in nodes.items()}, "lookups": {k: med(v) for k, v in looks.items()}})
    return rows


def sweep_verdict(rows):
    """Aussage zum Dichte-Sweep, aus den Zeilen berechnet: größter und kleinster Faktor der Knotenzahl einfach gegen Färbung (beide Startordnung Grad) sowie derselbe Faktor bei den Adjazenzabfragen."""
    node_f = [(r["density"], factor(r["nodes"]["simple"], r["nodes"]["color"])) for r in rows]
    look_f = [(r["density"], factor(r["lookups"]["simple"], r["lookups"]["color"])) for r in rows]
    best_n, worst_n = max(node_f, key=lambda t: t[1]), min(node_f, key=lambda t: t[1])
    best_l, worst_l = max(look_f, key=lambda t: t[1]), min(look_f, key=lambda t: t[1])
    return {"best_density": best_n[0], "best_node_factor": best_n[1], "worst_density": worst_n[0], "worst_node_factor": worst_n[1],
            "best_lookup_factor": best_l[1], "worst_lookup_density": worst_l[0], "worst_lookup_factor": worst_l[1],
            "any_aborted": any(r["aborted"]["simple"] for r in rows)}


# --- Experiment 2 und 3: feste Strukturen -------------------------------------------------------------------------------------------------------

STRUCTURES = (
    ("Zufall dicht, n = 60, 70 %", lambda seed: S.random_graph(60, 70, seed)),
    ("Zeitfenster, n = 100, 50 %", lambda seed: S.window_graph(100, 50, seed)),
    ("Klassenregeln, n = 80, 50 %", lambda seed: S.class_graph(80, 50, seed)),
    ("Moon–Moser, n = 30", lambda seed: S.moon_moser_graph(10)),
    ("Baum, n = 500", lambda seed: S.tree_graph(500, seed)),
    ("skalenfrei, n = 2000, m = 5", lambda seed: S.scale_free_graph(2000, 5, seed)),
    ("Zufall dünn, n = 500, 5 %", lambda seed: S.random_graph(500, 5, seed)),
    ("Zufall sehr dünn, n = 1500, 1 %", lambda seed: S.random_graph(1500, 1, seed)),
)


def structure_rows(seeds=C.SWEEP_SEEDS[:3], budget=C.SWEEP_BUDGET):
    """Je Struktur der Median über die festen Instanzen: Knoten und Adjazenzabfragen von einfach und Färbung (beide Startordnung Grad), ω, Degeneracy.
    Zeigt, wo die Färbung viele Knoten spart, aber nicht mehr Abfragen (sehr dünne Graphen)."""
    rows = []
    for name, build in STRUCTURES:
        nodes = {"simple": [], "color": []}
        looks = {"simple": [], "color": []}
        omegas, degs, aborted = [], [], 0
        n = None
        for seed in seeds:
            g = build(seed)
            n = g.n
            w = (1,) * g.n
            vals = []
            for key in ("simple", "color"):
                r = A.largest_clique(g.adj, w, key, "degree", False, budget=budget)
                nodes[key].append(r.nodes)
                looks[key].append(r.lookups)
                aborted += int(r.aborted and key == "simple")
                if not r.aborted:
                    vals.append(r.value)
            omegas.append(vals[0])
            degs.append(A.core_decomposition(g.adj)[2])
        rows.append({"name": name, "n": n, "omega": med(omegas), "degeneracy": med(degs), "aborted": aborted,
                     "nodes": {k: med(v) for k, v in nodes.items()}, "lookups": {k: med(v) for k, v in looks.items()}})
    return rows


def lookup_change(row):
    """Änderung der Adjazenzabfragen durch die Färbungsschranke gegenüber „einfach“ in Prozent (negativ = weniger)."""
    return 100.0 * (row["lookups"]["color"] / row["lookups"]["simple"] - 1.0) if row["lookups"]["simple"] else 0.0


CORE_STRUCTURES = (("Zufall, n = 40, 50 %", lambda seed: S.random_graph(40, 50, seed)),) + STRUCTURES[:2] + STRUCTURES[2:3] + STRUCTURES[4:]


def core_rows(seeds=C.SWEEP_SEEDS[:3], budget=C.SWEEP_BUDGET):
    """Je Struktur der Median: n, Degeneracy d, ω, Lücke d + 1 − ω, Greedy-Startwert, Zahl der nach der Vorverarbeitung verbleibenden Knoten, die Adjazenzabfragen mit
    (einschließlich Vorverarbeitung) und ohne Vorverarbeitung, und in wie vielen Instanzen die Greedy-Clique schon ohne Suche als optimal bewiesen war.
    Färbungsschranke, Startordnung Degeneracy, Anzahl der Sendungen als Ziel."""
    rows = []
    for name, build in CORE_STRUCTURES:
        vals = {"omega": [], "d": [], "lb": [], "kept": [], "with": [], "without": [], "proven": 0}
        n = None
        for seed in seeds:
            g = build(seed)
            n = g.n
            w = (1,) * g.n
            r = A.largest_clique(g.adj, w, "color", "degeneracy", True, budget=budget)
            plain = A.largest_clique(g.adj, w, "color", "degeneracy", False, budget=budget)
            vals["omega"].append(r.value)
            vals["d"].append(r.degeneracy)
            vals["lb"].append(r.greedy_value)
            vals["kept"].append(r.kept)
            vals["with"].append(r.lookups)
            vals["without"].append(plain.lookups)
            vals["proven"] += int(r.proven_by_prune)
        rows.append({"name": name, "n": n, "omega": med(vals["omega"]), "degeneracy": med(vals["d"]), "gap": med(vals["d"]) + 1 - med(vals["omega"]),
                     "greedy": med(vals["lb"]), "kept": med(vals["kept"]), "kept_share": med(vals["kept"]) / n, "proven": vals["proven"], "seeds": len(seeds),
                     "lookups_with": med(vals["with"]), "lookups_without": med(vals["without"])})
    return rows


# --- Experiment 4: Greedy-Heuristik und Gewichte ----------------------------------------------------------------------------------------------

GREEDY_STRUCTURES = (
    ("Zufall, n = 40, 50 %", lambda seed: S.random_graph(40, 50, seed)),
    ("Zufall, n = 60, 70 %", lambda seed: S.random_graph(60, 70, seed)),
    ("Zeitfenster, n = 80, 50 %", lambda seed: S.window_graph(80, 50, seed)),
    ("Klassenregeln, n = 80, 50 %", lambda seed: S.class_graph(80, 50, seed)),
    ("skalenfrei, n = 500, m = 5", lambda seed: S.scale_free_graph(500, 5, seed)),
)


def greedy_rows(seeds=C.GREEDY_SEEDS):
    """Je Struktur über 20 feste Instanzen: in wie vielen die Greedy-Heuristik ω exakt trifft, mittlere und größte Lücke zum Optimum (Anzahl der Sendungen)."""
    rows = []
    for name, build in GREEDY_STRUCTURES:
        gaps = []
        for seed in seeds:
            g = build(seed)
            w = (1,) * g.n
            opt = A.largest_clique(g.adj, w, "color", "degree", budget=C.SWEEP_BUDGET * 4)
            greedy = A.greedy_clique(g.adj, w)[1]
            gaps.append(opt.value - greedy)
        rows.append({"name": name, "runs": len(gaps), "exact": sum(1 for x in gaps if x == 0), "mean_gap": statistics.mean(gaps), "max_gap": max(gaps)})
    return rows


def weighted_rows(sizes=(30, 40), densities=(50, 70), seeds=C.SWEEP_SEEDS, budget=C.SWEEP_BUDGET):
    """Gewichtete Variante (Gewichte 1 bis 9): Knoten der einfachen gegen die gewichtete Färbungsschranke, Median über die festen Instanzen."""
    rows = []
    for n in sizes:
        for d in densities:
            ns, nc, ls, lc, ab = [], [], [], [], 0
            for seed in seeds:
                g = S.random_graph(n, d, seed)
                w = S.make_weights(n, seed, "value")
                a = A.largest_clique(g.adj, w, "simple", "degree", False, budget=budget)
                b = A.largest_clique(g.adj, w, "color", "degree", False, budget=budget)
                ns.append(a.nodes), nc.append(b.nodes), ls.append(a.lookups), lc.append(b.lookups)
                ab += int(a.aborted)
            rows.append({"n": n, "density": d, "simple": med(ns), "color": med(nc), "simple_lookups": med(ls), "color_lookups": med(lc), "aborted": ab})
    return rows


# --- Brücke Clique ⇄ unabhängige Menge ----------------------------------------------------------------------------------------------------------

def complement_check(settings, n=C.CHECK_N):
    """Kleine Instanz (n = CHECK_N, Regelart, Anteil und Seed wie eingestellt): die größte Clique des Verträglichkeitsgraphen und die größte unabhängige Menge des
    Konfliktgraphen (Aufzählen aller Teilmengen, ohne Branch-and-Bound) haben denselben Wert; umgekehrt auch."""
    g = S.build_graph(settings.graph_type, n, settings.density, settings.seed)
    ones = (1,) * g.n
    conflict = S.complement(g.adj)
    omega = A.largest_clique(g.adj, ones).value
    alpha_conflict = A.brute_force_max_independent_set(conflict, ones)
    omega_conflict = A.largest_clique(conflict, ones).value
    alpha = A.brute_force_max_independent_set(g.adj, ones)
    return {"n": n, "omega": omega, "alpha_conflict": alpha_conflict, "equal": omega == alpha_conflict,
            "omega_conflict": omega_conflict, "alpha": alpha, "equal_back": omega_conflict == alpha}
