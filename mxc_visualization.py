"""Plotly-Figuren: Graph mit Zustand eines Schritts, Verlauf der besten Fuhre, Dichte-Sweep, Strukturen, Vorverarbeitung, Greedy. Alle Achsen fest (fixedrange)."""

import plotly.graph_objects as go

import mxc_constants as C
import mxc_evaluation as ev

_FONT = dict(size=13)
_PALETTE = C.CLASS_PALETTE


def _fix(fig, height=420, **layout):
    layout.setdefault("margin", dict(l=40, r=20, t=30, b=40))
    fig.update_layout(height=height, font=_FONT, **layout)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _edge_trace(pos, edges, color, width):
    xs, ys = [], []
    for u, v in edges:
        xs += [pos[u][0], pos[v][0], None]
        ys += [pos[u][1], pos[v][1], None]
    return go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=width), hoverinfo="skip", showlegend=False)


def class_color(number):
    """Farbe der Färbungsklasse (zyklisch, falls es mehr Klassen als Farben gibt)."""
    return _PALETTE[(number - 1) % len(_PALETTE)]


def build_graph_figure(graph, weights=None, event=None, best=()):
    """Der Verträglichkeitsgraph auf dem Kreis. Mit `event`: R grün; Kandidaten nach Färbungsklasse getönt (bei der einfachen Schranke einheitlich blau); die bisher beste Fuhre
    (`best`) rot umrandet und ihre Kanten rot. Ohne Event nur die beste Fuhre."""
    pos = graph.positions
    edges = graph.edges()
    fig = go.Figure()
    fig.add_trace(_edge_trace(pos, edges, C.COLOR_EDGE, 1))
    colors = [C.COLOR_IDLE] * graph.n
    sizes = [20] * graph.n
    outline_color = ["white"] * graph.n
    outline_width = [1] * graph.n
    if event is not None:
        for i, v in enumerate(event.P):
            colors[v] = class_color(event.classes[i]) if event.classes else C.COLOR_P
        for v in event.R:
            colors[v] = C.COLOR_R
            sizes[v] = 26
        r_set = set(event.R)
        inside = [(u, v) for u, v in edges if u in r_set and v in r_set]
        if inside:
            fig.add_trace(_edge_trace(pos, inside, C.COLOR_R, 4))
    best_set = set(best)
    for v in best_set:
        outline_color[v] = C.COLOR_BEST
        outline_width[v] = 4
    if len(best_set) > 1:
        fig.add_trace(_edge_trace(pos, [(u, v) for u, v in edges if u in best_set and v in best_set], C.COLOR_BEST, 2))
    labels = [str(i + 1) for i in range(graph.n)]
    hover = [graph.labels[i] + ("" if weights is None or max(weights) == 1 else f", Wert {weights[i]}") for i in range(graph.n)]
    text_colors = ["#333333" if c == C.COLOR_IDLE else "white" for c in colors]
    fig.add_trace(go.Scatter(
        x=[p[0] for p in pos], y=[p[1] for p in pos], mode="markers+text", text=labels, textposition="middle center", textfont=dict(color=text_colors, size=10),
        marker=dict(color=colors, size=sizes, line=dict(color=outline_color, width=outline_width)), hovertext=hover, hoverinfo="text", showlegend=False))
    for name, color in (("R: gewählt", C.COLOR_R), ("Kandidat (Farbe = Färbungsklasse)", C.COLOR_P)):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(color=color, size=12), name=name))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", marker=dict(color="white", size=12, line=dict(color=C.COLOR_BEST, width=4)), name="beste Fuhre bisher"))
    fig.add_trace(go.Scatter(x=[-1.25, 1.25], y=[-1.25, 1.25], mode="markers", marker=dict(opacity=0), hoverinfo="skip", showlegend=False))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
    return _fix(fig, 520, legend=dict(orientation="h", y=-0.02, x=0.5, xanchor="center"), margin=dict(l=10, r=10, t=10, b=40))


def build_history_figure(result, objective="size"):
    """Bester gefundener Wert über den Knoten des Suchbaums (Treppe): zeigt, wie früh die beste Fuhre gefunden wird und wie lange der Rest der Suche nur noch beweist."""
    xs = [h[0] for h in result.history]
    ys = [h[1] for h in result.history]
    fig = go.Figure()
    if xs:
        xs_ext = xs + [max(result.nodes, xs[-1])]
        ys_ext = ys + [ys[-1]]
        fig.add_trace(go.Scatter(x=xs_ext, y=ys_ext, mode="lines", line=dict(color=C.COLOR_R, width=3, shape="hv"), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", marker=dict(color=C.COLOR_BEST, size=10), showlegend=False,
                                 hovertemplate="Knoten %{x}: bester Wert %{y}<extra></extra>"))
    fig.update_xaxes(title="Knoten des Suchbaums")
    fig.update_yaxes(title="Wert der besten Fuhre" if objective == "value" else "Sendungen in der besten Fuhre", rangemode="tozero")
    return _fix(fig, 260)


def build_sweep_figure(rows, metric="nodes"):
    """Knoten bzw. Adjazenzabfragen über der Dichte, logarithmisch, vier Linien; offene Quadrate markieren Mediane, bei denen mindestens ein Lauf das Budget erreicht hat (nur bei der einfachen Schranke möglich: Untergrenze)."""
    names = {"simple": "einfach (Größe + Rest), Grad", "color_index": "Färbung, nach Nummer", "color": "Färbung, nach Grad", "color_degeneracy": "Färbung, nach Degeneracy"}
    fig = go.Figure()
    xs = [r["density"] for r in rows]
    for key, name in names.items():
        ys = [max(r[metric][key], 1) for r in rows]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", name=name, line=dict(color=C.COLOR_LINE[key], width=3), marker=dict(size=8),
                                 hovertemplate="Dichte %{x} %%: %{y:,.0f}<extra>" + name + "</extra>"))
        cut = [(r["density"], max(r[metric][key], 1)) for r in rows if r["aborted"][key]]
        if cut:
            fig.add_trace(go.Scatter(x=[c[0] for c in cut], y=[c[1] for c in cut], mode="markers", showlegend=False,
                                     marker=dict(symbol="square-open", size=14, color=C.COLOR_LINE[key], line=dict(width=2)),
                                     hovertemplate="mindestens ein Lauf abgebrochen: Untergrenze<extra></extra>"))
    fig.update_xaxes(title="Anteil verträglicher Paare (%)", dtick=10)
    fig.update_yaxes(title=("Knoten" if metric == "nodes" else "Adjazenzabfragen") + " (Median, logarithmisch)", type="log")
    return _fix(fig, 400, legend=dict(orientation="h", y=1.18, x=0.5, xanchor="center"))


def build_structure_figure(rows):
    """Je Struktur die Änderung durch die Färbungsschranke gegenüber „einfach“ in Prozent: Knoten und Adjazenzabfragen (negativ = weniger)."""
    names = [f"{r['name']} (ω = {r['omega']:.0f})" for r in rows]
    node_change = [100.0 * (r["nodes"]["color"] / r["nodes"]["simple"] - 1.0) for r in rows]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=names, x=node_change, orientation="h", name="Knoten", marker_color="#4c78a8", hovertemplate="%{x:+.1f} %%<extra>Knoten</extra>"))
    fig.add_trace(go.Bar(y=names, x=[ev.lookup_change(r) for r in rows], orientation="h", name="Adjazenzabfragen", marker_color="#e0a030", hovertemplate="%{x:+.1f} %%<extra>Adjazenzabfragen</extra>"))
    fig.update_xaxes(title="Änderung durch die Färbungsschranke gegenüber „einfach“ (%)", zeroline=True)
    fig.update_yaxes(autorange="reversed")
    return _fix(fig, 460, barmode="group", legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"), margin=dict(l=250, r=20, t=30, b=50))


def build_core_figure(rows):
    """Je Struktur der Anteil der Sendungen, die nach der Kernzahl-Vorverarbeitung im Suchgraphen bleiben, mit der Lücke d + 1 − ω in der Beschriftung."""
    names = [f"{r['name']} (Lücke {r['gap']:.0f})" for r in rows]
    fig = go.Figure(go.Bar(y=names, x=[100.0 * r["kept_share"] for r in rows], orientation="h", marker_color=C.COLOR_R,
                           hovertemplate="%{x:.0f} %% der Sendungen bleiben<extra></extra>"))
    fig.update_xaxes(title="Sendungen, die nach der Vorverarbeitung bleiben (%)", range=[0, 105])
    fig.update_yaxes(autorange="reversed")
    return _fix(fig, 380, margin=dict(l=260, r=20, t=20, b=50))


def build_prep_cost_figure(rows):
    """Adjazenzabfragen mit und ohne Vorverarbeitung (Färbungsschranke, Startordnung Degeneracy), logarithmisch; die Vorverarbeitung ist eingerechnet."""
    names = [r["name"] for r in rows]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=names, x=[max(r["lookups_without"], 1) for r in rows], orientation="h", name="ohne Vorverarbeitung", marker_color="#4c78a8"))
    fig.add_trace(go.Bar(y=names, x=[max(r["lookups_with"], 1) for r in rows], orientation="h", name="mit Vorverarbeitung", marker_color="#e0a030"))
    fig.update_xaxes(title="Adjazenzabfragen (Median, logarithmisch)", type="log")
    fig.update_yaxes(autorange="reversed")
    return _fix(fig, 400, barmode="group", legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"), margin=dict(l=260, r=20, t=30, b=50))


def build_greedy_figure(rows):
    """Je Struktur der Anteil der Instanzen, in denen die Greedy-Heuristik die größte Clique trifft."""
    names = [f"{r['name']} (mittlere Lücke {r['mean_gap']:.1f})".replace(".", ",") for r in rows]
    fig = go.Figure(go.Bar(y=names, x=[100.0 * r["exact"] / r["runs"] for r in rows], orientation="h", marker_color=C.COLOR_R,
                           hovertemplate="%{x:.0f} %% der Instanzen exakt<extra></extra>"))
    fig.update_xaxes(title="Instanzen, in denen Greedy die größte Clique trifft (%)", range=[0, 100])
    fig.update_yaxes(autorange="reversed")
    return _fix(fig, 320, margin=dict(l=300, r=20, t=20, b=50))
