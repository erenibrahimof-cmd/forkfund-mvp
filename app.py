from __future__ import annotations

from html import escape
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

SCORE_DIMENSIONS = [
    ("data_completeness", "s1_data_completeness"),
    ("revenue_stability", "s2_revenue_stability"),
    ("cashflow_strength", "s3_cashflow_strength"),
    ("debt_burden", "s4_debt_burden"),
    ("prime_cost", "s5_prime_cost"),
    ("rent_pressure", "s6_rent_pressure"),
    ("pos_quality", "s7_pos_quality"),
    ("seasonality", "s8_seasonality"),
    ("business_maturity", "s9_business_maturity"),
]

SCORE_COLUMNS = [score_col for _, score_col in SCORE_DIMENSIONS]
SCORE_LABELS = {
    score_col: DIMENSION_LABELS[dim_key]
    for dim_key, score_col in SCORE_DIMENSIONS
}

GRADE_ORDER = list("ABCDE")

st.set_page_config(
    page_title="ForkFund MVP",
    page_icon="FF",
    layout="wide",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
            .ff-hero {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 1.15rem 1.25rem;
                background: #ffffff;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
                margin-bottom: 1rem;
            }
            .ff-card {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 1rem;
                background: #ffffff;
                min-height: 100%;
                box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            }
            .ff-metric-card {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 0.85rem 0.9rem;
                background: #ffffff;
                min-height: 116px;
            }
            .ff-flow-step {
                border: 1px solid #dbe3ee;
                border-radius: 8px;
                padding: 0.8rem;
                background: #f8fafc;
                min-height: 104px;
            }
            .ff-mini-label {
                color: #64748b;
                font-size: 0.74rem;
                font-weight: 700;
                letter-spacing: 0.03em;
                text-transform: uppercase;
                margin-bottom: 0.25rem;
            }
            .ff-muted {
                color: #64748b;
                font-size: 0.9rem;
                line-height: 1.45;
            }
            .ff-value {
                color: #0f172a;
                font-size: 1.35rem;
                font-weight: 750;
                line-height: 1.25;
                margin: 0.15rem 0;
            }
            .ff-small-value {
                color: #0f172a;
                font-size: 1.05rem;
                font-weight: 700;
                line-height: 1.25;
                margin: 0.15rem 0;
            }
            .ff-badge {
                display: inline-block;
                border-radius: 999px;
                padding: 0.18rem 0.56rem;
                font-size: 0.78rem;
                font-weight: 700;
                line-height: 1.25;
                margin-right: 0.25rem;
                margin-top: 0.25rem;
                white-space: nowrap;
            }
            .ff-grade-a { background: #dcfce7; color: #166534; }
            .ff-grade-b { background: #e0f2fe; color: #075985; }
            .ff-grade-c { background: #fef9c3; color: #854d0e; }
            .ff-grade-d { background: #ffedd5; color: #9a3412; }
            .ff-grade-e { background: #fee2e2; color: #991b1b; }
            .ff-risk-low { background: #dcfce7; color: #166534; }
            .ff-risk-low-to-medium { background: #e0f2fe; color: #075985; }
            .ff-risk-medium { background: #fef9c3; color: #854d0e; }
            .ff-risk-high { background: #ffedd5; color: #9a3412; }
            .ff-risk-very-high { background: #fee2e2; color: #991b1b; }
            .ff-driver-positive {
                border-left: 4px solid #16a34a;
                background: #f0fdf4;
                border-radius: 8px;
                padding: 0.85rem 0.95rem;
                margin-bottom: 0.65rem;
            }
            .ff-driver-risk {
                border-left: 4px solid #ea580c;
                background: #fff7ed;
                border-radius: 8px;
                padding: 0.85rem 0.95rem;
                margin-bottom: 0.65rem;
            }
            .ff-status-card {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 0.85rem;
                background: #ffffff;
                min-height: 98px;
            }
            .ff-status-connected { border-left: 4px solid #16a34a; }
            .ff-status-missing { border-left: 4px solid #dc2626; }
            .ff-status-dot {
                display: inline-block;
                width: 0.5rem;
                height: 0.5rem;
                border-radius: 999px;
                margin-right: 0.35rem;
                vertical-align: middle;
            }
            .ff-dot-connected { background: #16a34a; }
            .ff-dot-missing { background: #dc2626; }
            .ff-section-note {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 0.9rem 1rem;
                background: #f8fafc;
                color: #334155;
            }
            div[data-testid="stMetric"] {
                background: #ffffff;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 0.8rem 0.9rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_app_data(data_dir: str = DATA_DIR) -> dict[str, Any]:
    """Load raw CSVs, compute derived metrics, and score restaurants at runtime."""
    raw_data = load_raw_data(data_dir)
    validate_raw_data(raw_data)
    metrics = compute_restaurant_metrics(raw_data)
    scored = score_all_restaurants(metrics)
    return {"raw": raw_data, "metrics": metrics, "scored": scored}


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        missing = pd.isna(value)
    except TypeError:
        return False
    try:
        return bool(missing)
    except ValueError:
        return False


def html_escape(value: Any) -> str:
    if is_missing(value):
        return "n/a"
    return escape(str(value))


def format_eur(value: float | int | None, decimals: int = 0) -> str:
    if is_missing(value):
        return "n/a"
    return f"EUR {float(value):,.{decimals}f}"


def format_pct(
    value: float | int | None,
    decimals: int = 1,
    *,
    already_percent: bool = False,
) -> str:
    if is_missing(value):
        return "n/a"
    number = float(value)
    if not already_percent:
        number *= 100
    return f"{number:.{decimals}f}%"


def format_score(value: float | int | None, decimals: int = 1) -> str:
    if is_missing(value):
        return "n/a"
    return f"{float(value):.{decimals}f}"


def grade_class(grade: Any) -> str:
    grade_key = str(grade).lower() if not is_missing(grade) else "e"
    return f"ff-grade-{grade_key}" if grade_key in list("abcde") else "ff-grade-e"


def risk_class(label: Any) -> str:
    risk_key = str(label).lower().replace(" ", "-") if not is_missing(label) else ""
    risk_key = risk_key.replace("--", "-")
    allowed = {
        "low-risk",
        "low-to-medium-risk",
        "medium-risk",
        "high-risk",
        "very-high-risk",
    }
    return f"ff-risk-{risk_key.replace('-risk', '')}" if risk_key in allowed else "ff-risk-medium"


def grade_badge(grade: Any) -> str:
    grade_text = html_escape(grade)
    return f'<span class="ff-badge {grade_class(grade)}">Grade {grade_text}</span>'


def risk_badge(label: Any) -> str:
    label_text = html_escape(label)
    return f'<span class="ff-badge {risk_class(label)}">{label_text}</span>'


def metric_card(label: str, value: str, context: str = "") -> str:
    context_html = f'<div class="ff-muted">{html_escape(context)}</div>' if context else ""
    return (
        '<div class="ff-metric-card">'
        f'<div class="ff-mini-label">{html_escape(label)}</div>'
        f'<div class="ff-value">{html_escape(value)}</div>'
        f"{context_html}"
        "</div>"
    )


def info_card(label: str, value: Any, context: str = "") -> str:
    context_html = f'<div class="ff-muted">{html_escape(context)}</div>' if context else ""
    return (
        '<div class="ff-card">'
        f'<div class="ff-mini-label">{html_escape(label)}</div>'
        f'<div class="ff-small-value">{html_escape(value)}</div>'
        f"{context_html}"
        "</div>"
    )


def source_status_card(label: str, connected: Any) -> str:
    is_connected = bool(connected)
    status = "Connected" if is_connected else "Missing"
    status_class = "ff-status-connected" if is_connected else "ff-status-missing"
    dot_class = "ff-dot-connected" if is_connected else "ff-dot-missing"
    return (
        f'<div class="ff-status-card {status_class}">'
        f'<div class="ff-mini-label">{html_escape(label)}</div>'
        '<div class="ff-small-value">'
        f'<span class="ff-status-dot {dot_class}"></span>{status}'
        "</div>"
        '<div class="ff-muted">Used in runtime score calculation</div>'
        "</div>"
    )


def driver_card(driver: dict[str, Any], kind: str) -> str:
    css_class = "ff-driver-positive" if kind == "positive" else "ff-driver-risk"
    dim_key = driver.get("dimension", "")
    label = DIMENSION_LABELS.get(dim_key, str(dim_key).replace("_", " ").title())
    sub_score = format_score(driver.get("sub_score"))
    text = driver.get("text", "")
    return (
        f'<div class="{css_class}">'
        f'<div class="ff-mini-label">{html_escape(label)} - {sub_score}/100</div>'
        f'<div>{html_escape(text)}</div>'
        "</div>"
    )


def risk_profile_text(row: pd.Series) -> str:
    grade = str(row.get("grade", ""))
    risk = str(row.get("risk_label", ""))
    profiles = {
        "A": "Strong profile with high data confidence and lender-ready fundamentals.",
        "B": "Finance-ready profile with a small number of operating watch points.",
        "C": "Reviewable profile; lender should inspect cost, cash-flow, and volatility drivers.",
        "D": "High-risk profile with meaningful repayment and operating pressure.",
        "E": "Very high-risk profile; not suitable for fast-track credit review.",
    }
    return profiles.get(grade, risk or "Review profile and supporting data.")


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
    source_cols = st.columns(3)
    source_data = [
        ("Bank", row["bank_present"]),
        ("POS", row["pos_present"]),
        ("Accounting", row["accounting_present"]),
    ]
    for col, (label, connected) in zip(source_cols, source_data):
        col.markdown(source_status_card(label, connected), unsafe_allow_html=True)


def subscore_frame(row: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Dimension": DIMENSION_LABELS[dim_key],
                "Weight": WEIGHTS[dim_key],
                "Score": float(row[score_col]),
                "Weighted points": float(row[score_col]) * WEIGHTS[dim_key],
            }
            for dim_key, score_col in SCORE_DIMENSIONS
        ]
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


def score_column_config() -> dict[str, Any] | None:
    if not hasattr(st, "column_config"):
        return None
    return {
        "Weight": st.column_config.NumberColumn("Weight", format="%.1f%%"),
        "Score": st.column_config.NumberColumn("Score", format="%.1f"),
        "Weighted points": st.column_config.NumberColumn("Weighted points", format="%.1f"),
    }


def dashboard_column_config() -> dict[str, Any] | None:
    if not hasattr(st, "column_config"):
        return None
    return {
        "Requested loan": st.column_config.NumberColumn("Requested loan", format="EUR %.0f"),
        "Score": st.column_config.NumberColumn("Score", format="%.1f"),
        "Peer percentile": st.column_config.NumberColumn("Peer percentile", format="%.0f%%"),
        "Prime cost ratio": st.column_config.NumberColumn("Prime cost ratio", format="%.1f%%"),
        "Rent-to-revenue": st.column_config.NumberColumn("Rent-to-revenue", format="%.1f%%"),
        "Cash-flow margin": st.column_config.NumberColumn("Cash-flow margin", format="%.1f%%"),
        "Revenue CV": st.column_config.NumberColumn("Revenue CV", format="%.1f%%"),
        "Data completeness": st.column_config.NumberColumn("Data completeness", format="%.0f%%"),
    }


def render_metric_grid(cards: list[tuple[str, str, str]], columns: int = 4) -> None:
    for start in range(0, len(cards), columns):
        cols = st.columns(columns)
        for col, (label, value, context) in zip(cols, cards[start : start + columns]):
            col.markdown(metric_card(label, value, context), unsafe_allow_html=True)


def render_home_page(data: dict[str, Any]) -> None:
    scored = data["scored"]

    st.title("ForkFund")
    st.markdown(
        """
        <div class="ff-hero">
            <div class="ff-mini-label">FinTech MVP</div>
            <div class="ff-value">Restaurant Credit Passport and lender dashboard</div>
            <div class="ff-muted">
                ForkFund turns synthetic restaurant identity, bank, POS, and accounting
                data into a runtime credit view for Dutch restaurant financing.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    flow_steps = [
        ("1", "Restaurant profile", "Synthetic KvK-style business identity and loan request."),
        ("2", "Data connected", "Bank, POS, and accounting summaries are loaded from CSV."),
        ("3", "Runtime score", "The approved rules-based scoring engine calculates grades."),
        ("4", "Credit Passport", "Lenders see score, drivers, trends, and source coverage."),
        ("5", "Lender dashboard", "Restaurants can be filtered and opened for review."),
    ]
    st.markdown("### MVP flow")
    flow_cols = st.columns(5)
    for col, (number, title, description) in zip(flow_cols, flow_steps):
        col.markdown(
            (
                '<div class="ff-flow-step">'
                f'<div class="ff-mini-label">Step {number}</div>'
                f'<div class="ff-small-value">{html_escape(title)}</div>'
                f'<div class="ff-muted">{html_escape(description)}</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    st.markdown("### Demo restaurants")
    demo_rows = scored[scored["legal_name"].isin(DEMO_RESTAURANTS)].copy()
    demo_rows["demo_order"] = demo_rows["legal_name"].apply(DEMO_RESTAURANTS.index)
    demo_rows = demo_rows.sort_values("demo_order")

    demo_cols = st.columns(3)
    for col, (_, row) in zip(demo_cols, demo_rows.iterrows()):
        with col:
            st.markdown(
                (
                    '<div class="ff-card">'
                    f'<div class="ff-mini-label">{html_escape(row["city"])}</div>'
                    f'<div class="ff-value">{html_escape(row["legal_name"])}</div>'
                    f'{grade_badge(row["grade"])}{risk_badge(row["risk_label"])}'
                    f'<div class="ff-muted" style="margin-top:0.65rem;">'
                    f'Score {format_score(row["total_score"])} / 100 | '
                    f'{html_escape(row["revenue_band"])}'
                    "</div>"
                    f'<div class="ff-muted" style="margin-top:0.45rem;">'
                    f'{html_escape(risk_profile_text(row))}'
                    "</div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
            if st.button("Select profile", key=f"home_select_{int(row['restaurant_id'])}"):
                set_selected_restaurant(int(row["restaurant_id"]))
                st.success(f"{row['legal_name']} selected for the Credit Passport.")

    st.markdown(
        """
        <div class="ff-section-note">
            All records are synthetic. Scores, grades, drivers, and peer percentiles
            are computed in memory at runtime and are not stored in the raw CSV files.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_restaurant_onboarding_page(data: dict[str, Any]) -> None:
    scored = data["scored"]
    current_id = selected_restaurant_id(scored)
    options = restaurant_options(scored)
    index = options.index(current_id) if current_id in options else 0

    st.title("Restaurant Onboarding")
    st.write("Select a synthetic restaurant profile to simulate the borrower onboarding step.")

    restaurant_id = st.selectbox(
        "Restaurant profile",
        options,
        index=index,
        format_func=lambda rid: restaurant_label(scored, rid),
    )
    set_selected_restaurant(restaurant_id)
    row = row_for(scored, restaurant_id)

    panel_cols = st.columns(2)
    with panel_cols[0]:
        st.markdown("### Business identity")
        identity_cards = [
            ("Legal name", str(row["legal_name"]), f"KvK {int(row['kvk_number']):08d}"),
            ("City", str(row["city"]), str(row["legal_form"])),
            ("Cuisine", str(row["cuisine_type"]), f"{int(row['seats'])} seats"),
            ("Registration date", str(row["registration_date"]), f"{row['years_active']:.1f} years active"),
        ]
        render_metric_grid(identity_cards, columns=2)

    with panel_cols[1]:
        st.markdown("### Financing request")
        request_cards = [
            ("Requested loan", format_eur(row["requested_loan_amount"]), str(row["loan_purpose"])),
            ("Revenue band", str(row["revenue_band"]), format_eur(row["annual_revenue"], 0)),
            ("Current grade", f"{row['grade']}", f"Score {format_score(row['total_score'])}"),
            ("Risk label", str(row["risk_label"]), risk_profile_text(row)),
        ]
        render_metric_grid(request_cards, columns=2)

    st.markdown("### Mock data connections")
    display_source_status(row)

    st.markdown(
        (
            '<div class="ff-section-note">'
            f'{html_escape(row["legal_name"])} is selected. Open the Credit Passport page '
            "to review the runtime score, lender metrics, and score drivers."
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_credit_passport_page(data: dict[str, Any]) -> None:
    raw = data["raw"]
    metrics = data["metrics"]
    scored = data["scored"]
    options = restaurant_options(scored)
    current_id = selected_restaurant_id(scored)
    index = options.index(current_id) if current_id in options else 0

    st.title("Credit Passport")

    restaurant_id = st.selectbox(
        "Passport restaurant",
        options,
        index=index,
        format_func=lambda rid: restaurant_label(scored, rid),
    )
    set_selected_restaurant(restaurant_id)

    scored_row = row_for(scored, restaurant_id)
    metrics_row = metrics.loc[metrics["restaurant_id"] == restaurant_id].iloc[0]

    header_cols = st.columns([2.2, 1])
    with header_cols[0]:
        st.markdown(
            (
                '<div class="ff-hero">'
                f'<div class="ff-mini-label">{html_escape(scored_row["city"])} | '
                f'{html_escape(scored_row["revenue_band"])}</div>'
                f'<div class="ff-value">{html_escape(scored_row["legal_name"])}</div>'
                f'{grade_badge(scored_row["grade"])}{risk_badge(scored_row["risk_label"])}'
                f'<div class="ff-muted" style="margin-top:0.65rem;">'
                f'{html_escape(scored_row["loan_purpose"])} request of '
                f'{format_eur(scored_row["requested_loan_amount"])} | '
                f'Peer percentile {format_pct(scored_row["peer_percentile"], 0, already_percent=True)}'
                "</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
    with header_cols[1]:
        st.markdown(
            metric_card(
                "ForkFund score",
                f"{format_score(scored_row['total_score'])}/100",
                "Computed at runtime from connected CSV data",
            ),
            unsafe_allow_html=True,
        )

    overview_tab, drivers_tab, trends_tab, details_tab = st.tabs(
        ["Overview", "Score drivers", "Trends", "Details"]
    )

    with overview_tab:
        st.markdown("### Lender-first snapshot")
        overview_cards = [
            ("Loan request", format_eur(scored_row["requested_loan_amount"]), str(scored_row["loan_purpose"])),
            ("Annual revenue", format_eur(scored_row["annual_revenue"]), str(scored_row["revenue_band"])),
            ("DSCR proxy", format_score(scored_row["dscr_proxy"], 2), "Debt service coverage indicator"),
            ("Cash-flow margin", format_pct(scored_row["cash_flow_margin"]), "Bank inflows minus outflows"),
            ("Prime cost ratio", format_pct(scored_row["prime_cost_ratio"]), "Food plus labour over revenue"),
            ("Rent-to-revenue", format_pct(scored_row["rent_to_revenue"]), "Occupancy pressure"),
            ("Revenue CV", format_pct(scored_row["revenue_cv"]), "Monthly revenue volatility"),
            (
                "Data completeness",
                format_pct(scored_row["data_completeness"], 0, already_percent=True),
                "Bank, POS, accounting coverage",
            ),
        ]
        render_metric_grid(overview_cards, columns=4)

        st.markdown("### Data-source status")
        display_source_status(scored_row)

    with drivers_tab:
        pop_context = build_pop_context(metrics)
        breakdown = score_restaurant(metrics_row, pop_context)
        driver_result = generate_score_drivers(metrics_row, breakdown)

        positive_col, risk_col = st.columns(2)
        with positive_col:
            st.markdown("### Top positive drivers")
            if driver_result["top_positive"]:
                for driver in driver_result["top_positive"]:
                    st.markdown(driver_card(driver, "positive"), unsafe_allow_html=True)
            else:
                st.info("No positive drivers are available for this profile.")

        with risk_col:
            st.markdown("### Top risk drivers")
            if driver_result["top_risk"]:
                for driver in driver_result["top_risk"]:
                    st.markdown(driver_card(driver, "risk"), unsafe_allow_html=True)
            else:
                st.info("No risk drivers are available for this profile.")

        st.markdown("### Nine scoring dimensions")
        subscores = subscore_frame(scored_row)
        chart_df = subscores.set_index("Dimension")[["Score"]]
        st.bar_chart(chart_df)
        table_df = subscores.copy()
        table_df["Weight"] = table_df["Weight"] * 100
        st.dataframe(
            table_df,
            hide_index=True,
            use_container_width=True,
            column_config=score_column_config(),
        )

    with trends_tab:
        chart_cols = st.columns(2)
        with chart_cols[0]:
            st.markdown("### Monthly revenue")
            pos_months = monthly_pos_for(raw, restaurant_id)
            revenue_chart = pos_months.set_index("period")[["total_revenue"]]
            st.line_chart(revenue_chart)

        with chart_cols[1]:
            st.markdown("### Bank inflows versus outflows")
            bank_months = monthly_bank_for(raw, restaurant_id)
            bank_chart = bank_months.set_index("period")[["total_inflows", "total_outflows"]]
            st.line_chart(bank_chart)

    with details_tab:
        st.markdown("### Business identity")
        detail_cols = st.columns(3)
        detail_cols[0].markdown(info_card("KvK number", f"{int(scored_row['kvk_number']):08d}"), unsafe_allow_html=True)
        detail_cols[1].markdown(info_card("Legal form", scored_row["legal_form"]), unsafe_allow_html=True)
        detail_cols[2].markdown(info_card("Cuisine", scored_row["cuisine_type"]), unsafe_allow_html=True)
        detail_cols[0].markdown(info_card("Seats", int(scored_row["seats"]), "Dining capacity"), unsafe_allow_html=True)
        detail_cols[1].markdown(info_card("Opening hours/day", format_score(scored_row["opening_hours_per_day"], 1)), unsafe_allow_html=True)
        detail_cols[2].markdown(info_card("Years active", format_score(scored_row["years_active"], 1)), unsafe_allow_html=True)

        st.markdown("### Source flags")
        display_source_status(scored_row)

        st.markdown("### Metric detail")
        metric_rows = [
            ("Requested loan", format_eur(scored_row["requested_loan_amount"])),
            ("Annual revenue", format_eur(scored_row["annual_revenue"])),
            ("Existing debt", format_eur(scored_row["existing_debt"])),
            ("Debt service estimate", format_eur(scored_row["debt_service_estimated"])),
            ("Debt-to-revenue", format_pct(scored_row["debt_to_revenue"])),
            ("DSCR proxy", format_score(scored_row["dscr_proxy"], 2)),
            ("Cash-flow margin", format_pct(scored_row["cash_flow_margin"])),
            ("Prime cost ratio", format_pct(scored_row["prime_cost_ratio"])),
            ("Rent-to-revenue", format_pct(scored_row["rent_to_revenue"])),
            ("EBITDA margin", format_pct(scored_row["ebitda_margin"])),
            ("Revenue CV", format_pct(scored_row["revenue_cv"])),
            ("Delivery share", format_pct(scored_row["delivery_share"])),
            ("Weekend share", format_pct(scored_row["weekend_share"])),
            ("Average check", format_eur(scored_row["average_check"], decimals=2)),
            ("Covers per seat/month", format_score(scored_row["covers_per_seat_month"])),
            ("RevPASH", format_eur(scored_row["revpash"], decimals=2)),
            ("Data completeness", format_pct(scored_row["data_completeness"], 0, already_percent=True)),
        ]
        st.dataframe(
            pd.DataFrame(metric_rows, columns=["Metric", "Value"]),
            hide_index=True,
            use_container_width=True,
        )

        st.markdown("### Detailed scoring breakdown")
        full_breakdown = subscore_frame(scored_row)
        full_breakdown["Weight"] = full_breakdown["Weight"] * 100
        st.dataframe(
            full_breakdown,
            hide_index=True,
            use_container_width=True,
            column_config=score_column_config(),
        )


def render_lender_dashboard_page(data: dict[str, Any]) -> None:
    scored = data["scored"].copy()

    st.title("Lender Dashboard")
    st.write("Filter the synthetic restaurant pool and open a selected Credit Passport.")

    summary_cards = [
        ("Restaurants", f"{len(scored)}", "Synthetic profiles in the pool"),
        ("Average score", format_score(scored["total_score"].mean()), "Runtime weighted score"),
        ("A/B profiles", str(int(scored["grade"].isin(["A", "B"]).sum())), "Lower-risk opportunities"),
        ("D/E profiles", str(int(scored["grade"].isin(["D", "E"]).sum())), "Higher-risk reviews"),
    ]
    render_metric_grid(summary_cards, columns=4)

    chart_cols = st.columns(2)
    with chart_cols[0]:
        st.markdown("### Grade distribution")
        grade_counts = scored["grade"].value_counts().reindex(GRADE_ORDER, fill_value=0)
        st.bar_chart(grade_counts)
    with chart_cols[1]:
        st.markdown("### Revenue band by grade")
        crosstab = pd.crosstab(scored["revenue_band"], scored["grade"]).reindex(
            columns=GRADE_ORDER, fill_value=0
        )
        st.dataframe(crosstab, use_container_width=True)

    with st.expander("Dashboard filters", expanded=True):
        filter_cols = st.columns(3)
        cities = filter_cols[0].multiselect(
            "City",
            sorted(scored["city"].unique()),
            default=sorted(scored["city"].unique()),
        )
        grades = filter_cols[1].multiselect(
            "Grade", GRADE_ORDER, default=GRADE_ORDER
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

    with st.expander("Optional operating-risk filters", expanded=False):
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
    percent_cols = [
        "Prime cost ratio",
        "Rent-to-revenue",
        "Cash-flow margin",
        "Revenue CV",
    ]
    for col in percent_cols:
        display_df[col] = display_df[col] * 100
    display_df["Score"] = display_df["Score"].round(1)
    display_df["Peer percentile"] = display_df["Peer percentile"].round(0)

    st.dataframe(
        display_df,
        hide_index=True,
        use_container_width=True,
        column_config=dashboard_column_config(),
    )

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
        selected_row = row_for(scored, int(open_id))

        st.markdown(
            (
                '<div class="ff-card">'
                f'<div class="ff-mini-label">Selected restaurant</div>'
                f'<div class="ff-value">{html_escape(selected_row["legal_name"])}</div>'
                f'{grade_badge(selected_row["grade"])}{risk_badge(selected_row["risk_label"])}'
                f'<div class="ff-muted" style="margin-top:0.65rem;">'
                f'{html_escape(selected_row["city"])} | '
                f'{html_escape(selected_row["revenue_band"])} | '
                f'{format_eur(selected_row["requested_loan_amount"])} request'
                "</div>"
                f'<div class="ff-muted" style="margin-top:0.45rem;">'
                f'Score {format_score(selected_row["total_score"])} / 100 | '
                f'Peer percentile {format_pct(selected_row["peer_percentile"], 0, already_percent=True)}'
                "</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        if st.button("Use this restaurant for the Credit Passport"):
            set_selected_restaurant(open_id)
            st.success("Restaurant selected. Open the Credit Passport page from the sidebar.")


def render_methodology_page() -> None:
    st.title("Methodology / About")

    st.markdown(
        """
        <div class="ff-section-note">
            ForkFund is a technical MVP for pre-underwriting decision support in
            restaurant finance. It uses synthetic CSV data and a transparent
            rules-based scoring engine. It is not predictive ML and it is not a
            final lending decision.
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Scoring dimensions", expanded=True):
        weights_df = pd.DataFrame(
            [
                {
                    "Dimension": DIMENSION_LABELS[key],
                    "Weight": weight * 100,
                }
                for key, weight in WEIGHTS.items()
            ]
        )
        st.dataframe(
            weights_df,
            hide_index=True,
            use_container_width=True,
            column_config={"Weight": st.column_config.NumberColumn("Weight", format="%.1f%%")}
            if hasattr(st, "column_config")
            else None,
        )

    with st.expander("Grade thresholds", expanded=False):
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

    with st.expander("MVP limitations", expanded=False):
        limitations = [
            "Uses synthetic CSV data rather than live PSD2, POS, or KvK integrations.",
            "Computes scores, grades, peer percentiles, and drivers at runtime.",
            "Does not persist derived scores or modify raw CSV files.",
            "Does not include authentication, lender offers, iDIN, BKR, or money movement.",
            "Does not use a predictive machine-learning default model.",
        ]
        for limitation in limitations:
            st.write(f"- {limitation}")


def main() -> None:
    inject_styles()
    data = load_app_data(DATA_DIR)

    st.sidebar.title("ForkFund")
    selected_page = st.sidebar.radio("Go to", PAGES)
    st.sidebar.caption(
        "Synthetic CSV backend. Scores and grades are computed at runtime."
    )

    if "selected_restaurant_id" in st.session_state:
        row = row_for(data["scored"], int(st.session_state["selected_restaurant_id"]))
        st.sidebar.markdown(
            (
                f"**Selected:** {html_escape(row['legal_name'])}  \n"
                f"Grade {html_escape(row['grade'])} | Score {format_score(row['total_score'])}"
            )
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
