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
    lo: float | None = None
    hi: float | None = None
    options: tuple | None = None       # erlaubte Werte bei Auswahlreglern


SETTING_SPECS = {
    "type_select": SettingSpec("gt", str, C.DEFAULT_TYPE, options=tuple(C.GRAPH_TYPES)),
    "n_slider": SettingSpec("n", int, C.DEFAULT_N, C.N_MIN, C.N_MAX),
    "density_slider": SettingSpec("d", int, C.DEFAULT_DENSITY, C.DENSITY_MIN, C.DENSITY_MAX),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, 0, C.SEED_MAX),
    "bound_radio": SettingSpec("b", str, C.DEFAULT_BOUND, options=tuple(C.BOUNDS)),
    "order_select": SettingSpec("o", str, C.DEFAULT_ORDER, options=tuple(C.ORDERS)),
    "prune_check": SettingSpec("p", _to_bool, False),
    "objective_radio": SettingSpec("w", str, C.DEFAULT_OBJECTIVE, options=tuple(C.OBJECTIVES)),
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
