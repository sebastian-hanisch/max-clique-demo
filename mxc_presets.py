"""Permalink (Begrenzen), Presets und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio).

Alle Regler sind immer sichtbar und immer wirksam (keine ausblendbaren Regler, also kein KEPT-Muster nötig): die Startordnung wirkt bei beiden Schranken."""

import random
from dataclasses import dataclass

import streamlit as st

import mxc_constants as C


def _to_bool(raw):
    text = str(raw).strip().lower()
    if text in ("1", "true", "ja"):
        return True
    if text in ("0", "false", "nein"):
        return False
    raise ValueError(raw)


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: object
    default: object
    lo: object = None                  # bei Auswahlreglern: erste und letzte Option (für tests/test_layout.py)
    hi: object = None
    options: tuple | None = None       # erlaubte Werte bei Auswahlreglern


def _choice(url_param, default, options):
    return SettingSpec(url_param, str, default, options[0], options[-1], tuple(options))


SETTING_SPECS = {
    "type_select": _choice("gt", C.DEFAULT_TYPE, tuple(C.GRAPH_TYPES)),
    "n_slider": SettingSpec("n", int, C.DEFAULT_N, C.N_MIN, C.N_MAX),
    "density_slider": SettingSpec("d", int, C.DEFAULT_DENSITY, C.DENSITY_MIN, C.DENSITY_MAX),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, 0, C.SEED_MAX),
    "bound_radio": _choice("b", C.DEFAULT_BOUND, tuple(C.BOUNDS)),
    "order_select": _choice("o", C.DEFAULT_ORDER, tuple(C.ORDERS)),
    "prune_check": SettingSpec("p", _to_bool, False, False, True),
    "objective_radio": _choice("w", C.DEFAULT_OBJECTIVE, tuple(C.OBJECTIVES)),
}
PRESET_KEYS = {"type": "type_select", "n": "n_slider", "density": "density_slider", "seed": "seed_input", "bound": "bound_radio", "order": "order_select",
               "prune": "prune_check", "objective": "objective_radio"}


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def _coerce(spec, raw):
    """Wert aus der Adresszeile in den Reglerbereich bringen; None, wenn er nicht lesbar ist."""
    if isinstance(raw, list):               # ältere Streamlit-Versionen liefern Listen
        raw = raw[0] if raw else None
    try:
        value = spec.caster(raw)
    except (ValueError, TypeError):
        return None
    if spec.options is not None:
        return value if value in spec.options else None
    if spec.lo is not None:
        value = max(spec.lo, value)
    if spec.hi is not None:
        value = min(spec.hi, value)
    return value


def load_permalink_settings():
    """Einmal je Sitzung: Werte aus der Adresszeile übernehmen, auf die Reglergrenzen begrenzt."""
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            value = _coerce(spec, qp[spec.url_param])
            if value is not None:
                st.session_state[state_key] = value
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}; die Adresszeile spiegelt die Konfiguration (Wahrheitswerte als 1/0)."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(int(value)) if isinstance(value, bool) else str(value)
    except Exception:
        pass


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        if key in C.PRESETS[name]:
            st.session_state[state_key] = C.PRESETS[name][key]
    st.session_state.pop("step_owner", None)      # die Schritt-Ansicht beginnt beim neuen Szenario wieder vorn


def randomize_seed():
    st.session_state["seed_input"] = random.randint(0, C.SEED_MAX)


def aktives_preset():
    """Name des Presets, dessen Werte GENAU den aktuellen Einstellungen entsprechen, sonst None.

    Zustandslos: verglichen wird jeder Regler aus SETTING_SPECS (ein Preset ohne Eintrag für einen Regler meint dessen
    Standardwert) mit dem Session State. Ein später ergänzter Regler braucht nur seinen Eintrag in SETTING_SPECS,
    dann hebt auch seine Änderung die Markierung auf (tests/test_layout.py prüft das für jeden Regler)."""
    preset_key_of = {state_key: key for key, state_key in PRESET_KEYS.items()}
    for name, preset in C.PRESETS.items():
        if all(
            st.session_state.get(state_key, spec.default) == preset.get(preset_key_of.get(state_key), spec.default)
            for state_key, spec in SETTING_SPECS.items()
        ):
            return name
    return None


def sidebar_presets():
    """Schnellstart oben in der Seitenleiste; das aktive Preset ist hervorgehoben (`type="primary"`)."""
    if not C.PRESETS:
        return
    st.header("🎯 Schnellstart")
    st.caption("Ein Beispielszenario laden:")
    aktiv = aktives_preset()
    for name in C.PRESETS:
        st.button(
            name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP.get(name, ""), key=f"preset_{name}",
            type="primary" if aktiv == name else "secondary",
        )
