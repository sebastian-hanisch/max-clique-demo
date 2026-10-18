# Größte Clique: Färbungsschranke und Kernzahl – Streamlit-Demo

<!-- TODO nach dem Deploy: direkt hierher den Live-Link setzen (Leerzeile davor und danach):
**[→ Demo live ausprobieren](https://sebastianhanisch-max-clique-demo.streamlit.app/)** -->

Zweites Stück der **Härte-und-Struktur-Reihe** der „Konzepte“-Reihe für die Website „Sebastian Hanisch – Operations Research und Machine Learning“. Die Reihe fragt, welche Struktur ein auf Graphen schweres Problem leicht macht (Cliquen, unabhängige Mengen, Überdeckungen, Baumweite). Das erste Stück ([bron-kerbosch-demo](https://github.com/sebastian-hanisch/bron-kerbosch-demo)) zählt **alle** maximalen Cliquen auf und zeigt, dass es davon bis 3^(n/3) geben kann. Dieses Stück sucht nur die **größte** (Kante `fix`: Aufzählen ist Verschwendung, wenn nur die größte gebraucht wird) mit **Branch-and-Bound** und fragt, wie gut die **obere Schranke** ist, mit der er Teilbäume abschneidet: die einfache Schranke „Größe + Restkandidaten“ gegen die **Färbungsschranke** (Tomita und Seki 2003), dazu eine **Vorverarbeitung** (Greedy-Startclique plus Kernzahl-Filter) und die **Greedy-Heuristik** als Kontrast. Anders als die Fall-Demos zeigt die Demo ein Verfahren an einem wachsenden Beispiel: dem **Verträglichkeitsgraphen einer Sammelladung** (Sendungen als Knoten, eine Kante heißt „dürfen zusammen verladen werden“; eine größte Clique ist die größte Fuhre, optional mit Werten je Sendung).

```
Bron–Kerbosch: alle maximalen Cliquen (Wurzel)
 ├─ Größte Clique: Färbungsschranke und Kernzahl                        [DIESES STÜCK]
 ├─ Knotenüberdeckung: Approximation, Kernbildung, Verzweigen
 ├─ Chordale und perfekte Graphen
 │    └─ Baumweite ─ Dynamische Programmierung auf der Baumzerlegung
 ├─ Kantenclique-Überdeckung und Kernbildung
 └─ Unabhängige Menge im großen Maßstab: Reduktionen und Lokalsuche
```

## Warum dieses Problem

Wer eine Fuhre packt, will meist die größte Gruppe von Sendungen, die sich alle paarweise vertragen. Diese Aufgabe ist NP-schwer; der Branch-and-Bound löst sie auf diesen Größen trotzdem schnell, **wenn seine Schranke gut ist**. Die Kernfrage der Demo: **Wie viel schneidet die Färbungsschranke gegenüber „Größe + Rest“ ab, und wann kostet sie mehr, als sie spart?** Beantwortet wird sie in zwei Maßen: **Knoten** des Suchbaums und **Adjazenzabfragen** („ist w ein Nachbar von v?“), ein einheitliches Maß für beide Schranken und die Vorverarbeitung. Es ist keine Laufzeit.

Abgrenzung: `graph-coloring-demo` nutzt die größte Clique als untere Schranke für die Färbung und enthält dafür die Funktion `clique_number` (Einschließen/Ausschließen, Schranke „Größe + Restkandidaten“) ohne eigene Darstellung, ohne Färbungsschranke und ohne Vorverarbeitung. Diese Demo baut genau diese Schranke als Referenz nach (nicht importiert) und tritt dagegen an. Auch `constraint-programming-demo` kennt Paarunverträglichkeiten, aber als Nebenbedingung neben einer Kapazität, nicht als Graphthema.

## Modell

Ungerichteter Graph G = (V, E) mit ganzzahligen Gewichten w_v ≥ 1 (bei „Anzahl der Sendungen“ überall 1, bei „Wert der Fuhre“ gleichverteilt 1 bis 9 aus einem eigenen Generator). Gesucht ist die Clique mit dem größten Gesamtwert. Graphtypen: **Zufallsregeln** (jedes Paar unabhängig verträglich), **Zeitfenster** (verträglich, wenn die Fenster überlappen: ein Intervallgraph; die Fensterlänge l erfüllt 1 − (1 − l)² = Anteil verträglicher Paare), **Klassenregeln** (sechs Sendungsklassen, ein Klassenpaar ist verträglich oder nicht). Alle Graphen sind synthetisch; der Zufall kommt aus `random.Random(seed)`, die Algorithmen sind vollständig deterministisch. Formeln und Literatur stehen im 📐-Expander der App.

## Methodik

| Verfahren | Idee |
|---|---|
| **Einfache Schranke** („Größe + Rest“) | Einschließen/Ausschließen je erstem Kandidaten; abgeschnitten wird, wenn Größe + Zahl der Restkandidaten nicht größer ist als die beste Fuhre (bei Gewichten: Gesamtgewicht der Kandidaten). Die Referenz aus `graph-coloring-demo`. |
| **Färbungsschranke** (Tomita und Seki 2003) | Die Kandidaten werden gierig in Klassen paarweise nicht verträglicher Sendungen gefärbt; eine Fuhre nimmt höchstens eine Sendung je Klasse, also ist die Klassenzahl (bei Gewichten die Summe der Klassenmaxima) eine obere Schranke. Verzweigt wird von der zuletzt gefärbten Klasse rückwärts. |
| **Startordnung** | Reihenfolge der Kandidaten: nach Nummer, nach Grad (größter zuerst) oder nach Degeneracy (kleinster Restgrad zuletzt); wirkt bei beiden Schranken. |
| **Vorverarbeitung** | Greedy-Startclique als untere Schranke, dazu der Kernzahl-Filter: In einer Clique der Größe s hat jeder Knoten Kernzahl ≥ s − 1; bleibt kein Knoten übrig, ist die Greedy-Clique ohne Suche als optimal bewiesen. Die eigenen Abfragen (Kernzahlen, Greedy) zählen mit. |
| **Greedy-Heuristik** | Immer die Sendung mit den meisten Nachbarn im Kandidatenrest (Gleichstand: größeres Gewicht, dann kleinerer Index). |

Die App zeigt den Suchbaum Schritt für Schritt (die ersten 400 Ereignisse, Abspielen mit ▶️; die Kandidaten sind nach Färbungsklasse getönt), vergleicht beide Schranken live und rechnet vier Experimente.

## Befunde (gemessen, keine Behauptungen)

Jede Zahl steht in `tests/test_claims.py`. Alle Knoten- und Abfragezahlen sind ganzzahlig und plattformunabhängig exakt. Sweeps sind Mediane über fünf feste Graphen, die Strukturtabellen über drei, der Greedy-Vergleich über 20 (feste Seeds); Läufe der einfachen Schranke sind auf 60 000 Knoten begrenzt (Hauptansicht: 200 000), die Mediane solcher Zeilen sind Untergrenzen.

| Frage | Befund |
|---|---|
| Standardfall (24 Sendungen, 50 %, Zufallsregeln, Seed 35, Startordnung Grad)? | Größte Fuhre 6 Sendungen. Einfache Schranke 374 Knoten und 1 502 Abfragen, Färbung **12 Knoten und 405 Abfragen** (Faktor 31,2 weniger Knoten, Faktor 3,71 weniger Abfragen). Greedy trifft 6, Degeneracy 10, Färbungsschranke an der Wurzel 8. |
| Was spart die Färbung bei dichten Graphen? | Preset „Dicht“ (40 Sendungen, 80 %): größte Fuhre 13, **28 507 Knoten gegen 88** (Faktor 324), 179 551 gegen 8 612 Abfragen (Faktor 20,9). Dichte-Sweep (n = 40): bei Zufallsregeln Faktor 20,4 weniger Knoten bei 20 % verträglichen Paaren bis **mindestens Faktor 1 250 bei 90 %** (die einfache Schranke erreicht dort in allen fünf Instanzen die Grenze); Zeitfenster Faktor 13,9 bis mindestens 1 875, Klassenregeln Faktor 55 bis mindestens 2 000. |
| Gewinnt die Färbung auch bei den Abfragen? | Im Dichte-Sweep (n = 40) **in jeder Dichte und jeder Regelart**: Faktor 2,0 (Zufall, 10 %), 1,9 (Zeitfenster, 10 %) bzw. 2,7 (Klassen, 10 %) bis mindestens Faktor 99 (Zufall und Zeitfenster) bzw. 205 (Klassen). |
| Wann kostet die Färbung mehr, als sie spart? | **Auf sehr dünnen Graphen.** Zufall n = 1 500, 1 % verträglich: 19 492 Knoten einfach gegen 791 mit Färbung (Faktor 24,6 weniger), aber **1 292 933 gegen 1 191 416 Abfragen, also +8,5 % mehr**. Zufall n = 500, 5 %: nur −9,3 % Abfragen bei Faktor 38 weniger Knoten. Bei dichten oder strukturierten Graphen −92 bis −99 %, beim Baum n = 500 −38,4 %, beim skalenfreien Netz n = 2 000 −48,6 %. |
| Hilft die Kernzahl-Vorverarbeitung auf dünnen großen Graphen? | **Nein.** Zufall n = 500, 5 % und n = 1 500, 1 %: jede Sendung bleibt (Lücke d + 1 − ω = 15 bzw. 8). Sie wirft nur dort Sendungen weg, wo die Lücke höchstens 7 beträgt: Zeitfenster n = 100 (56 von 100 bleiben, Lücke 0), Klassenregeln n = 80 (67 von 80, Lücke 7), Baum (0 von 500, Lücke 0). Eine kleine Lücke allein genügt nicht: beim skalenfreien Netz (Lücke 1) bleiben alle 2 000, weil jede Sendung Kernzahl ≥ ω hat. |
| Beweist die Vorverarbeitung die Lösung, und spart sie Arbeit? | Beim Baum in allen 3 Instanzen ohne Suche (2 026 statt 83 473 Abfragen, Faktor 41), bei den Klassenregeln in 1 von 3. Beim Preset „Zeitfenster“ (60 Sendungen, 50 %) beweist sie die Greedy-Clique (23) mit **0 Knoten**, braucht aber **13 496 Abfragen gegen 6 848 für die Färbung allein**. Insgesamt senkt sie die Abfragen nur in 2 von 8 Strukturen (Baum, skalenfrei: 785 451 gegen 1 197 605); beim Zeitfenster n = 100 verdoppelt sie sie fast (67 415 gegen 25 955, Faktor 2,6). |
| Wie viel ändert die Startordnung? | Wenig und uneinheitlich: Zufall, 50 %: 28 (nach Nummer), 26 (Grad), 32 (Degeneracy) Knoten; Zeitfenster, 90 %: 6 044 (Nummer) gegen 6 174 (Grad) Abfragen. |
| Wie weit liegt die Greedy-Heuristik daneben? | Sie trifft die größte Clique in 4 bis 18 von 20 Instanzen: Zufall n = 40, 50 %: 12/20 (mittlere Lücke 0,4); Zufall n = 60, 70 %: 4/20 (1,2); Zeitfenster n = 80: 6/20 (1,3); Klassenregeln n = 80: 11/20 (3,4, **in einer Instanz 18 Sendungen zu wenig**); skalenfrei n = 500: 18/20 (0,1). Auf der Mini-Instanz mit Wert 9 an einer Sendung verfehlt sie das gewichtete Optimum (3 statt 10). |
| Trägt die gewichtete Färbungsschranke ebenso? | Ja, in den vier gemessenen Fällen (n = 30 und 40, 50 % und 70 %) Faktor 7,6 bis 23,5 weniger Knoten (449 → 59, 1 325 → 72, 936 → 68, 4 094 → 174), und weniger Abfragen. |
| Gilt „größte Clique = größte unabhängige Menge des Komplements“? | Ja, auf dem Standardgraph mit 14 Sendungen: 4 = 4, umgekehrt 5 = 5, geprüft gegen das Aufzählen aller Teilmengen (ohne Branch-and-Bound). |

## Befunde und Korrekturen gegenüber dem Plan

Vor dem Bau lag eine Vormessung vor (andere Zählweise der Schritte). Sie bestätigte den Gewinn der Färbungsschranke und **widerlegte zwei Annahmen des Planentwurfs**: dass die Kernzahl-Beschneidung auf dünnen großen Graphen hilft (sie hilft nur bei kleiner Lücke d + 1 − ω), und dass die Färbung überall auch in Elementarschritten gewinnt (nicht auf sehr dünnen Graphen). Beides ist als Experiment 2 und 3 Teil der Demo. Die zwei Schrittmaße der Vormessung sind durch ein einheitliches Maß (Adjazenzabfragen) ersetzt; der Befund auf dem sehr dünnen Graphen blieb bestehen (+8,5 %). Weitere Abweichungen vom Einzelplan: kein PDF-Export (Konzepte-Demos haben üblicherweise keinen); die Startordnung wirkt bei beiden Schranken (kein toter Regler); Experiment 1 rechnet bei fester Knotenzahl n = 40, unabhängig vom Regler; die Vorverarbeitung enthält die Greedy-Startclique als untere Schranke (nicht nur den Kernzahl-Filter).

## Ehrliche Grenzen

- **Adjazenzabfragen sind Elementarschritte, keine Laufzeit.** Reale Implementierungen nutzen Bitmengen, und die Kosten je Abfrage unterscheiden sich. Hier Python-Mengen.
- **Die Färbung ist nur eine Schranke.** Sie ist nicht scharf: das Fünfeck hat die Cliquengröße 2, braucht aber 3 Farben (Test). Wo die Färbung mehr Klassen als ω ergibt, muss der Suchbaum den Rest beweisen.
- **Stärkere Schranken fehlen.** Löser mit MaxSAT-Schlüssen (z. B. MaxCLQ) schneiden auf großen dünnen Graphen aus der Praxis mehr ab als die Färbung; die Demo baut sie nicht nach. Dort ist auch die Kernzahl-Beschneidung nach Pattabiraman u. a. ein Baustein; die hier gezeigte Vorverarbeitung ist ihre einfachste Form.
- **Rechengrenze.** Die einfache Schranke bricht nach 200 000 Knoten (Hauptansicht) bzw. 60 000 (Sweeps) ab und meldet es; die Zahlen solcher Zeilen sind Untergrenzen, in den Diagrammen mit offenen Quadraten markiert (Experiment 2: das „>“ in der Tabelle).
- **Kleine Graphen.** Hauptansicht bis n = 60, Strukturen bis n = 2 000.
- **Nur paarweise Verträglichkeit.** Regeln für Dreiergruppen brauchen einen Hypergraphen.
- **Synthetische Graphen.** Die Muster gelten für die Graphklassen, nicht für ein bestimmtes Lager.

## Verifikation

- **Kern:** jede Einheit (`core_decomposition`, `start_order`, `greedy_clique`, `core_keep`, `greedy_color_classes`, `color_prefix_bounds`, `simple_bound`) gegen Handrechnung auf der Mini-Instanz (Dreieck, Pendel, isolierter Knoten); Knoten- und Abfragezahlen der Komposition von Hand gerechnet (Färbung: 3 Knoten, 12 Abfragen; einfach: 6 Knoten, 8 Abfragen; Vorverarbeitung: 22 Abfragen, 0 Knoten), Fünfeck und K₄.
- **Orakel (`tests/test_oracle_max_clique.py`):** alle zwölf Konfigurationen (2 Schranken × 3 Startordnungen × Vorverarbeitung an/aus) gegen `networkx.max_weight_clique` auf über 300 festen Zufalls-, Zeitfenster-, Klassen- und Sonderinstanzen, je mit Anzahl- und Wertziel; gegen eine zweite, unabhängige Formulierung (OR-Tools CP-SAT) und gegen Brute Force über alle Teilmengen (n ≤ 12); Familien mit bekanntem Wert (Moon–Moser: ω = k, Baum: 2, vollständiger Graph: n, Zeitfenster: größte Zahl gleichzeitig offener Fenster, unabhängig per Sweep berechnet); α(Ḡ) = ω(G) gegen Brute Force.
- **Zweige (`tests/test_branches.py`):** jede Schranke, Startordnung, die Gewichte, die Vorverarbeitung weichen auf mindestens einer Instanz von der Nachbarvariante ab; die Schranke jedes Aufruf-Ereignisses liegt über dem Wert der besten Fortsetzung innerhalb der Kandidaten (gegen Brute Force); die Wurzelschranke der Färbung liegt nie über „Größe + Rest“; die Rechengrenzen greifen.
- **Zahlen:** `tests/test_claims.py` rechnet jede Zahl dieser README über dieselben Auswertungsfunktionen wie die App nach.
- **Oberfläche:** AppTest-Rauchtest (jeder Button, jeder Regler an Minimum und Maximum, jede Regelart, Startordnung, Schranke, Ziel, Vorverarbeitung, Extrem-Seeds, Permalink, langsamste Ecke) und Footer-Test.

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App: Schritt-Ansicht, Kernfrage, vier Experimente, Brücke, Grenzen, Mathematik |
| `mxc_algorithm.py` | Kern: Einheiten, Branch-and-Bound mit zwei Schranken, Vorverarbeitung, Brute-Force-Referenzen |
| `mxc_constants.py` | Regler-Grenzen, Rechengrenzen, Farben, Presets |
| `mxc_evaluation.py` | Einstellungen, Analyse, Sweeps (Dichte, Strukturen, Kernzahl, Greedy, gewichtet), Komplement-Prüfung |
| `mxc_presets.py` | Permalink (Begrenzen), Presets, Zufalls-Seed-Button |
| `mxc_scenario.py` | Graphen: Zufall, Zeitfenster, Klassenregeln, Moon–Moser, Baum, Gitter, skalenfrei; Gewichte |
| `mxc_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `requirements-dev.txt` | Laufzeit plus pytest, networkx und OR-Tools (nur für die Gegenproben) |
| `requirements.txt` | Laufzeit-Bibliotheken (ungepinnt) |
| `tests/` | Algorithmus, Orakel, Zweige, Szenarien, Zahlen, Figuren, Presets, AppTest, Footer |

## Bewusst nicht umgesetzt

- **Stärkere Schranken** (MaxSAT-Schlüsse, Neufärbung): eigener Aufbau, würde ein SAT-Gerüst verlangen.
- **Bitmengen-Implementierung und Parallelisierung:** die Demo zählt Abfragen, nicht Laufzeit.
- **Hypergraphen:** Regeln für mehr als zwei Sendungen.
- **PDF-Export** (siehe Korrekturen oben).

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Literatur

- Tomita, E., & Seki, T. (2003). *An efficient branch-and-bound algorithm for finding a maximum clique.* Discrete Mathematics and Theoretical Computer Science (DMTCS 2003), Lecture Notes in Computer Science 2731.
- San Segundo, P., Rodríguez-Losada, D., & Jiménez, A. (2011). *An exact bit-parallel algorithm for the maximum clique problem.* Computers & Operations Research 38(2), 571–581.
- Pattabiraman, B., Patwary, M. M. A., Gebremedhin, A. H., Liao, W., & Choudhary, A. (2013). *Fast algorithms for the maximum clique problem on massive sparse graphs.* WAW 2013, LNCS 8305, 156–169.

Gebaut mit Streamlit, Plotly und pandas.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zu den Demos: [Interaktive Demos](https://sebastianhanisch.net/demos.html).
