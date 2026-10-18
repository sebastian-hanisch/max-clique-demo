"""Größte Clique: Färbungsschranke und Kernzahl - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Zweites Stück der Härte-und-Struktur-Reihe: Branch-and-Bound für die größte konfliktfreie Fuhre am Verträglichkeitsgraphen einer Sammelladung.

Lauffähig mit: streamlit run app.py
"""

import time

import pandas as pd
import streamlit as st

import mxc_constants as C
import mxc_evaluation as ev
from mxc_presets import (
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sync_query_params,
)
from mxc_visualization import (
    build_core_figure,
    build_graph_figure,
    build_greedy_figure,
    build_history_figure,
    build_prep_cost_figure,
    build_structure_figure,
    build_sweep_figure,
)

st.set_page_config(page_title="Größte Clique – Sebastian Hanisch", layout="wide")


def _i(x):
    """Ganze Zahl mit Punkt als Tausendertrenner."""
    return f"{x:,.0f}".replace(",", ".")


def _f(x, digits=1):
    """Dezimalzahl mit Komma."""
    return f"{x:.{digits}f}".replace(".", ",")


def _s(x, digits=1):
    """Dezimalzahl mit Komma und ausdrücklichem Vorzeichen."""
    return f"{x:+.{digits}f}".replace(".", ",")


@st.cache_data(show_spinner=False)
def _analysis(settings):
    return ev.analyse(settings)


@st.cache_data(show_spinner=False)
def _density_sweep(graph_type):
    return ev.density_sweep(graph_type)


@st.cache_data(show_spinner=False)
def _structures():
    return ev.structure_rows()


@st.cache_data(show_spinner=False)
def _core():
    return ev.core_rows()


@st.cache_data(show_spinner=False)
def _greedy():
    return ev.greedy_rows()


@st.cache_data(show_spinner=False)
def _weighted():
    return ev.weighted_rows()


@st.cache_data(show_spinner=False)
def _complement(settings):
    return ev.complement_check(settings)


st.title("🧩 Größte Clique: Färbungsschranke und Kernzahl")
st.markdown(
    """
Wer eine Fuhre packt, will meist die **größte** Gruppe von Sendungen, die sich alle paarweise vertragen: eine **größte Clique** im Verträglichkeitsgraphen (Sendung = Knoten, Kante = „dürfen zusammen verladen werden“). Die Demo zur Aufzählung aller maximalen Fuhren zeigt, dass es davon bis 3^(n/3) geben kann; hier wird nur die größte gesucht, per **Branch-and-Bound**, und die Frage ist, wie gut die **obere Schranke** ist, mit der er Teilbäume abschneidet.

Das ist das zweite Stück der **Härte-und-Struktur-Reihe**. Anders als die Fall-Demos zeigt diese Demo ein Verfahren an einem wachsenden Beispiel. Weiter unten: die vier Experimente **🔬**, **🚧 Wo die Annahmen enden** und der Expander **📐 Mathematische Formulierung**.
"""
)

with st.expander("So funktioniert Branch-and-Bound mit Färbungsschranke", expanded=True):
    st.markdown(
        """
1. **Färbe die Kandidaten gierig:** Jede Farbklasse ist eine Gruppe von Sendungen, die **paarweise nicht** verträglich sind. Eine Fuhre nimmt daher höchstens **eine Sendung je Klasse**: Die Zahl der Klassen ist eine obere Schranke für die Fuhrengröße.
2. **Verzweige von der höchsten Klasse rückwärts:** Nimm eine Sendung in die Fuhre auf und beschränke die Kandidaten auf ihre Nachbarn.
3. **Schneide ab**, sobald Größe der Fuhre + Klassennummer nicht größer ist als die beste bisher gefundene Fuhre: Dieser Teilbaum kann sie nicht mehr schlagen.

| Begriff | Bedeutung |
|---|---|
| **Einfache Schranke** | „Größe + Restkandidaten“: so viele Sendungen, wie noch übrig sind. Billig, aber sehr locker. (Dieselbe Schranke nutzt die Demo zur Färbung für ihre Cliquenzahl.) |
| **Färbungsschranke** | Größe + Zahl der Farbklassen der Kandidaten (Tomita und Seki 2003). Mit Gewichten: die Summe der größten Werte je Klasse. |
| **Startordnung** | In welcher Reihenfolge die Kandidaten gefärbt bzw. verzweigt werden: nach Nummer, nach Grad (größter zuerst) oder nach Degeneracy (der Sendung mit dem kleinsten Rest-Grad zuletzt). |
| **Vorverarbeitung** | Eine Greedy-Startclique als untere Schranke, dazu der Kernzahl-Filter: In einer Clique der Größe s hat jeder Knoten Kernzahl ≥ s − 1; Sendungen mit kleinerer Kernzahl fallen weg. |
| **Greedy-Heuristik** | Immer die Sendung mit den meisten Nachbarn im Rest nehmen: schnell, aber ohne Garantie. |
        """
    )

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
cols = st.columns(len(C.PRESETS))
for col, name in zip(cols, C.PRESETS):
    with col:
        st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}")

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.markdown("**Graph**")
    graph_type = st.selectbox("Regelart", list(C.GRAPH_TYPES), format_func=C.GRAPH_TYPES.get, key="type_select",
                              help="Zufallsregeln: jedes Paar unabhängig verträglich. Zeitfenster: verträglich, wenn die Fenster überlappen. Klassenregeln: sechs Klassen, ein Klassenpaar ist verträglich oder nicht.")
    n = st.slider("Sendungen n", *bounds("n_slider"), key="n_slider", help="Knotenzahl des Graphen.")
    density = st.slider("Anteil verträglicher Paare (%)", *bounds("density_slider"), key="density_slider",
                        help="Zufallsregeln: Wahrscheinlichkeit je Paar. Zeitfenster: die Fensterlänge wird so gewählt, dass zwei Fenster mit dieser Wahrscheinlichkeit überlappen. Klassenregeln: Wahrscheinlichkeit je Klassenpaar.")
    seed = st.number_input("Zufalls-Seed des Graphen", *bounds("seed_input"), key="seed_input", step=1)
    st.button("🎲 Neuen Graphen erzeugen", width="stretch", on_click=randomize_seed)
    st.markdown("**Ziel**")
    objective = st.radio("Gesucht ist die Fuhre mit", list(C.OBJECTIVES), format_func=C.OBJECTIVES.get, key="objective_radio",
                         help="Anzahl: jede Sendung zählt 1 (größte Clique). Wert: jede Sendung hat einen ganzzahligen Wert von 1 bis 9, gesucht ist die Fuhre mit dem größten Gesamtwert.")
    st.markdown("**Verfahren**")
    bound = st.radio("Schranke", list(C.BOUNDS), format_func=C.BOUNDS.get, key="bound_radio",
                     help="Welche obere Schranke der Branch-and-Bound der Schritt-Ansicht nutzt. Die Kennzahlen darunter vergleichen immer beide.")
    order = st.selectbox("Startordnung", list(C.ORDERS), format_func=C.ORDERS.get, key="order_select",
                         help="Reihenfolge der Kandidaten: bei der einfachen Schranke ist der erste Kandidat der Verzweigungsknoten, bei der Färbungsschranke bestimmt sie die gierige Färbung.")
    prune = st.checkbox("Vorverarbeitung (Greedy-Start + Kernzahl)", key="prune_check",
                        help="Greedy-Startclique als untere Schranke, dann nur Sendungen mit ausreichender Kernzahl im Suchgraphen. Die Abfragen der Vorverarbeitung zählen mit.")

sync_query_params({"type_select": graph_type, "n_slider": int(n), "density_slider": int(density), "seed_input": int(seed), "bound_radio": bound,
                   "order_select": order, "prune_check": bool(prune), "objective_radio": objective})

settings = ev.Settings(graph_type=graph_type, n=int(n), density=int(density), seed=int(seed), bound=bound, order=order, prune=bool(prune), objective=objective)
with st.spinner("Rechne..."):
    a = _analysis(settings)
g, w, res = a.graph, a.weights, a.result
unit = "Sendungen" if objective == "size" else "Wert"

# --- Die größte Fuhre ----------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Die größte Fuhre: Schritt für Schritt")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Größte Fuhre" + (" (Sendungen)" if objective == "size" else " (Wert)"), _i(a.value) if a.complete else "unbekannt",
          help="Größte Zahl von Sendungen bzw. größter Gesamtwert einer Fuhre, in der alle Paare verträglich sind.")
m2.metric(f"Knoten ({C.BOUNDS[bound]})", (">" if res.aborted else "") + _i(res.nodes), help="Aufrufe des Branch-and-Bound (ein Knoten des Suchbaums).")
m3.metric("Adjazenzabfragen", (">" if res.aborted else "") + _i(res.lookups), delta=(f"davon {_i(res.prep_lookups)} Vorverarbeitung" if res.prep_lookups else "ohne Vorverarbeitung"), delta_color="off",
          help="Wie oft gefragt wurde, ob zwei Sendungen verträglich sind: ein einheitliches Maß für beide Schranken und die Vorverarbeitung, keine Laufzeit.")
if a.complete:
    gap = a.value - res.greedy_value
    m4.metric("Greedy-Startwert", _i(res.greedy_value), delta=("trifft das Optimum" if gap == 0 else f"{_i(gap)} unter dem Optimum"), delta_color="off",
              help="Wert der Greedy-Heuristik (immer die Sendung mit den meisten Nachbarn im Rest).")
else:
    m4.metric("Greedy-Startwert", _i(res.greedy_value))
if res.aborted:
    st.warning(f"Die Konfiguration „{C.BOUNDS[bound]}“ ist nach {_i(C.NODE_BUDGET)} Knoten abgebrochen (Rechengrenze der Demo). Der bis dahin beste Fund steht oben; die Größe stammt aus einem Verfahren, das fertig wurde.")
if res.proven_by_prune:
    st.success("Die Vorverarbeitung beweist die Greedy-Clique als optimal: Kein Knoten erreicht die nötige Kernzahl für eine bessere Fuhre, der Suchbaum hat **0 Knoten**.")
st.caption(f"Obere Schranke an der Wurzel (alle Sendungen gefärbt): {_i(a.root_bound)}. Der Abstand zur größten Fuhre ({_i(a.value) if a.complete else '?'}) ist das, was der Suchbaum noch beweisen muss.")

events = res.trace
n_events = len(events)
owner = (settings.graph_type, settings.n, settings.density, settings.seed, settings.bound, settings.order, settings.prune, settings.objective)
if st.session_state.get("step_owner") != owner:
    st.session_state["mxc_step"] = 0
    st.session_state["step_owner"] = owner
if n_events > 1:
    st.session_state["mxc_step"] = min(int(st.session_state.get("mxc_step", 0)), n_events - 1)
step_col, play_col = st.columns([5, 2])
with step_col:
    if n_events > 1:
        step = st.slider("Schritt", 0, n_events - 1, key="mxc_step", help="Welches Ereignis des Suchbaums die Ansicht zeigt (Tiefensuche): Aufruf, Abschneiden, Blatt oder neue beste Fuhre.")
    else:
        step = 0
        st.caption("Hier gibt es nichts zu durchsuchen." if res.proven_by_prune else "Dieser Graph braucht nur ein Ereignis.")
with play_col:
    auto_play = st.button("▶️ Abspielen", width="stretch", disabled=n_events <= 1)
view_slot = st.empty()


def _names(items):
    return "{" + ", ".join(str(v + 1) for v in items) + "}" if items else "∅"


def _classes_text(e):
    groups = {}
    for v, c in zip(e.P, e.classes):
        groups.setdefault(c, []).append(v)
    return " | ".join(f"{c}: {_names(vs)}" for c, vs in groups.items())


def _describe(k):
    e = events[k]
    head = f"**Ereignis {k + 1} von {_i(n_events) if not res.trace_truncated else str(_i(C.TRACE_LIMIT)) + '+'}** (Tiefe {e.depth}): R = {_names(e.R)}"
    if e.kind == "call":
        if e.classes:
            return f"{head}, Kandidaten in {max(e.classes)} Farbklassen: {_classes_text(e)}. Schranke {_i(e.bound)}, bester Fund bisher {_i(e.best)}."
        return f"{head}, {len(e.P)} Kandidaten. Schranke „Größe + Rest“ = {_i(e.bound)}, bester Fund bisher {_i(e.best)}."
    if e.kind == "cut":
        return f"{head}. **Abgeschnitten:** Schranke {_i(e.bound)} ≤ bester Fund {_i(e.best)}; dieser Teilbaum kann die beste Fuhre nicht mehr schlagen."
    if e.kind == "improve":
        return f"{head}. **Neue beste Fuhre:** {_names(e.best_clique)} mit {unit} {_i(e.best)}."
    return f"{head}. Blatt ohne Verbesserung (Schranke {_i(e.bound)})."


def _render(k):
    with view_slot.container():
        e = events[k]
        st.plotly_chart(build_graph_figure(g, w, event=e, best=e.best_clique), width="stretch", key=f"graph_{k}")
        st.markdown(_describe(k))


if n_events == 0:
    with view_slot.container():
        st.plotly_chart(build_graph_figure(g, w, best=res.clique), width="stretch", key="graph_static")
elif auto_play:
    for k in range(n_events):
        _render(k)
        time.sleep(min(0.6, 12.0 / max(n_events, 1)))
else:
    _render(step)
if res.trace_truncated:
    st.caption(f"Die Schritt-Ansicht zeigt die ersten {_i(C.TRACE_LIMIT)} Ereignisse; die Zahlen oben gelten für den ganzen Lauf.")
st.caption("Grün: R. Farbige Kandidaten: je Färbungsklasse eine Farbe (blau: einfache Schranke, keine Klassen). Rot umrandet, Kanten rot: die beste Fuhre bisher.")
if res.history:
    st.plotly_chart(build_history_figure(res, objective), width="stretch", key="history_chart")
    st.caption("Wann die beste Fuhre gefunden wird: Der Rest der Suche beweist nur noch, dass es keine bessere gibt.")

# --- Kernfrage -----------------------------------------------------------------------------------------------------------------------------

st.markdown("## ❓ Kernfrage: Wie viel schneidet die Färbung gegenüber „Größe + Rest“ ab, bei genau diesem Graphen?")
simple, color = a.simple, a.color
if simple.aborted:
    st.success(f"Mit „Größe + Rest“ bricht der Lauf nach {_i(C.NODE_BUDGET)} Knoten ab, mit der Färbung sind es **{_i(color.nodes)}** Knoten und {_i(color.lookups)} Adjazenzabfragen: mindestens **Faktor {_i(C.NODE_BUDGET // max(color.nodes, 1))}** weniger Knoten.")
else:
    node_f = ev.factor(simple.nodes, color.nodes)
    look_f = ev.factor(simple.lookups, color.lookups)
    if look_f >= 5:
        st.success(f"„Größe + Rest“: **{_i(simple.nodes)}** Knoten und {_i(simple.lookups)} Abfragen. Färbung: **{_i(color.nodes)}** Knoten und {_i(color.lookups)} Abfragen, also **Faktor {_f(node_f, 1)}** weniger Knoten und **Faktor {_f(look_f, 1)}** weniger Abfragen.")
    elif look_f >= 1.0:
        st.info(f"„Größe + Rest“: {_i(simple.nodes)} Knoten, {_i(simple.lookups)} Abfragen. Färbung: {_i(color.nodes)} Knoten, {_i(color.lookups)} Abfragen: Faktor {_f(node_f, 1)} weniger Knoten, aber nur Faktor {_f(look_f, 2)} weniger Abfragen. Jeder Färbungsschritt kostet selbst Abfragen.")
    else:
        st.warning(f"„Größe + Rest“: {_i(simple.nodes)} Knoten, {_i(simple.lookups)} Abfragen. Färbung: {_i(color.nodes)} Knoten, aber **{_i(color.lookups)} Abfragen**, also mehr: Die Färbung spart hier Knoten, kostet aber mehr, als sie spart.")
pr = a.pruned
st.caption(f"Vorverarbeitung (Färbungsschranke): {_i(pr.kept)} von {_i(pr.n)} Sendungen bleiben im Suchgraphen, {_i(pr.nodes)} Knoten, {_i(pr.lookups)} Abfragen einschließlich {_i(pr.prep_lookups)} für die Vorverarbeitung selbst "
           f"(ohne Vorverarbeitung {_i(color.lookups)}).")

st.markdown("---")

# --- Experiment 1 --------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 1: Wie viel spart die Färbungsschranke — und wann?")
st.caption(f"Median über {len(C.SWEEP_SEEDS)} feste Graphen mit n = {C.SWEEP_N} Sendungen und der Regelart „{C.GRAPH_TYPES[graph_type]}“ aus der Seitenleiste (n, Seed, Ziel und Verfahren der Seitenleiste gelten hier nicht; Anzahl der Sendungen); "
           f"jeder Lauf ist auf {_i(C.SWEEP_BUDGET)} Knoten begrenzt, offene Quadrate markieren Mediane, bei denen mindestens ein Lauf diese Grenze erreicht hat.")
with st.spinner("Rechne den Sweep..."):
    sweep = _density_sweep(graph_type)
c1, c2 = st.columns(2)
c1.plotly_chart(build_sweep_figure(sweep, "nodes"), width="stretch", key="sweep_nodes")
c2.plotly_chart(build_sweep_figure(sweep, "lookups"), width="stretch", key="sweep_lookups")
vd = ev.sweep_verdict(sweep)
cut = "mindestens " if vd["any_aborted"] else ""
st.info(
    f"Bei {vd['worst_density']} % verträglichen Paaren spart die Färbung am wenigsten Knoten: Faktor {_f(vd['worst_node_factor'], 1)}; bei {vd['best_density']} % am meisten: {cut}Faktor {_f(vd['best_node_factor'], 0)}. "
    f"Bei den Adjazenzabfragen liegt der Gewinn zwischen Faktor {_f(vd['worst_lookup_factor'], 1)} (bei {vd['worst_lookup_density']} %) und {cut}Faktor {_f(vd['best_lookup_factor'], 0)}. "
    "Die Startordnung ändert die Knotenzahl der Färbungsschranke nur mäßig und nicht einheitlich in eine Richtung."
)

st.markdown("---")

# --- Experiment 2 --------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 2: Wann kostet die Färbung mehr, als sie spart?")
st.caption("Median über 3 feste Graphen je Struktur, beide Schranken mit Startordnung Grad. Balken: Änderung der Knoten und der Adjazenzabfragen durch die Färbungsschranke gegenüber „Größe + Rest“ in Prozent (negativ = weniger).")
with st.spinner("Rechne die Strukturen..."):
    rows2 = _structures()
st.plotly_chart(build_structure_figure(rows2), width="stretch", key="structure_chart")
dearer = [r for r in rows2 if ev.lookup_change(r) > 0]
best2 = min(rows2, key=ev.lookup_change)
if dearer:
    worst2 = max(dearer, key=ev.lookup_change)
    st.warning(
        f"In {len(dearer)} von {len(rows2)} Strukturen braucht die Färbung **mehr Adjazenzabfragen** als „Größe + Rest“, am meisten bei „{worst2['name']}“ ({_s(ev.lookup_change(worst2), 1)} %), "
        f"obwohl sie dort um den Faktor {_f(ev.factor(worst2['nodes']['simple'], worst2['nodes']['color']), 0)} weniger Knoten braucht. Am meisten spart sie bei „{best2['name']}“ ({_s(ev.lookup_change(best2), 0)} % Abfragen). "
        "Auf sehr dünnen Graphen gibt es kaum etwas abzuschneiden, und das Färben jedes Knotens kostet mehr, als es spart."
    )
else:
    st.info(f"Die Färbung braucht in allen {len(rows2)} Strukturen weniger Adjazenzabfragen; am meisten spart sie bei „{best2['name']}“ ({_s(ev.lookup_change(best2), 0)} %).")
with st.expander("Tabelle zu Experiment 2"):
    st.dataframe(pd.DataFrame({
        "Struktur": [r["name"] for r in rows2], "n": [r["n"] for r in rows2], "ω": [r["omega"] for r in rows2], "Degeneracy d": [r["degeneracy"] for r in rows2],
        "Knoten einfach": [(">" if r["aborted"] else "") + _i(r["nodes"]["simple"]) for r in rows2], "Knoten Färbung": [r["nodes"]["color"] for r in rows2],
        "Abfragen einfach": [_i(r["lookups"]["simple"]) for r in rows2], "Abfragen Färbung": [_i(r["lookups"]["color"]) for r in rows2],
    }), hide_index=True, width="stretch")

st.markdown("---")

# --- Experiment 3 --------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 3: Wann hilft die Kernzahl-Vorverarbeitung?")
st.caption("Median über 3 feste Graphen je Struktur, Färbungsschranke, Startordnung Degeneracy, Anzahl der Sendungen. Die Lücke ist d + 1 − ω: Degeneracy plus eins ist eine obere Schranke für ω; je kleiner die Lücke, desto mehr Sendungen kann der Kernzahl-Filter wegwerfen.")
with st.spinner("Rechne die Vorverarbeitung..."):
    rows3 = _core()
st.plotly_chart(build_core_figure(rows3), width="stretch", key="core_chart")
st.plotly_chart(build_prep_cost_figure(rows3), width="stretch", key="prep_chart")
cheaper = [r for r in rows3 if r["lookups_with"] < r["lookups_without"]]
proven = [r for r in rows3 if r["proven"] > 0]
removed_any = [r for r in rows3 if r["kept"] < r["n"]]
max_gap = max((r["gap"] for r in removed_any), default=None)
no_effect = [r for r in rows3 if r["kept"] == r["n"] and max_gap is not None and r["gap"] <= max_gap]
removal_text = (f"Der Filter wirft in {len(removed_any)} von {len(rows3)} Strukturen Sendungen weg, und nur dort, wo die Lücke d + 1 − ω höchstens {_f(max_gap, 0)} beträgt"
                + (f"; eine kleine Lücke allein genügt aber nicht: bei „{'“, „'.join(r['name'] + '“ (Lücke ' + _f(r['gap'], 0) + ')' for r in no_effect)} bleibt trotzdem jede Sendung, weil jede Kernzahl ≥ ω hat" if no_effect else "")
                if removed_any else "Der Filter wirft in keiner Struktur Sendungen weg")
st.info(
    f"{removal_text}. Auf dünnen Zufallsgraphen (große Lücke) bleibt jede Sendung. "
    f"Die Greedy-Clique wird in {len(proven)} Strukturen in mindestens einer Instanz ohne Suche als optimal bewiesen. "
    f"Die Vorverarbeitung senkt die Adjazenzabfragen insgesamt nur in {len(cheaper)} von {len(rows3)} Strukturen"
    + (f" („{'“, „'.join(r['name'] for r in cheaper)}“)" if cheaper else "")
    + ": ihre eigenen Kosten (Kernzahlen: zwei Abfragen je Kante, dazu der Greedy-Start) sind sonst größer als die Ersparnis."
)

st.markdown("---")

# --- Experiment 4 --------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Experiment 4: Wie weit liegt die Greedy-Heuristik daneben — und was ändern Gewichte?")
st.caption("20 feste Instanzen je Struktur. Die Greedy-Heuristik nimmt immer die Sendung mit den meisten Nachbarn im Rest; verglichen wird ihr Wert mit dem exakten Optimum.")
with st.spinner("Rechne den Greedy-Vergleich..."):
    rows4 = _greedy()
st.plotly_chart(build_greedy_figure(rows4), width="stretch", key="greedy_chart")
worst4 = max(rows4, key=lambda r: r["max_gap"])
best4 = max(rows4, key=lambda r: r["exact"] / r["runs"])
st.info(
    f"Greedy trifft die größte Clique je nach Struktur in {min(r['exact'] for r in rows4)} bis {max(r['exact'] for r in rows4)} von {rows4[0]['runs']} Instanzen (am häufigsten bei „{best4['name']}“). "
    f"Die größte Abweichung in einer einzelnen Instanz: {worst4['max_gap']} Sendungen zu wenig („{worst4['name']}“). Eine Heuristik ohne Schranke weiß nie, ob sie schon optimal ist; genau das beweist der Branch-and-Bound."
)
st.markdown("**Gewichtete Variante (Wert der Fuhre, Werte 1 bis 9):** Die Färbungsschranke summiert die größten Werte je Klasse statt die Klassen zu zählen.")
with st.spinner("Rechne die gewichtete Variante..."):
    rows_w = _weighted()
st.dataframe(pd.DataFrame({
    "n": [r["n"] for r in rows_w], "Anteil verträglich (%)": [r["density"] for r in rows_w],
    "Knoten einfach": [(">" if r["aborted"] else "") + _i(r["simple"]) for r in rows_w], "Knoten Färbung": [_i(r["color"]) for r in rows_w],
    "Faktor Knoten": [_f(ev.factor(r["simple"], r["color"]), 1) for r in rows_w],
    "Abfragen einfach": [_i(r["simple_lookups"]) for r in rows_w], "Abfragen Färbung": [_i(r["color_lookups"]) for r in rows_w],
}), hide_index=True, width="stretch")

st.markdown("---")

# --- Brücke --------------------------------------------------------------------------------------------------------------------------------

st.subheader("🔗 Brücke: größte Clique = größte konfliktfreie Auswahl")
cc = _complement(settings)
st.caption(f"Ein kleiner Graph mit n = {cc['n']} Sendungen (Regelart, Anteil und Seed aus der Seitenleiste). Branch-and-Bound auf dem Verträglichkeitsgraphen gegen ein Brute-Force-Aufzählen aller Teilmengen im Konfliktgraphen (ohne Branch-and-Bound).")
b1, b2 = st.columns(2)
b1.metric("Größte Clique (Branch-and-Bound)", cc["omega"])
b2.metric("Größte unabhängige Menge des Konfliktgraphen (Brute Force)", cc["alpha_conflict"])
if cc["equal"] and cc["equal_back"]:
    st.success(f"Beides ist **{cc['omega']}**. Umgekehrt ist die größte Clique des Konfliktgraphen ({cc['omega_conflict']}) so groß wie die größte unabhängige Menge des Verträglichkeitsgraphen ({cc['alpha']}). "
               "Wer eine größte Clique findet, findet damit auch die größte konfliktfreie Auswahl: Hier setzt die Knotenüberdeckung an, denn die Sendungen außerhalb einer größten unabhängigen Menge sind eine kleinste Überdeckung.")
else:
    st.error("Die Werte stimmen nicht überein: Das darf nicht passieren, bitte melden.")

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Die Färbung ist scharf** | Sie ist nur eine obere Schranke: Das Fünfeck hat die Cliquengröße 2, braucht aber 3 Farben. Wo die Färbung mehr Klassen als ω ergibt, muss der Suchbaum den Rest beweisen. | Chordale und perfekte Graphen (dort ist die Färbung scharf) |
| **Adjazenzabfragen als Aufwand** | Elementarschritte, keine Laufzeit. Reale Löser nutzen Bitmengen und stärkere Schranken (MaxSAT-Schlüsse), die auf großen dünnen Graphen aus der Praxis die Färbung schlagen; die Demo baut sie nicht nach. | – |
| **Eine größte Fuhre genügt** | Gebraucht werden manchmal alle maximalen Fuhren oder die k besten. | Aufzählen aller maximalen Cliquen |
| **Nur paarweise Verträglichkeit** | Ein Graph kann nur „A und B nie zusammen“ ausdrücken. Regeln für Dreiergruppen brauchen einen Hypergraphen. | – |
| **Kleine Graphen** | Bis n = 60 in der Hauptansicht (Strukturen bis n = 2000); auf Graphen mit Millionen Kanten unterscheiden sich die Verfahren anders. | – |
| **Synthetische Graphen** | Die Graphen sind erzeugt, keine echten Sendungsdaten. | – |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Problem.** Gegeben ein ungerichteter Graph $G = (V, E)$ und Gewichte $w_v \ge 1$. Gesucht ist eine Clique $C \subseteq V$ mit größtem Wert $w(C) = \sum_{v \in C} w_v$; ohne Gewichte ist $w_v = 1$ und der Wert die Größe $\omega(G)$.

**Färbungsschranke.** Eine Färbung der Kandidaten $P$ ist eine Zerlegung $P = K_1 \cup \dots \cup K_k$ in Klassen ohne Kante innerhalb einer Klasse. Eine Clique enthält je Klasse höchstens einen Knoten (zwei Knoten derselben Klasse sind nicht benachbart), also

$$\omega(G[P]) \le k$$

und gewichtet

$$w(C) \le \sum_{j=1}^{k} \max_{v \in K_j} w_v \quad \text{für jede Clique } C \subseteq P.$$

Der Branch-and-Bound schneidet einen Teilbaum mit Clique $R$ und Kandidaten $P$ ab, wenn

$$w(R) + \text{Schranke}(P) \le w(C^*)$$

gilt, wobei $C^*$ die beste bisher gefundene Clique ist. Verzweigt wird von der zuletzt gefärbten Klasse rückwärts; die Schranke für die Kandidaten bis einschließlich Position $i$ ist die Summe der Klassenmaxima der Klassen, die dort vorkommen.

**Einfache Schranke.** Zum Vergleich

$$w(R) + \sum_{v \in P} w_v \le w(C^*)$$

(„Größe + Restkandidaten“).

**Kernzahl-Vorverarbeitung.** Die Kernzahl $c(v)$ ist der größte Wert $k$, für den $v$ in einem Teilgraphen mit Mindestgrad $k$ liegt (die Degeneracy $d$ ist das Maximum aller $c(v)$). Eine Clique mit $s$ Knoten ist ein Teilgraph vom Mindestgrad $s - 1$, also hat jeder ihrer Knoten

$$c(v) \ge s - 1.$$

Hat die Greedy-Startclique den Wert $L$ und ist $w_{\max}$ das größte Gewicht, braucht eine bessere Clique mindestens $\lfloor L / w_{\max} \rfloor + 1$ Knoten; es bleiben nur Knoten mit

$$c(v) \ge \lfloor L / w_{\max} \rfloor.$$

Bleibt kein Knoten übrig, ist die Startclique optimal. Außerdem gilt $\omega(G) \le d + 1$; die Lücke $d + 1 - \omega$ bestimmt, wie viel der Filter wegwerfen kann.

**Brücke.** Eine Menge ist genau dann eine Clique in $G$, wenn sie eine unabhängige Menge im Komplement $\overline{G}$ ist:

$$\omega(G) = \alpha(\overline{G})$$

**Annahmen.**

| Annahme | Inhalt | Wer setzt an |
|---|---|---|
| Paarweise Verträglichkeit | Eine Fuhre ist genau dann zulässig, wenn alle Paare verträglich sind | Hypergraph (nicht in der Reihe) |
| Gierige Färbung | Die Färbung ist nicht optimal (χ-Berechnung ist selbst schwer), nur eine Schranke | Chordale und perfekte Graphen |
| Adjazenzabfragen als Aufwand | Elementarschritte statt Laufzeit | – |

**Literatur.**
- Tomita, E., & Seki, T. (2003). *An efficient branch-and-bound algorithm for finding a maximum clique.* Discrete Mathematics and Theoretical Computer Science (DMTCS 2003), Lecture Notes in Computer Science 2731.
- San Segundo, P., Rodríguez-Losada, D., & Jiménez, A. (2011). *An exact bit-parallel algorithm for the maximum clique problem.* Computers & Operations Research 38(2), 571–581.
- Pattabiraman, B., Patwary, M. M. A., Gebremedhin, A. H., Liao, W., & Choudhary, A. (2013). *Fast algorithms for the maximum clique problem on massive sparse graphs.* WAW 2013, LNCS 8305, 156–169.
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html)."
)
