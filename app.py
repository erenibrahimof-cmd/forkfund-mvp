from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.data_loader import compute_restaurant_metrics, load_raw_data, validate_raw_data
from src.scorer import (
    WEIGHTS,
    build_pop_context,
    generate_score_drivers,
    score_all_restaurants,
    score_restaurant,
)


DATA_DIR = "data"
DEMO_RESTAURANTS = ["Bonne Table", "Trattoria Pietro", "Levant Express"]

PAGES = [
    "Home / Concept Overview",
    "Restaurant Onboarding",
    "Credit Passport",
    "Lender Dashboard",
    "Methodology / About",
]

SCORE_COLUMNS = [
    "s1_data_completeness",
    "s2_revenue_stability",
    "s3_cashflow_strength",
    "s4_debt_burden",
    "s5_prime_cost",
    "s6_rent_pressure",
    "s7_pos_quality",
    "s8_seasonality",
    "s9_business_maturity",
]

SCORE_LABELS = {
    "s1_data_completeness": "Data completeness",
    "s2_revenue_stability": "Revenue stability",
    "s3_cashflow_strength": "Cash-flow strength",
    "s4_debt_burden": "Debt burden",
    "s5_prime_cost": "Prime cost",
    "s6_rent_pressure": "Rent pressure",
    "s7_pos_quality": "POS demand quality",
    "s8_seasonality": "Seasonality risk",
    "s9_business_maturity": "Business maturity",
}

DIMENSION_LABELS = {
    "data_completeness": "Data completeness and verification",
    "revenue_stability": "Revenue stability",
    "cashflow_strength": "Cash-flow strength",
    "debt_burden": "Debt burden and repayment capacity",
    "prime_cost": "Prime cost efficiency",
    "rent_pressure": "Rent / occupancy pressure",
    "pos_quality": "POS demand quality",
    "seasonality": "Seasonality and concentration risk",
    "business_maturity": "Business maturity",
}

st.set_page_config(
    page_title="ForkFund MVP",
    page_icon="FF",
    layout="wide",
)


@st.cache_data
def load_app_data(data_dir: str = DATA_DIR) -> dict[str, Any]:
    """Load raw CSVs, compute derived metrics, and score restaurants at runtime."""
    raw_data = load_raw_data(data_dir)
    validate_raw_data(raw_data)
    metrics = compute_restaurant_metrics(raw_data)
    scored = score_all_restaurants(metrics)
    return {"raw": raw_data, "metrics": metrics, "scored": scored}


def format_eur(value: float | int | None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"EUR {float(value):,.{decimals}f}"


def format_pct(value: float | int | None, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value) * 100:.{decimals}f}%"


def format_score(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{float(value):.1f}"


def restaurant_options(scored: pd.DataFrame) -> list[int]:
    demo_ids = (
        scored.loc[scored["legal_name"].isin(DEMO_RESTAURANTS), "restaurant_id"]
        .astype(int)
        .tolist()
    )
    demo_ids = sorted(
        demo_ids,
        key=lambda rid: DEMO_RESTAURANTS.index(
            scored.loc[scored["restaurant_id"] == rid, "legal_name"].iloc[0]
        ),
    )
    other_ids = (
        scored.loc[~scored["restaurant_id"].isin(demo_ids)]
        .sort_values(["legal_name", "restaurant_id"])["restaurant_id"]
        .astype(int)
        .tolist()
    )
    return demo_ids + other_ids


def restaurant_label(scored: pd.DataFrame, restaurant_id: int) -> str:
    row = scored.loc[scored["restaurant_id"] == restaurant_id].iloc[0]
    return (
        f"{row['legal_name']} | {row['city']} | "
        f"Grade {row['grade']} | Score {row['total_score']:.1f}"
    )


def selected_restaurant_id(scored: pd.DataFrame) -> int:
    if "selected_restaurant_id" not in st.session_state:
        default_id = int(
            scored.loc[scored["legal_name"] == "Bonne Table", "restaurant_id"].iloc[0]
        )
        st.session_state["selected_restaurant_id"] = default_id
    return int(st.session_state["selected_restaurant_id"])


def set_selected_restaurant(restaurant_id: int) -> None:
    st.session_state["selected_restaurant_id"] = int(restaurant_id)


def row_for(scored: pd.DataFrame, restaurant_id: int) -> pd.Series:
    return scored.loc[scored["restaurant_id"] == restaurant_id].iloc[0]


def display_source_status(row: pd.Series) -> None:
    source_cols = st.columns(4)
    source_cols[0].metric("Data completeness", format_pct(row["data_completeness"] / 100))
    source_cols[1].metric("Bank", "Connected" if row["bank_present"] else "Missing")
    source_cols[2].metric("POS", "Connected" if row["pos_present"] else "Missing")
    source_cols[3].metric(
        "Accounting", "Connected" if row["accounting_present"] else "Missing"
    )


def subscore_frame(row: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Dimension": [SCORE_LABELS[col] for col in SCORE_COLUMNS],
            "Score": [float(row[col]) for col in SCORE_COLUMNS],
        }
    )


def monthly_pos_for(raw: dict[str, pd.DataFrame], restaurant_id: int) -> pd.DataFrame:
    return (
        raw["monthly_pos"]
        .loc[raw["monthly_pos"]["restaurant_id"] == restaurant_id]
        .sort_values("month_number")
        .copy()
    )


def monthly_bank_for(raw: dict[str, pd.DataFrame], restaurant_id: int) -> pd.DataFrame:
    return (
        raw["monthly_bank"]
        .loc[raw["monthly_bank"]["restaurant_id"] == restaurant_id]
        .sort_values("month_number")
        .copy()
    )


def render_home_page(data: dict[str, Any]) -> None:
    scored = data["scored"]

    st.title("ForkFund")
    st.subheader("Restaurant Credit Passport and lender dashboard")

    st.write(
        "ForkFund turns synthetic restaurant identity, bank, POS, and accounting "
        "data into a standardised Credit Passport for Dutch restaurant financing."
    )

    flow_cols = st.columns(5)
    flow_steps = [
        ("1", "Restaurant profile"),
        ("2", "Mock data connected"),
        ("3", "Rules-based score"),
        ("4", "Credit Passport"),
        ("5", "Lender dashboard"),
    ]
    for col, (number, label) in zip(flow_cols, flow_steps):
        col.metric(number, label)

    st.markdown("### Demo restaurants")
    demo_rows = scored[scored["legal_name"].isin(DEMO_RESTAURANTS)].copy()
    demo_rows["demo_order"] = demo_rows["legal_name"].apply(DEMO_RESTAURANTS.index)
    demo_rows = demo_rows.sort_values("demo_order")

    demo_cols = st.columns(3)
    for col, (_, row) in zip(demo_cols, demo_rows.iterrows()):
        with col:
            st.markdown(f"#### {row['legal_name']}")
            st.metric("Grade", row["grade"], f"Score {row['total_score']:.1f}")
            st.write(f"{row['city']} - {row['risk_label']}")
            st.caption(
                f"{row['revenue_band']} | {format_eur(row['requested_loan_amount'])} "
                f"| {row['loan_purpose']}"
            )

    st.info(
        "All records are synthetic. Scores, grades, drivers, and peer percentiles "
        "are computed at runtime by the rules-based scoring engine."
    )


def render_restaurant_onboarding_page(data: dict[str, Any]) -> None:
    scored = data["scored"]
    current_id = selected_restaurant_id(scored)
    options = restaurant_options(scored)
    index = options.index(current_id) if current_id in options else 0

    st.title("Restaurant Onboarding")
    st.write("Select a synthetic restaurant profile to simulate onboarding.")

    restaurant_id = st.selectbox(
        "Restaurant profile",
        options,
        index=index,
        format_func=lambda rid: restaurant_label(scored, rid),
    )
    set_selected_restaurant(restaurant_id)
    row = row_for(scored, restaurant_id)

    st.markdown("### Identity")
    identity_cols = st.columns(3)
    identity_cols[0].metric("KvK number", f"{int(row['kvk_number']):08d}")
    identity_cols[1].metric("Legal name", row["legal_name"])
    identity_cols[2].metric("City", row["city"])
    identity_cols[0].metric("Registration date", str(row["registration_date"]))
    identity_cols[1].metric("Legal form", row["legal_form"])
    identity_cols[2].metric("Cuisine type", row["cuisine_type"])

    st.markdown("### Financing request")
    request_cols = st.columns(3)
    request_cols[0].metric("Requested loan", format_eur(row["requested_loan_amount"]))
    request_cols[1].metric("Loan purpose", row["loan_purpose"])
    request_cols[2].metric("Revenue band", row["revenue_band"])

    st.markdown("### Mock data connections")
    display_source_status(row)

    st.success(
        f"{row['legal_name']} is selected. Open the Credit Passport page to review "
        "the runtime score and drivers."
    )


def render_credit_passport_page(data: dict[str, Any]) -> None:
    raw = data["raw"]
    metrics = data["metrics"]
    scored = data["scored"]
    options = restaurant_options(scored)
    current_id = selected_restaurant_id(scored)
    index = options.index(current_id) if current_id in options else 0

    st.title("Restaurant Credit Passport")

    restaurant_id = st.selectbox(
        "Passport restaurant",
        options,
        index=index,
        format_func=lambda rid: restaurant_label(scored, rid),
    )
    set_selected_restaurant(restaurant_id)

    scored_row = row_for(scored, restaurant_id)
    metrics_row = metrics.loc[metrics["restaurant_id"] == restaurant_id].iloc[0]

    headline_cols = st.columns(4)
    headline_cols[0].metric("Score", f"{scored_row['total_score']:.1f}")
    headline_cols[1].metric("Grade", scored_row["grade"])
    headline_cols[2].metric("Risk label", scored_row["risk_label"])
    headline_cols[3].metric(
        "Peer percentile", f"{scored_row['peer_percentile']:.0f}%"
    )

    st.markdown("### Business identity and request")
    identity_cols = st.columns(4)
    identity_cols[0].metric("Restaurant", scored_row["legal_name"])
    identity_cols[1].metric("City", scored_row["city"])
    identity_cols[2].metric("Cuisine", scored_row["cuisine_type"])
    identity_cols[3].metric("Years active", f"{scored_row['years_active']:.1f}")

    request_cols = st.columns(4)
    request_cols[0].metric("Requested loan", format_eur(scored_row["requested_loan_amount"]))
    request_cols[1].metric("Loan purpose", scored_row["loan_purpose"])
    request_cols[2].metric("Annual revenue", format_eur(scored_row["annual_revenue"]))
    request_cols[3].metric("Revenue band", scored_row["revenue_band"])

    st.markdown("### Data completeness")
    display_source_status(scored_row)

    st.markdown("### Key restaurant metrics")
    metric_rows = [
        ("Prime cost ratio", format_pct(scored_row["prime_cost_ratio"])),
        ("Rent-to-revenue", format_pct(scored_row["rent_to_revenue"])),
        ("EBITDA margin", format_pct(scored_row["ebitda_margin"])),
        ("DSCR proxy", format_score(scored_row["dscr_proxy"])),
        ("Cash-flow margin", format_pct(scored_row["cash_flow_margin"])),
        ("Revenue CV", format_pct(scored_row["revenue_cv"])),
        ("Delivery share", format_pct(scored_row["delivery_share"])),
        ("Weekend share", format_pct(scored_row["weekend_share"])),
        ("Average check", format_eur(scored_row["average_check"], decimals=2)),
        ("Covers per seat/month", format_score(scored_row["covers_per_seat_month"])),
        ("RevPASH", format_eur(scored_row["revpash"], decimals=2)),
    ]
    metrics_table = pd.DataFrame(metric_rows, columns=["Metric", "Value"])
    st.dataframe(metrics_table, hide_index=True, use_container_width=True)

    st.markdown("### Nine scoring dimensions")
    subscores = subscore_frame(scored_row)
    st.bar_chart(subscores.set_index("Dimension"))
    st.dataframe(
        subscores.assign(Score=subscores["Score"].map(lambda value: f"{value:.1f}")),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("### Written drivers")
    pop_context = build_pop_context(metrics)
    breakdown = score_restaurant(metrics_row, pop_context)
    driver_result = generate_score_drivers(metrics_row, breakdown)

    positive_col, risk_col = st.columns(2)
    with positive_col:
        st.markdown("#### Top positives")
        if driver_result["top_positive"]:
            for driver in driver_result["top_positive"]:
                st.success(driver["text"])
        else:
            st.write("No positive drivers available.")

    with risk_col:
        st.markdown("#### Top risks")
        if driver_result["top_risk"]:
            for driver in driver_result["top_risk"]:
                st.warning(driver["text"])
        else:
            st.write("No risk drivers available.")

    st.markdown("### Monthly revenue")
    pos_months = monthly_pos_for(raw, restaurant_id)
    revenue_chart = pos_months.set_index("period")[["total_revenue"]]
    st.line_chart(revenue_chart)

    st.markdown("### Bank inflows versus outflows")
    bank_months = monthly_bank_for(raw, restaurant_id)
    bank_chart = bank_months.set_index("period")[["total_inflows", "total_outflows"]]
    st.line_chart(bank_chart)


def render_lender_dashboard_page(data: dict[str, Any]) -> None:
    scored = data["scored"].copy()

    st.title("Lender Dashboard")
    st.write("Filter the synthetic restaurant pool and open a Credit Passport.")

    summary_cols = st.columns(4)
    summary_cols[0].metric("Restaurants", f"{len(scored)}")
    summary_cols[1].metric("Average score", f"{scored['total_score'].mean():.1f}")
    summary_cols[2].metric("A/B profiles", int(scored["grade"].isin(["A", "B"]).sum()))
    summary_cols[3].metric("D/E profiles", int(scored["grade"].isin(["D", "E"]).sum()))

    grade_counts = scored["grade"].value_counts().reindex(list("ABCDE"), fill_value=0)
    risk_counts = scored["risk_label"].value_counts()
    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.markdown("### Grade distribution")
        st.bar_chart(grade_counts)
    with chart_cols[1]:
        st.markdown("### Risk labels")
        st.dataframe(
            risk_counts.rename_axis("Risk label").reset_index(name="Count"),
            hide_index=True,
            use_container_width=True,
        )

    st.markdown("### Revenue band by grade")
    crosstab = pd.crosstab(scored["revenue_band"], scored["grade"]).reindex(
        columns=list("ABCDE"), fill_value=0
    )
    st.dataframe(crosstab, use_container_width=True)

    st.markdown("### Filters")
    filter_cols = st.columns(3)
    cities = filter_cols[0].multiselect(
        "City",
        sorted(scored["city"].unique()),
        default=sorted(scored["city"].unique()),
    )
    grades = filter_cols[1].multiselect(
        "Grade", list("ABCDE"), default=list("ABCDE")
    )
    risk_labels = filter_cols[2].multiselect(
        "Risk label",
        sorted(scored["risk_label"].unique()),
        default=sorted(scored["risk_label"].unique()),
    )

    filter_cols = st.columns(3)
    revenue_bands = filter_cols[0].multiselect(
        "Revenue band",
        sorted(scored["revenue_band"].unique()),
        default=sorted(scored["revenue_band"].unique()),
    )
    loan_purposes = filter_cols[1].multiselect(
        "Loan purpose",
        sorted(scored["loan_purpose"].unique()),
        default=sorted(scored["loan_purpose"].unique()),
    )
    min_loan = int(scored["requested_loan_amount"].min())
    max_loan = int(scored["requested_loan_amount"].max())
    loan_range = filter_cols[2].slider(
        "Requested loan amount",
        min_value=min_loan,
        max_value=max_loan,
        value=(min_loan, max_loan),
        step=25_000,
    )

    min_completeness = st.slider(
        "Minimum data completeness",
        min_value=0,
        max_value=100,
        value=0,
        step=10,
    )

    with st.expander("Operating-risk filters"):
        risk_filter_cols = st.columns(4)
        max_prime_cost = risk_filter_cols[0].slider(
            "Max prime cost ratio", 0, 100, 100, 5
        )
        max_rent = risk_filter_cols[1].slider(
            "Max rent-to-revenue", 0, 30, 30, 1
        )
        max_delivery = risk_filter_cols[2].slider(
            "Max delivery share", 0, 100, 100, 5
        )
        max_weekend = risk_filter_cols[3].slider(
            "Max weekend share", 0, 100, 100, 5
        )

    filtered = scored[
        scored["city"].isin(cities)
        & scored["grade"].isin(grades)
        & scored["risk_label"].isin(risk_labels)
        & scored["revenue_band"].isin(revenue_bands)
        & scored["loan_purpose"].isin(loan_purposes)
        & scored["requested_loan_amount"].between(loan_range[0], loan_range[1])
        & (scored["data_completeness"] >= min_completeness)
        & (scored["prime_cost_ratio"] <= max_prime_cost / 100)
        & (scored["rent_to_revenue"] <= max_rent / 100)
        & (scored["delivery_share"] <= max_delivery / 100)
        & (scored["weekend_share"] <= max_weekend / 100)
    ].copy()

    st.markdown(f"### Matching restaurants ({len(filtered)})")
    display_cols = [
        "restaurant_id",
        "legal_name",
        "city",
        "revenue_band",
        "requested_loan_amount",
        "loan_purpose",
        "total_score",
        "grade",
        "risk_label",
        "peer_percentile",
        "prime_cost_ratio",
        "rent_to_revenue",
        "cash_flow_margin",
        "revenue_cv",
        "data_completeness",
    ]
    display_df = filtered[display_cols].rename(
        columns={
            "restaurant_id": "ID",
            "legal_name": "Restaurant",
            "city": "City",
            "revenue_band": "Revenue band",
            "requested_loan_amount": "Requested loan",
            "loan_purpose": "Loan purpose",
            "total_score": "Score",
            "grade": "Grade",
            "risk_label": "Risk label",
            "peer_percentile": "Peer percentile",
            "prime_cost_ratio": "Prime cost ratio",
            "rent_to_revenue": "Rent-to-revenue",
            "cash_flow_margin": "Cash-flow margin",
            "revenue_cv": "Revenue CV",
            "data_completeness": "Data completeness",
        }
    )
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    if filtered.empty:
        st.warning("No restaurants match the selected filters.")
    else:
        filtered_ids = filtered["restaurant_id"].astype(int).tolist()
        current_id = selected_restaurant_id(scored)
        default_index = filtered_ids.index(current_id) if current_id in filtered_ids else 0
        open_id = st.selectbox(
            "Select a restaurant to open in the Credit Passport",
            filtered_ids,
            index=default_index,
            format_func=lambda rid: restaurant_label(scored, rid),
        )
        if st.button("Use this restaurant for the Credit Passport"):
            set_selected_restaurant(open_id)
            st.success(
                "Restaurant selected. Open the Credit Passport page from the sidebar."
            )


def render_methodology_page() -> None:
    st.title("Methodology / About")

    st.write(
        "ForkFund is a technical MVP for pre-underwriting decision support in "
        "restaurant finance. It uses synthetic CSV data and a transparent "
        "rules-based scoring engine."
    )

    st.markdown("### Scoring model")
    weights_df = pd.DataFrame(
        [
            {
                "Dimension": DIMENSION_LABELS[key],
                "Weight": f"{weight * 100:.1f}%",
            }
            for key, weight in WEIGHTS.items()
        ]
    )
    st.dataframe(weights_df, hide_index=True, use_container_width=True)

    st.markdown("### Grade thresholds")
    grade_df = pd.DataFrame(
        [
            ("A", "85-100", "Low risk"),
            ("B", "70-84", "Low-to-medium risk"),
            ("C", "55-69", "Medium risk"),
            ("D", "40-54", "High risk"),
            ("E", "0-39", "Very high risk"),
        ],
        columns=["Grade", "Score range", "Risk band"],
    )
    st.dataframe(grade_df, hide_index=True, use_container_width=True)

    st.markdown("### Synthetic CSV backend")
    st.write(
        "The app reads restaurants, monthly bank summaries, monthly POS summaries, "
        "annual accounting data, and lender reference data from CSV files. Derived "
        "ratios, scores, grades, drivers, and peer percentiles are computed in "
        "memory at runtime."
    )

    st.markdown("### MVP limitations")
    limitations = [
        "No live PSD2 or open-banking connection",
        "No live KvK API",
        "No real lender offers or money movement",
        "No iDIN or BKR checks",
        "No authentication",
        "No production security or persistence",
        "No predictive machine-learning default model",
    ]
    for limitation in limitations:
        st.write(f"- {limitation}")


def main() -> None:
    data = load_app_data(DATA_DIR)

    st.sidebar.title("ForkFund Navigation")
    selected_page = st.sidebar.radio("Go to", PAGES)

    if "selected_restaurant_id" in st.session_state:
        row = row_for(data["scored"], int(st.session_state["selected_restaurant_id"]))
        st.sidebar.caption(
            f"Selected: {row['legal_name']} | Grade {row['grade']} | "
            f"Score {row['total_score']:.1f}"
        )

    if selected_page == "Home / Concept Overview":
        render_home_page(data)
    elif selected_page == "Restaurant Onboarding":
        render_restaurant_onboarding_page(data)
    elif selected_page == "Credit Passport":
        render_credit_passport_page(data)
    elif selected_page == "Lender Dashboard":
        render_lender_dashboard_page(data)
    elif selected_page == "Methodology / About":
        render_methodology_page()


if __name__ == "__main__":
    main()
