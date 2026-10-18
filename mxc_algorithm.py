"""Größte Clique (bzw. Clique größten Werts) per Branch-and-Bound, mit zwei Schranken und optionaler Vorverarbeitung.

Jede Regel ist eine eigene kleine Funktion mit expliziten Ein- und Ausgaben (DEMO-PLAYBOOK 1b); `largest_clique` ruft sie nur der Reihe nach auf.
Ein *Knoten* ist ein Aufruf des Branch-and-Bound. Gerechnet wird in *Adjazenzabfragen* („ist w ein Nachbar von v?“): ein einheitliches Maß für beide Schranken
und die Vorverarbeitung; es ist keine Laufzeit. Reine Python-Mengen, feste Reihenfolgen, kein Zufall: das Ergebnis ist vollständig deterministisch.

Die Gewichte sind ganzzahlig und mindestens 1 (bei „Anzahl der Sendungen“ überall 1)."""

import heapq
from dataclasses import dataclass, field

import mxc_constants as C


class BudgetExceeded(Exception):
    """Das Knotenbudget ist aufgebraucht; der Lauf bricht ab."""


@dataclass(frozen=True)
class Event:
    """Ein Ereignis für die Schritt-Ansicht (Knotennummern des Originalgraphen)."""
    kind: str            # "call" (Aufruf), "cut" (abgeschnitten), "leaf" (Blatt), "improve" (neue beste Fuhre)
    depth: int
    R: tuple
    P: tuple             # Kandidaten in Verarbeitungsreihenfolge
    classes: tuple       # Farbklasse je Kandidat (leer bei der einfachen Schranke)
    bound: int           # obere Schranke dieses Teilbaums (Wert von R plus Schranke der Kandidaten)
    best: int            # bester bis dahin gefundener Wert
    best_clique: tuple


@dataclass
class Result:
    bound_rule: str
    order: str
    prune: bool
    clique: tuple                     # größte Clique (sortiert)
    value: int                        # ihr Wert (Zahl der Sendungen bzw. Gesamtwert)
    nodes: int                        # Knoten des Suchbaums
    lookups: int                      # Adjazenzabfragen insgesamt (Suche plus Vorverarbeitung)
    prep_lookups: int                 # davon in der Vorverarbeitung (Kernzahlen, Greedy-Start)
    aborted: bool
    greedy_clique: tuple
    greedy_value: int
    degeneracy: int
    kept: int                         # Knoten, die nach der Vorverarbeitung im Suchgraphen bleiben (n, wenn aus)
    n: int
    proven_by_prune: bool             # Greedy-Clique ist ohne Suche als optimal bewiesen
    history: list = field(default_factory=list)       # [(Knoten, bester Wert)] bei jeder Verbesserung
    trace: list = field(default_factory=list)
    trace_truncated: bool = False


# --- Einheiten -------------------------------------------------------------------------------------------------------------------------------

def core_decomposition(adj):
    """Kernzerlegung durch wiederholtes Entfernen des Knotens mit kleinstem Restgrad (Gleichstand: kleinster Index).
    Gibt (Entfernungsreihenfolge, Kernzahl je Knoten, Degeneracy d) zurück; die Kernzahl ist der größte Restgrad bis einschließlich des Entfernens."""
    n = len(adj)
    degree = [len(a) for a in adj]
    removed = [False] * n
    heap = [(degree[v], v) for v in range(n)]
    heapq.heapify(heap)
    order, core, d = [], [0] * n, 0
    while heap:
        dv, v = heapq.heappop(heap)
        if removed[v] or dv != degree[v]:
            continue
        d = max(d, dv)
        core[v] = d
        removed[v] = True
        order.append(v)
        for w in adj[v]:
            if not removed[w]:
                degree[w] -= 1
                heapq.heappush(heap, (degree[w], w))
    return order, core, d


def start_order(adj, rule, removal_order):
    """Reihenfolge der Kandidaten: nach Nummer, nach Grad (größter zuerst, Gleichstand kleinster Index) oder nach Degeneracy (der zuerst entfernte Knoten steht zuletzt)."""
    n = len(adj)
    if rule == "index":
        return list(range(n))
    if rule == "degree":
        return sorted(range(n), key=lambda v: (-len(adj[v]), v))
    if rule == "degeneracy":
        return list(reversed(removal_order))
    raise ValueError(f"unbekannte Startordnung: {rule}")


def greedy_clique(adj, weights):
    """Greedy-Heuristik: immer den Kandidaten mit den meisten Nachbarn im Kandidatenrest nehmen (Gleichstand: größeres Gewicht, dann kleinerer Index).
    Gibt (Clique sortiert, Wert, Adjazenzabfragen) zurück; Kosten je Kandidat v: min(|Rest|, Grad(v))."""
    n = len(adj)
    cand = set(range(n))
    clique, cost = [], 0
    while cand:
        best_v, best_key = None, None
        for v in sorted(cand):
            cost += min(len(cand), len(adj[v]))
            key = (len(adj[v] & cand), weights[v], -v)
            if best_key is None or key > best_key:
                best_v, best_key = v, key
        clique.append(best_v)
        cand = cand & adj[best_v]
    return tuple(sorted(clique)), sum(weights[v] for v in clique), cost


def core_keep(core, weights, lower_bound):
    """Knoten, die in einer Clique mit Wert > lower_bound liegen können: eine solche Clique hat mindestens lower_bound // w_max + 1 Knoten, jeder ihrer Knoten also Kernzahl >= (diese Zahl − 1).
    Bei Gewicht überall 1 ist das die Bedingung Kernzahl >= lower_bound."""
    w_max = max(weights) if weights else 1
    need = lower_bound // w_max
    return [v for v in range(len(core)) if core[v] >= need]


def greedy_color_classes(P, adj):
    """Gierige Färbung der Kandidaten in der Reihenfolge von P: jede Klasse ist eine Menge paarweise NICHT verträglicher Sendungen.
    Gibt (Kandidaten klassenweise geordnet, Klassennummer je Kandidat, Adjazenzabfragen) zurück."""
    uncolored = list(P)
    order, numbers, lookups, k = [], [], 0, 0
    while uncolored:
        k += 1
        cls, rest = [], []
        for v in uncolored:
            fits = True
            for u in cls:
                lookups += 1
                if v in adj[u]:
                    fits = False
                    break
            (cls if fits else rest).append(v)
        order.extend(cls)
        numbers.extend([k] * len(cls))
        uncolored = rest
    return order, numbers, lookups


def color_prefix_bounds(order, numbers, weights):
    """Schranke je Position i: die Summe der größten Gewichte aller Klassen, die in order[:i+1] vorkommen (innerhalb der letzten Klasse nur bis i).
    Eine Clique enthält höchstens einen Knoten je Klasse, also ist das eine obere Schranke für jede Clique in order[:i+1]; bei Gewicht 1 ist es die Klassennummer."""
    bounds, finished, current, current_max = [], 0, 0, 0
    for v, c in zip(order, numbers):
        if c != current:
            finished += current_max
            current, current_max = c, 0
        current_max = max(current_max, weights[v])
        bounds.append(finished + current_max)
    return bounds


def simple_bound(value, candidates, weights):
    """Schranke „Größe + Restkandidaten“ (bzw. Wert + Gesamtgewicht der Kandidaten)."""
    return value + sum(weights[v] for v in candidates)


def is_clique(adj, vertices):
    vs = list(vertices)
    return all(vs[j] in adj[vs[i]] for i in range(len(vs)) for j in range(i + 1, len(vs)))


def clique_value(weights, vertices):
    return sum(weights[v] for v in vertices)


# --- Komposition -----------------------------------------------------------------------------------------------------------------------------

class _Search:
    """Zustand einer Suche (Knotenzähler, Abfragen, bester Fund, Verlauf, Protokoll)."""

    def __init__(self, labels, best, best_clique, budget, trace_limit):
        self.labels, self.best, self.best_clique = labels, best, best_clique
        self.budget, self.trace_limit = budget, trace_limit
        self.nodes = self.lookups = 0
        self.history, self.trace, self.truncated = [], [], False

    def tick(self):
        self.nodes += 1
        if self.budget is not None and self.nodes > self.budget:
            raise BudgetExceeded

    def event(self, kind, depth, R, P, classes, bound):
        if not self.trace_limit:
            return
        if len(self.trace) >= self.trace_limit:
            self.truncated = True
            return
        lab = self.labels
        self.trace.append(Event(kind, depth, tuple(lab[v] for v in R), tuple(lab[v] for v in P), tuple(classes), bound, self.best, self.best_clique))

    def improve(self, R, value, depth):
        self.best = value
        self.best_clique = tuple(sorted(self.labels[v] for v in R))
        self.history.append((self.nodes, value))
        self.event("improve", depth, R, (), (), value)


def _expand_simple(st, adj, weights, cand, R, value, depth):
    """Einschließen/Ausschließen je erstem Kandidaten. Der Ausschluss-Zweig ist ein Endaufruf und läuft als Schleifendurchgang (jeder Durchgang zählt als ein Knoten),
    damit die Rekursionstiefe nur von der Cliquengröße abhängt und nicht von der Kandidatenzahl."""
    while True:
        st.tick()
        bound = simple_bound(value, cand, weights)
        if not cand:
            if value > st.best:
                st.improve(R, value, depth)
            else:
                st.event("leaf", depth, R, (), (), bound)
            return
        if bound <= st.best:
            st.event("cut", depth, R, cand, (), bound)
            return
        st.event("call", depth, R, cand, (), bound)
        v, rest = cand[0], cand[1:]
        st.lookups += len(rest)
        _expand_simple(st, adj, weights, [x for x in rest if x in adj[v]], R + [v], value + weights[v], depth + 1)
        if bound - weights[v] <= st.best:
            return
        cand, depth = rest, depth + 1


def _expand_color(st, adj, weights, P, R, value, depth):
    st.tick()
    order, numbers, looked = greedy_color_classes(P, adj)
    st.lookups += looked
    bounds = color_prefix_bounds(order, numbers, weights)
    if not order:
        if value > st.best:
            st.improve(R, value, depth)
        return
    st.event("call", depth, R, order, numbers, value + bounds[-1])
    for i in range(len(order) - 1, -1, -1):
        if value + bounds[i] <= st.best:
            st.event("cut", depth, R, order[:i + 1], numbers[:i + 1], value + bounds[i])
            return
        v = order[i]
        st.lookups += i
        child = [x for x in order[:i] if x in adj[v]]
        if child:
            _expand_color(st, adj, weights, child, R + [v], value + weights[v], depth + 1)
        elif value + weights[v] > st.best:
            st.improve(R + [v], value + weights[v], depth + 1)


def largest_clique(adj, weights, bound="color", order="degree", prune=False, budget=None, trace_limit=0):
    """Clique größten Werts per Branch-and-Bound.

    `bound`: "simple" (Größe + Restkandidaten) oder "color" (Färbungsschranke). `order`: Startordnung der Kandidaten.
    `prune`: Vorverarbeitung = Greedy-Startclique als untere Schranke plus Kernzahl-Filter; bleibt kein Knoten übrig, ist die Greedy-Clique bewiesen optimal.
    `budget`: höchste Zahl von Knoten; danach `aborted=True`, der bis dahin beste Fund bleibt erhalten."""
    if bound not in C.BOUNDS or order not in C.ORDERS:
        raise ValueError(f"unbekannte Schranke oder Startordnung: {bound}, {order}")
    n = len(adj)
    assert len(weights) == n and all(w >= 1 for w in weights)
    removal, core, d = core_decomposition(adj)
    g_clique, g_value, g_cost = greedy_clique(adj, weights) if n else ((), 0, 0)
    m2 = sum(len(a) for a in adj)
    prep = (m2 if (order == "degeneracy" or prune) else 0) + (g_cost if prune else 0)
    order_list = start_order(adj, order, removal)
    if prune:
        keep = core_keep(core, weights, g_value)
        kept_set = set(keep)
        labels = [v for v in order_list if v in kept_set]
        best, best_clique = g_value, g_clique
    else:
        labels = order_list
        best, best_clique = 0, ()
    index = {v: i for i, v in enumerate(labels)}
    sub_adj = tuple(frozenset(index[w] for w in adj[v] if w in index) for v in labels)
    sub_weights = tuple(weights[v] for v in labels)
    st = _Search(labels, best, best_clique, budget, trace_limit)
    if prune:
        st.history.append((0, g_value))
    aborted = False
    if labels:
        positions = list(range(len(labels)))
        try:
            if bound == "simple":
                _expand_simple(st, sub_adj, sub_weights, positions, [], 0, 0)
            else:
                _expand_color(st, sub_adj, sub_weights, positions, [], 0, 0)
        except BudgetExceeded:
            aborted = True
    clique = st.best_clique
    if n and not clique:                                   # ohne Vorverarbeitung und ohne Fund (nur bei Abbruch vor dem ersten Blatt)
        clique, st.best = g_clique, g_value
    return Result(bound, order, prune, tuple(sorted(clique)), st.best, st.nodes, st.lookups + prep, prep, aborted, g_clique, g_value, d,
                  len(labels), n, bool(prune and n and not labels), st.history, st.trace, st.truncated)


def root_color_bound(adj, weights, order="degree"):
    """Die Färbungsschranke an der Wurzel (alle Sendungen gefärbt): eine obere Schranke für den Wert jeder Clique; bei Gewicht 1 die Zahl der Farben, also χ-Schätzung nach oben."""
    if not adj:
        return 0
    removal, _, _ = core_decomposition(adj)
    ordered = start_order(adj, order, removal)
    cls_order, numbers, _ = greedy_color_classes(ordered, adj)
    return color_prefix_bounds(cls_order, numbers, weights)[-1]


# --- Referenz und Hilfen für Gegenproben -----------------------------------------------------------------------------------------------------

def brute_force_max_clique(adj, weights):
    """Wert der besten Clique und alle optimalen Cliquen durch Aufzählen aller Teilmengen (nur für n <= 16; unabhängige Referenz ohne jede Rekursion)."""
    n = len(adj)
    nbr = [sum(1 << w for w in adj[v]) for v in range(n)]
    ok = {0: True}
    value = {0: 0}
    best, best_sets = 0, []
    for mask in range(1, 1 << n):
        low = mask & -mask
        v = low.bit_length() - 1
        rest = mask ^ low
        ok[mask] = ok[rest] and (rest & ~nbr[v]) == 0
        value[mask] = value[rest] + weights[v]
        if ok[mask]:
            if value[mask] > best:
                best, best_sets = value[mask], [mask]
            elif value[mask] == best:
                best_sets.append(mask)
    return best, sorted(tuple(v for v in range(n) if m >> v & 1) for m in best_sets)


def brute_force_max_independent_set(adj, weights):
    """Wert der besten unabhängigen Menge durch Aufzählen aller Teilmengen (nur für n <= 16)."""
    n = len(adj)
    nbr = [sum(1 << w for w in adj[v]) for v in range(n)]
    best = 0
    for mask in range(1, 1 << n):
        if all((mask & nbr[v]) == 0 for v in range(n) if mask >> v & 1):
            best = max(best, sum(weights[v] for v in range(n) if mask >> v & 1))
    return best
