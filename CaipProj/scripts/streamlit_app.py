#!/usr/bin/env python3
"""Minimal Streamlit demo for WAPDA-model maintenance cost inference."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import streamlit as st

from caip_maintenance.app.fields import (
    SECTION_ORDER,
    default_snapshot,
    form_fields_from_preprocessor,
)
from caip_maintenance.app.inference import (
    DISCLAIMER,
    load_inference_bundle,
    predict_snapshot,
)
from caip_maintenance.features.ahs_inference import load_preprocessor_artifact


st.set_page_config(
    page_title="WAPDA Maintenance Cost Demo",
    page_icon="🏠",
    layout="wide",
)


@st.cache_resource
def _load_bundle(project_root: str):
    return load_inference_bundle(Path(project_root))


def _render_field(field, container):
    missing_label = "Missing / unknown"
    if field.kind == "wave_year":
        value = container.selectbox(
            field.label,
            options=[missing_label, *field.categories],
            index=1 if field.default in field.categories else 0,
            help=field.help_text,
        )
        return "" if value == missing_label else value
    if field.kind == "code":
        options = [missing_label, *field.categories]
        default_index = 0
        if field.default in field.categories:
            default_index = options.index(str(field.default))
        value = container.selectbox(
            field.label,
            options=options,
            index=default_index,
            help=field.help_text,
        )
        return "" if value == missing_label else value
    step = 1.0 if field.name in {"year_built", "total_rooms", "bedrooms", "unit_floors"} else 50.0
    default_value = float(field.default or 0)
    min_value = float(field.min_value) if field.min_value is not None else None
    max_value = float(field.max_value) if field.max_value is not None else None
    value = container.number_input(
        field.label,
        min_value=min_value,
        max_value=max_value,
        value=default_value,
        step=step,
        help=field.help_text,
    )
    return str(int(value)) if field.name in {
        "year_built",
        "total_rooms",
        "bedrooms",
        "unit_floors",
        "source_wave_year",
    } else f"{value:.4g}"


def main() -> None:
    st.title("WAPDA staff-colony maintenance cost demo")
    st.caption(
        "Enter property facts on the WAPDA data model. The app scores baselines and tuned "
        "XGBoost on the mapped public proxy corpus."
    )

    try:
        preprocessor = load_preprocessor_artifact(ROOT, "ahs-feature-engineering-v1")
        bundle = _load_bundle(str(ROOT))
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.info(
            "Build prerequisites from the repo root:\n\n"
            "```\n"
            "PYTHONPATH=src .venv/bin/python -m caip_maintenance.data preprocess-ahs \\\n"
            "  --preprocessor ahs-feature-engineering-v1\n"
            "PYTHONPATH=src .venv/bin/python -m caip_maintenance.data train-ahs-xgboost-tuning\n"
            "```"
        )
        return

    with st.sidebar:
        st.subheader("Model bundle")
        st.write(f"Experiment: `{bundle.experiment_id}`")
        st.write(f"Preprocessor: `{bundle.preprocessor_id}`")
        st.write(f"Fitted model: `{bundle.model_name}`")
        st.write(f"High-cost cutoff: **USD {bundle.high_cost_threshold_usd:,.0f}**")
        st.divider()
        st.warning(DISCLAIMER)

    fields = form_fields_from_preprocessor(preprocessor)
    by_section: dict[str, list] = {name: [] for name in SECTION_ORDER}
    for field in fields:
        by_section.setdefault(field.section, []).append(field)

    if "snapshot" not in st.session_state:
        st.session_state.snapshot = default_snapshot(preprocessor)

    tab_labels = [name for name in SECTION_ORDER if by_section.get(name)]
    tabs = st.tabs(tab_labels)
    snapshot = dict(st.session_state.snapshot)
    for tab, section in zip(tabs, tab_labels):
        cols = tab.columns(2)
        for index, field in enumerate(by_section[section]):
            col = cols[index % 2]
            snapshot[field.name] = _render_field(field, col)

    st.session_state.snapshot = snapshot

    if st.button("Estimate maintenance cost", type="primary", use_container_width=True):
        try:
            result = predict_snapshot(bundle, snapshot)
        except ValueError as exc:
            st.error(f"Could not score this input: {exc}")
            return

        st.subheader("Estimated routine maintenance (USD, proxy label)")
        rows = []
        for name, amount in result.predictions_usd.items():
            label = {
                "training_median": "Training median baseline",
                "type_median": "Type median baseline (policy primary)",
                "prior_cost": "Prior cost baseline (high-cost reference)",
                "xgboost": "Tuned XGBoost",
            }.get(name, name)
            rows.append(
                {
                    "Method": label,
                    "Predicted USD": round(amount, 2),
                    "High cost?": "Yes" if result.high_cost_flags[name] else "No",
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)

        primary = result.predictions_usd["type_median"]
        fitted = result.predictions_usd[result.model_name]
        prior = result.predictions_usd["prior_cost"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Policy cost estimate", f"USD {primary:,.0f}")
        c2.metric("Tuned XGBoost", f"USD {fitted:,.0f}")
        c3.metric(
            "High-cost flag (prior cost rule)",
            "Yes" if result.high_cost_flags["prior_cost"] else "No",
        )

        st.info(
            "The dataset is built on the WAPDA residential data model but trained on "
            "mapped AHS public records."
        )


if __name__ == "__main__":
    main()
