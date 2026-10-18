"""Konstanten: Regler-Grenzen, Rechengrenzen, feste Annahmen, Farben und Presets."""

N_MIN, N_MAX, DEFAULT_N = 6, 60, 24
DENSITY_MIN, DENSITY_MAX, DEFAULT_DENSITY = 5, 95, 50   # Anteil verträglicher Paare in Prozent
SEED_MAX, DEFAULT_SEED = 999999, 35
SWEEP_SEEDS = tuple(range(100000, 100005))              # feste Instanzen für alle Sweeps: nie ein einzelner Seed als Befund
W_MIN, W_MAX = 1, 9                                     # ganzzahlige Sendungswerte bei „Wert der Fuhre“

GRAPH_TYPES = {"random": "Zufallsregeln", "windows": "Zeitfenster", "classes": "Klassenregeln"}
DEFAULT_TYPE = "random"
N_CLASSES = 6

# Schranken im Branch-and-Bound
BOUNDS = {"simple": "Größe + Restkandidaten", "color": "Färbungsschranke"}
DEFAULT_BOUND = "color"
# Startordnung der Kandidaten (wirkt bei beiden Schranken: bei „einfach“ ist der erste Kandidat der Verzweigungsknoten, bei der Färbung die Reihenfolge der gierigen Färbung)
ORDERS = {"index": "nach Nummer", "degree": "nach Grad (größter zuerst)", "degeneracy": "nach Degeneracy (kleinster Grad zuletzt)"}
DEFAULT_ORDER = "degree"
OBJECTIVES = {"size": "Anzahl der Sendungen", "value": "Wert der Fuhre (Summe)"}
DEFAULT_OBJECTIVE = "size"

# Rechengrenzen: ein Knoten ist ein Aufruf des Branch-and-Bound. Wird das Budget überschritten, bricht der Lauf ab und meldet es.
NODE_BUDGET = 200_000        # Hauptansicht, je Verfahren
SWEEP_BUDGET = 60_000        # Sweeps und Vergleichstabellen, je Lauf
TRACE_LIMIT = 400            # so viele Ereignisse zeigt die Schritt-Ansicht höchstens
SWEEP_N = 40                 # feste Knotenzahl des Dichte-Sweeps (unabhängig vom Regler n)
SWEEP_DENSITIES = (10, 20, 30, 40, 50, 60, 70, 80, 90)
CHECK_N = 14                 # Knotenzahl der Komplement-Gegenprobe (Brute Force über alle Teilmengen)
GREEDY_SEEDS = tuple(range(200000, 200020))             # 20 feste Instanzen für den Greedy-Vergleich

# Farben
COLOR_R = "#2F6B65"          # bereits gewählte Sendungen (R)
COLOR_P = "#4c78a8"          # Kandidaten (ohne Färbung)
COLOR_IDLE = "#d9d9d9"       # nicht beteiligt
COLOR_EDGE = "rgba(150,150,150,0.35)"
COLOR_BEST = "#c0504d"       # beste bisher gefundene Fuhre
CLASS_PALETTE = ("#4c78a8", "#f58518", "#54a24b", "#b279a2", "#9d755d", "#e45756", "#72b7b2", "#bab0ac")
COLOR_LINE = {"simple": "#c0504d", "color": "#2F6B65", "color_index": "#4c78a8", "color_degeneracy": "#e0a030"}

PRESETS = {
    "Lehrbeispiel (klein)": {"type": "random", "n": 10, "density": 50, "seed": 3, "bound": "color", "order": "degree", "prune": False, "objective": "size"},
    "Dicht: die Färbung rettet": {"type": "random", "n": 40, "density": 80, "seed": DEFAULT_SEED, "bound": "simple", "order": "degree", "prune": False, "objective": "size"},
    "Dünn: kaum Suche nötig": {"type": "random", "n": 60, "density": 10, "seed": DEFAULT_SEED, "bound": "color", "order": "degree", "prune": False, "objective": "size"},
    "Zeitfenster mit Vorverarbeitung": {"type": "windows", "n": 60, "density": 50, "seed": DEFAULT_SEED, "bound": "color", "order": "degeneracy", "prune": True, "objective": "size"},
    "Klassenregeln mit Wert": {"type": "classes", "n": 40, "density": 50, "seed": DEFAULT_SEED, "bound": "color", "order": "degree", "prune": False, "objective": "value"},
}
PRESET_HELP = {
    "Lehrbeispiel (klein)": "10 Sendungen, jedes zweite Paar verträglich, Färbungsschranke: wenige Schritte, gut zum Durchklicken.",
    "Dicht: die Färbung rettet": "40 Sendungen, 80 % der Paare verträglich, aber mit der einfachen Schranke „Größe + Restkandidaten“: so viele Knoten wie nie nötig. Auf die Färbungsschranke umschalten und vergleichen.",
    "Dünn: kaum Suche nötig": "60 Sendungen, nur jedes zehnte Paar verträglich: Beide Schranken kommen mit wenigen Knoten aus.",
    "Zeitfenster mit Vorverarbeitung": "Verträglich heißt: die Zeitfenster überlappen. Die Greedy-Startclique ist hier schon optimal, und die Kernzahl-Vorverarbeitung beweist das ohne Suche (0 Knoten), braucht dafür aber mehr Adjazenzabfragen als die Färbungsschranke allein. In den Kennzahlen vergleichen.",
    "Klassenregeln mit Wert": "Sechs Sendungsklassen; gesucht ist die Fuhre mit dem größten Gesamtwert (Werte 1 bis 9), nicht die mit den meisten Sendungen.",
}
