"""Presets: Vollständigkeit, gültige Werte, Standard-Preset = Standardeinstellungen; Permalink-Begrenzung."""

import pytest
from streamlit.testing.v1 import AppTest

import mxc_constants as C
import mxc_evaluation as ev
import mxc_presets as P


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP)
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS), name
        assert C.PRESET_HELP[name]


def test_preset_values_are_inside_the_slider_bounds_and_options():
    for name, p in C.PRESETS.items():
        assert C.N_MIN <= p["n"] <= C.N_MAX and C.DENSITY_MIN <= p["density"] <= C.DENSITY_MAX and 0 <= p["seed"] <= C.SEED_MAX, name
        assert p["type"] in C.GRAPH_TYPES and p["bound"] in C.BOUNDS and p["order"] in C.ORDERS and p["objective"] in C.OBJECTIVES, name
        assert isinstance(p["prune"], bool), name


def test_default_settings_are_valid_and_inside_the_bounds():
    s = ev.Settings()
    assert s.graph_type in C.GRAPH_TYPES and s.bound in C.BOUNDS and s.order in C.ORDERS and s.objective in C.OBJECTIVES
    assert C.N_MIN <= s.n <= C.N_MAX and C.DENSITY_MIN <= s.density <= C.DENSITY_MAX and s.prune is False


def test_setting_specs_cover_every_preset_key_and_url_params_are_unique():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)
    params = [spec.url_param for spec in P.SETTING_SPECS.values()]
    assert len(params) == len(set(params))


def test_every_preset_runs_and_finishes_without_abort():
    for name, p in C.PRESETS.items():
        s = ev.Settings(graph_type=p["type"], n=p["n"], density=p["density"], seed=p["seed"], bound=p["bound"], order=p["order"], prune=p["prune"], objective=p["objective"])
        a = ev.analyse(s)
        assert a.complete and not a.result.aborted, name


def test_coerce_clamps_numbers_and_rejects_unknown_choices_and_reads_booleans():
    n_spec = P.SETTING_SPECS["n_slider"]
    assert P._coerce(n_spec, "9999") == C.N_MAX and P._coerce(n_spec, "-5") == C.N_MIN and P._coerce(n_spec, "abc") is None
    assert P._coerce(P.SETTING_SPECS["type_select"], "windows") == "windows" and P._coerce(P.SETTING_SPECS["type_select"], "zzz") is None
    assert P._coerce(n_spec, ["12"]) == 12
    prune = P.SETTING_SPECS["prune_check"]
    assert P._coerce(prune, "1") is True and P._coerce(prune, "0") is False and P._coerce(prune, "maybe") is None


def _probe():
    import streamlit as st

    import mxc_presets as P
    P.load_permalink_settings()
    P.init_session_state_defaults()
    st.session_state["seen"] = {k: st.session_state[k] for k in P.SETTING_SPECS}


def test_permalink_is_clamped_to_the_bounds_and_invalid_values_fall_back():
    at = AppTest.from_function(_probe)
    at.query_params["n"] = "9999"
    at.query_params["d"] = "-3"
    at.query_params["gt"] = "windows"
    at.query_params["b"] = "nonsense"
    at.query_params["p"] = "1"
    at.run()
    assert not at.exception
    seen = at.session_state["seen"]
    assert seen["n_slider"] == C.N_MAX and seen["density_slider"] == C.DENSITY_MIN
    assert seen["type_select"] == "windows" and seen["bound_radio"] == C.DEFAULT_BOUND and seen["prune_check"] is True


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_apply_preset_writes_every_state_key(name):
    def _apply(preset_name):
        import streamlit as st

        import mxc_presets as P
        P.init_session_state_defaults()
        P.apply_preset(preset_name)
        st.session_state["seen"] = {k: st.session_state[k] for k in P.SETTING_SPECS}

    at = AppTest.from_function(_apply, args=(name,))
    at.run()
    assert not at.exception
    p = C.PRESETS[name]
    seen = at.session_state["seen"]
    assert (seen["n_slider"], seen["type_select"], seen["density_slider"], seen["bound_radio"], seen["order_select"], seen["prune_check"], seen["objective_radio"]) == \
        (p["n"], p["type"], p["density"], p["bound"], p["order"], p["prune"], p["objective"])


def test_first_preset_equals_the_default_settings():
    first = C.PRESETS[next(iter(C.PRESETS))]
    assert ev.Settings(graph_type=first["type"], n=first["n"], density=first["density"], seed=first["seed"], bound=first["bound"], order=first["order"], prune=first["prune"],
                       objective=first["objective"]) == ev.Settings()
