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
    "How it works",
]

PAGES_RESTAURANT = [
    "My Dashboard",
    "My Credit Passport",
    "My Lender Offers",
]

PAGES_LENDER = [
    "Lender Dashboard",
    "How it works",
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

import time

# ── Demo credentials ──────────────────────────────────────────────────────────
DEMO_ACCOUNTS = {
    "restaurant@forkfund.io": {
        "password": "demo1234",
        "role": "restaurant",
        "display_name": "Trattoria Pietro",
        "restaurant_name": "Trattoria Pietro",
        "existing_requests": [
            {
                "id": 1,
                "loan_amount": 75000,
                "loan_purpose": "Renovation",
                "status": "Active",
                "n_offers": 2,
                "created_at": "2026-05-20",
                "restaurant_id": 41,
            }
        ],
    },
    "lender@forkfund.io": {
        "password": "demo1234",
        "role": "lender",
        "display_name": "ABN AMRO",
    },
}


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        /* ── Global font scale up ──────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"], .stApp {
            font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
            font-size: 17px !important;
        }
        p, li, div, span, label {
            font-size: 1rem !important;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.82rem !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.04em !important;
            color: #556480 !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
            font-weight: 700 !important;
            color: #0D1F3C !important;
        }
        h1 { font-size: 2.1rem !important; font-weight: 800 !important;
             color: #0D1F3C !important; letter-spacing: -0.02em !important; }
        h2 { font-size: 1.5rem !important; font-weight: 700 !important;
             color: #0D1F3C !important; }
        h3 { font-size: 1.2rem !important; font-weight: 700 !important;
             color: #0D1F3C !important; margin-top: 1.5rem !important; }
        .stRadio label, .stSelectbox label, .stTextInput label,
        .stNumberInput label, .stTextArea label, .stMultiSelect label,
        .stSlider label, .stToggle label {
            font-size: 0.95rem !important;
            font-weight: 600 !important;
            color: #0D1F3C !important;
        }
        [data-testid="stSidebar"] * { font-size: 0.95rem !important; }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2 {
            font-size: 1.2rem !important;
        }
        [data-testid="baseButton-secondary"] button,
        [data-testid="baseButton-primary"] button,
        button[kind="secondary"], button[kind="primary"] {
            font-size: 0.95rem !important;
        }
        /* Tabs */
        [data-testid="stTabs"] [data-baseweb="tab"] {
            font-size: 1rem !important;
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # Second style block: component classes
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
    lenders = pd.read_csv(f"{data_dir}/lenders.csv")
    return {"raw": raw_data, "metrics": metrics, "scored": scored, "lenders": lenders}


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
            scored.loc[scored["legal_name"] == "Trattoria Pietro", "restaurant_id"].iloc[0]
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




def render_login_page() -> None:
    """Full-page login / register screen."""
    _, centre, _ = st.columns([1, 1.6, 1])
    with centre:
        st.markdown(
            "<div style='text-align:center;padding:2.5rem 0 1.5rem 0;'>"
            "<div style='font-size:2rem;font-weight:800;color:#0D1F3C;"
            "letter-spacing:-0.02em;'>🍴 ForkFund</div>"
            "<div style='font-size:0.78rem;color:#556480;font-weight:600;"
            "text-transform:uppercase;letter-spacing:0.08em;margin-top:0.3rem;'>"
            "Credit Passport for Restaurants</div></div>",
            unsafe_allow_html=True,
        )

        sign_in_tab, register_tab = st.tabs(["Sign in", "Create account"])

        # ── SIGN IN ──────────────────────────────────────────────────────────
        with sign_in_tab:
            st.markdown(
                "<div style='background:#F2F5F9;border:1px solid #DDE4EE;"
                "border-left:4px solid #0B6B56;border-radius:8px;"
                "padding:0.75rem 1rem;margin-bottom:1.25rem;font-size:0.8rem;color:#0D1F3C;'>"
                "<strong>Demo accounts</strong><br>"
                "🍴 Restaurant &nbsp;→&nbsp;"
                "<code>restaurant@forkfund.io</code> / <code>demo1234</code><br>"
                "🏦 Lender &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→&nbsp;"
                "<code>lender@forkfund.io</code> / <code>demo1234</code>"
                "</div>",
                unsafe_allow_html=True,
            )
            email_in = st.text_input("Email address", placeholder="you@example.com",
                                     key="signin_email")
            pw_in    = st.text_input("Password", type="password",
                                     placeholder="••••••••", key="signin_pw")

            if st.button("Sign in", use_container_width=True, key="signin_btn"):
                email_key = email_in.strip().lower()
                account   = DEMO_ACCOUNTS.get(email_key)
                if account and pw_in == account["password"]:
                    # Quick signin spinner
                    with st.spinner("Signing you in…"):
                        time.sleep(1)
                    st.session_state["logged_in"]    = True
                    st.session_state["role"]          = account["role"]
                    st.session_state["display_name"]  = account["display_name"]
                    st.session_state["verified"]      = True
                    if account["role"] == "restaurant":
                        st.session_state["demo_restaurant_name"] = account["restaurant_name"]
                        st.session_state["onboarding_complete"]  = True
                        st.session_state["loan_requests"] = account.get("existing_requests", [])
                    st.rerun()
                else:
                    st.error("Email or password incorrect.")

        # ── REGISTER ─────────────────────────────────────────────────────────
        with register_tab:
            st.markdown(
                "<div style='color:#556480;font-size:0.85rem;margin-bottom:1rem;'>"
                "Create your ForkFund account.</div>",
                unsafe_allow_html=True,
            )

            # Check if we're on lender step 2
            if st.session_state.get("reg_lender_step2"):
                # ── LENDER STEP 2: Institution profile ────────────────────────
                st.markdown(
                    "<div style='background:#0D1F3C;border-radius:10px;"
                    "padding:1rem 1.2rem;margin-bottom:1rem;'>"
                    "<div style='font-size:0.68rem;font-weight:700;color:#7A93B4;"
                    "text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.3rem;'>"
                    "Step 2 of 2: Institution profile</div>"
                    "<div style='color:#FFFFFF;font-size:0.88rem;font-weight:600;'>"
                    "Required for DNB verification and platform access.</div>"
                    "</div>",
                    unsafe_allow_html=True,
                )

                col1, col2 = st.columns(2)
                dnb_number = col1.text_input(
                    "DNB registration number",
                    key="reg_dnb",
                    placeholder="e.g. R123456",
                )
                lender_type = col2.selectbox(
                    "Institution type",
                    ["Bank", "SME lender", "Equipment finance",
                     "Alternative lender", "Revenue-based finance"],
                    key="reg_lender_type",
                )

                col3, col4 = st.columns(2)
                min_loan = col3.number_input(
                    "Minimum loan ticket (EUR)",
                    min_value=10000, max_value=500000,
                    value=50000, step=5000, key="reg_min_loan",
                )
                max_loan = col4.number_input(
                    "Maximum loan ticket (EUR)",
                    min_value=50000, max_value=2000000,
                    value=500000, step=25000, key="reg_max_loan",
                )

                loan_products = st.multiselect(
                    "Loan products offered",
                    ["Working capital", "Equipment", "Renovation",
                     "Term loan", "Expansion", "Revenue-based finance"],
                    default=["Working capital", "Term loan"],
                    key="reg_products",
                )

                contact_role = st.text_input(
                    "Your role at the institution",
                    key="reg_contact_role",
                    placeholder="e.g. SME Lending Manager",
                )

                back_col, submit_col = st.columns([1, 2])
                if back_col.button("← Back", key="reg_lender_back"):
                    st.session_state["reg_lender_step2"] = False
                    st.rerun()

                if submit_col.button("Create account →",
                                     use_container_width=True, key="reg_lender_submit"):
                    errors = []
                    if not dnb_number.strip():
                        errors.append("Please enter your DNB registration number.")
                    if not contact_role.strip():
                        errors.append("Please enter your role at the institution.")
                    if errors:
                        for e in errors:
                            st.error(e)
                    else:
                        st.session_state["logged_in"]            = True
                        st.session_state["role"]                  = "lender"
                        st.session_state["verified"]              = False
                        st.session_state["onboarding_complete"]   = True
                        st.session_state["loan_requests"]         = []
                        st.session_state["lender_dnb"]            = dnb_number.strip()
                        st.session_state["lender_type"]           = lender_type
                        st.session_state["lender_min_loan"]       = min_loan
                        st.session_state["lender_max_loan"]       = max_loan
                        st.session_state["lender_products"]       = loan_products
                        st.session_state["reg_lender_step2"]      = False
                        st.session_state["showing_verification"]  = True
                        st.session_state["verification_type"]     = "lender"
                        st.rerun()

            else:
                # ── STEP 1 (both roles): Basic account details ─────────────────
                st.markdown(
                    "<div style='font-size:0.78rem;font-weight:700;color:#0D1F3C;"
                    "margin:0 0 0.5rem 0;'>I am a</div>",
                    unsafe_allow_html=True,
                )
                reg_role = st.radio(
                    "role_select",
                    ["🍴  Restaurant: I need financing",
                     "🏦  Lender: I provide financing"],
                    key="reg_role",
                    label_visibility="collapsed",
                )
                is_lender_reg = "Lender" in reg_role

                st.markdown("<div style='margin-top:0.75rem;'></div>",
                            unsafe_allow_html=True)

                reg_name = st.text_input(
                    "Institution name" if is_lender_reg else "Restaurant name",
                    key="reg_name",
                    placeholder="e.g. ABN AMRO" if is_lender_reg else "e.g. Trattoria Pietro",
                )
                reg_email = st.text_input("Email address", key="reg_email",
                                          placeholder="you@example.com")
                reg_pw    = st.text_input("Password", type="password",
                                          placeholder="Min. 6 characters", key="reg_pw")

                btn_label = "Continue →" if is_lender_reg else "Create account"
                if st.button(btn_label, use_container_width=True, key="reg_btn"):
                    errors = []
                    if not reg_name.strip():
                        errors.append("Please enter your name.")
                    if not reg_email.strip():
                        errors.append("Please enter your email.")
                    if len(reg_pw) < 6:
                        errors.append("Password must be at least 6 characters.")

                    if errors:
                        for e in errors:
                            st.error(e)
                    elif is_lender_reg:
                        # Go to lender step 2
                        st.session_state["display_name"]    = reg_name.strip()
                        st.session_state["reg_lender_step2"] = True
                        st.rerun()
                    else:
                        # Restaurant: go straight to wizard
                        st.session_state["logged_in"]           = True
                        st.session_state["role"]                 = "restaurant"
                        st.session_state["display_name"]         = reg_name.strip()
                        st.session_state["verified"]             = False
                        st.session_state["onboarding_complete"]  = False
                        st.session_state["loan_requests"]        = []
                        st.session_state["showing_verification"] = False
                        st.rerun()

        st.markdown(
            "<div style='text-align:center;color:#A0AEC0;font-size:0.72rem;"
            "margin-top:2rem;'>RSM FinTech MVP · 2026 · Synthetic data only</div>",
            unsafe_allow_html=True,
        )


def render_verification_screen(vtype: str) -> None:
    """Animated verification screen shown after registration."""
    _, centre, _ = st.columns([1, 2, 1])
    with centre:
        st.markdown(
            "<div style='text-align:center;padding:3rem 0 1rem 0;'>"
            "<div style='font-size:2rem;font-weight:800;color:#0D1F3C;'>"
            "🍴 ForkFund</div></div>",
            unsafe_allow_html=True,
        )

        if vtype == "restaurant_register":
            steps = [
                ("🔍", "Verifying KvK registration…",       1.2),
                ("🏦", "Checking PSD2 consent setup…",      1.2),
                ("📊", "Validating data source connections…", 1.2),
                ("✅", "Profile verified. Welcome to ForkFund!", 0.8),
            ]
        else:  # lender
            steps = [
                ("🔍", "Verifying institution credentials…",  1.2),
                ("📋", "Checking DNB regulatory register…",   1.2),
                ("🔐", "Setting up lender access permissions…", 1.2),
                ("✅", "Account approved. Welcome to ForkFund!", 0.8),
            ]

        placeholder = st.empty()
        for icon, msg, delay in steps:
            is_done = icon == "✅"
            color   = "#0B6B56" if is_done else "#0D1F3C"
            bg      = "#E6F4F1" if is_done else "#F2F5F9"
            border  = "#0B6B56" if is_done else "#DDE4EE"
            placeholder.markdown(
                f"<div style='background:{bg};border:1px solid {border};"
                f"border-radius:12px;padding:2rem;text-align:center;margin:1rem 0;'>"
                f"<div style='font-size:2.5rem;margin-bottom:0.75rem;'>{icon}</div>"
                f"<div style='font-size:1rem;font-weight:700;color:{color};'>{msg}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            time.sleep(delay)

        # Mark verified and move forward
        time.sleep(0.5)
        st.session_state["verified"] = True
        st.session_state["showing_verification"] = False
        # Restaurant goes to wizard; lender goes straight to dashboard
        if vtype == "lender":
            st.session_state["onboarding_complete"] = True
        st.rerun()


def render_restaurant_dashboard(data: dict) -> None:
    """Restaurant home dashboard: existing requests + new request button."""
    display_name  = st.session_state.get("display_name", "Your Restaurant")
    loan_requests = st.session_state.get("loan_requests", [])

    st.title("My ForkFund Dashboard")
    st.markdown(
        f"<div style='color:#556480;font-size:0.9rem;margin-bottom:1.5rem;'>"
        f"Welcome back, <strong style='color:#0D1F3C;'>{html_escape(display_name)}</strong>. "
        f"Here are your active loan requests and lender responses.</div>",
        unsafe_allow_html=True,
    )

    # Summary strip
    n_req    = len(loan_requests)
    n_offers = sum(r.get("n_offers", 0) for r in loan_requests)
    sum_cols = st.columns(3)
    sum_cols[0].markdown(
        metric_card("Active requests", str(n_req), "Loan applications in progress"),
        unsafe_allow_html=True,
    )
    sum_cols[1].markdown(
        metric_card("Lender responses", str(n_offers), "Across all your requests"),
        unsafe_allow_html=True,
    )
    sum_cols[2].markdown(
        metric_card("Profile status", "✅ Verified", "KvK · PSD2 · Data sources"),
        unsafe_allow_html=True,
    )

    st.markdown("### Your loan requests")

    if not loan_requests:
        st.markdown(
            "<div style='background:#F2F5F9;border:1px dashed #DDE4EE;"
            "border-radius:10px;padding:2rem;text-align:center;color:#556480;'>"
            "No loan requests yet. Create your first one below.</div>",
            unsafe_allow_html=True,
        )
    else:
        scored = data["scored"]
        for req in loan_requests:
            # Resolve restaurant_id for this request
            if req.get("restaurant_id"):
                rid = req["restaurant_id"]
            else:
                demo_name = st.session_state.get("demo_restaurant_name", "Trattoria Pietro")
                matches = scored[scored["legal_name"] == demo_name]
                rid = int(matches.iloc[0]["restaurant_id"]) if not matches.empty else int(scored.iloc[0]["restaurant_id"])
                req["restaurant_id"] = rid

            row = row_for(scored, rid)
            grade     = html_escape(row["grade"])
            grade_css = grade_class(row["grade"])
            score     = format_score(row["total_score"])
            n_off     = req.get("n_offers", 0)
            status_color = "#0B6B56" if req["status"] == "Active" else "#556480"

            st.markdown(
                f"<div style='background:#FFFFFF;border:1px solid #DDE4EE;"
                f"border-radius:10px;padding:1.1rem 1.3rem;margin-bottom:0.75rem;"
                f"box-shadow:0 1px 4px rgba(13,31,60,0.06);'>"
                f"<div style='display:flex;align-items:center;"
                f"justify-content:space-between;margin-bottom:0.5rem;'>"
                f"<div style='font-size:1rem;font-weight:700;color:#0D1F3C;'>"
                f"{html_escape(req['loan_purpose'])} · EUR {req['loan_amount']:,}</div>"
                f"<span style='background:#E6F4F1;color:{status_color};"
                f"border-radius:6px;padding:0.2rem 0.7rem;font-size:0.75rem;"
                f"font-weight:700;'>{html_escape(req['status'])}</span>"
                f"</div>"
                f"<div style='display:flex;gap:2rem;margin-bottom:0.6rem;'>"
                f"<div><span style='font-size:0.7rem;color:#556480;font-weight:700;"
                f"text-transform:uppercase;letter-spacing:0.05em;'>Grade</span>"
                f"<span class='ff-badge {grade_css}' style='margin-left:0.4rem;"
                f"font-size:0.75rem;'>{grade}</span></div>"
                f"<div style='font-size:0.82rem;color:#556480;'>Score "
                f"<strong style='color:#0D1F3C;'>{score}</strong></div>"
                f"<div style='font-size:0.82rem;color:#556480;'>"
                f"<strong style='color:#0B6B56;'>{n_off} lender response"
                f"{'s' if n_off != 1 else ''}</strong></div>"
                f"<div style='font-size:0.82rem;color:#556480;'>"
                f"Submitted {req['created_at']}</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

            btn_cols = st.columns([2, 1, 1])
            if btn_cols[1].button(
                "View passport",
                key=f"view_passport_{req['id']}",
                use_container_width=True,
            ):
                st.session_state["selected_restaurant_id"] = rid
                st.session_state["current_page"] = "My Credit Passport"
                st.rerun()
            if btn_cols[2].button(
                f"View {n_off} offers",
                key=f"view_offers_{req['id']}",
                use_container_width=True,
            ):
                st.session_state["selected_restaurant_id"] = rid
                st.session_state["current_page"] = "My Lender Offers"
                st.rerun()

    # New request button
    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="ff-gold-btn">', unsafe_allow_html=True)
    if st.button("+ New loan request", key="new_request_btn"):
        st.session_state["showing_wizard"] = True
        st.session_state["wizard_step"]    = 1
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)



def generate_lender_offers(scored_row, lenders):
    import random, datetime
    rng = random.Random(int(scored_row["restaurant_id"]) * 37)
    grade = scored_row["grade"]
    loan_req = float(scored_row["requested_loan_amount"])
    n_offers = {"A": 4, "B": 3, "C": 2, "D": 1, "E": 1}.get(grade, 2)
    rate_base = {
        "A": (4.5, 6.5), "B": (5.5, 8.0), "C": (7.0, 10.5),
        "D": (9.5, 13.0), "E": (12.0, 17.0)
    }.get(grade, (8.0, 12.0))
    eligible = lenders[
        (lenders["min_loan_amount"] <= loan_req) &
        (lenders["max_loan_amount"] >= loan_req * 0.6)
    ]
    if eligible.empty:
        eligible = lenders
    sample = eligible.sample(
        n=min(n_offers, len(eligible)),
        random_state=int(scored_row["restaurant_id"])
    )
    statuses = {
        "A": ["Offer submitted", "Offer submitted", "Interested", "Offer submitted"],
        "B": ["Offer submitted", "Interested", "Awaiting data"],
        "C": ["Interested", "Awaiting data"],
        "D": ["Conditional interest"],
        "E": ["Conditional interest"],
    }.get(grade, ["Interested"])
    offers = []
    today = datetime.date.today()
    for i, (_, lender) in enumerate(sample.iterrows()):
        rate_lo = round(rate_base[0] + rng.uniform(-0.5, 0.5), 2)
        rate_hi = round(rate_base[1] + rng.uniform(-0.5, 0.5), 2)
        offer_amt = round(
            min(loan_req * rng.uniform(0.85, 1.0), float(lender["max_loan_amount"])) / 1000
        ) * 1000
        status = statuses[i % len(statuses)]
        valid_days = rng.randint(14, 45)
        conditions = []
        if grade in ("C", "D", "E"):
            conditions.append("Subject to additional documentation")
        if grade in ("D", "E"):
            conditions.append("Requires personal guarantee")
        offers.append({
            "lender_name": lender["lender_name"],
            "status": status,
            "offer_amount": offer_amt,
            "rate_lo": rate_lo,
            "rate_hi": rate_hi,
            "valid_until": str(today + datetime.timedelta(days=valid_days)),
            "conditions": conditions,
        })
    return offers


def render_offer_card(offer):
    status = offer["status"]
    color_map = {
        "Offer submitted":      ("#0B6B56", "#E6F4F1"),
        "Interested":           ("#1565A8", "#E8F4FD"),
        "Awaiting data":        ("#C49A2E", "#FBF4E0"),
        "Conditional interest": ("#B45309", "#FEF3C7"),
    }
    fg, bg = color_map.get(status, ("#556480", "#F2F5F9"))
    conds_html = ""
    if offer["conditions"]:
        conds = " &nbsp;&middot;&nbsp; ".join(offer["conditions"])
        conds_html = (
            f"<div style='margin-top:0.5rem;font-size:0.75rem;color:#B45309;'>"
            f"&#9888; {conds}</div>"
        )
    return (
        f"<div style='background:#FFFFFF;border:1px solid #DDE4EE;border-radius:10px;"
        f"padding:1rem 1.2rem;margin-bottom:0.75rem;"
        f"box-shadow:0 1px 4px rgba(13,31,60,0.06);'>"
        f"<div style='display:flex;align-items:center;justify-content:space-between;"
        f"margin-bottom:0.6rem;'>"
        f"<div style='font-size:1rem;font-weight:700;color:#0D1F3C;'>"
        f"{html_escape(offer['lender_name'])}</div>"
        f"<span style='background:{bg};color:{fg};border:1px solid {fg}33;"
        f"border-radius:6px;padding:0.2rem 0.7rem;font-size:0.75rem;font-weight:700;'>"
        f"{html_escape(status)}</span>"
        f"</div>"
        f"<div style='display:flex;gap:2rem;'>"
        f"<div><div style='font-size:0.68rem;color:#556480;font-weight:700;"
        f"text-transform:uppercase;letter-spacing:0.05em;'>Indicative amount</div>"
        f"<div style='font-size:1.2rem;font-weight:800;color:#0D1F3C;'>"
        f"EUR {offer['offer_amount']:,.0f}</div></div>"
        f"<div><div style='font-size:0.68rem;color:#556480;font-weight:700;"
        f"text-transform:uppercase;letter-spacing:0.05em;'>Rate range</div>"
        f"<div style='font-size:1.2rem;font-weight:800;color:#0D1F3C;'>"
        f"{offer['rate_lo']}% - {offer['rate_hi']}%</div></div>"
        f"<div><div style='font-size:0.68rem;color:#556480;font-weight:700;"
        f"text-transform:uppercase;letter-spacing:0.05em;'>Valid until</div>"
        f"<div style='font-size:1.2rem;font-weight:800;color:#0D1F3C;'>"
        f"{offer['valid_until']}</div></div>"
        f"</div>"
        f"{conds_html}"
        f"</div>"
    )

def render_restaurant_onboarding_wizard(data: dict) -> None:
    """3-step wizard: used both for first onboarding and new loan requests."""
    step = st.session_state.get("wizard_step", 1)
    is_new_request = st.session_state.get("onboarding_complete", False)

    title = "New loan request" if is_new_request else "Set up your restaurant profile"

    # Progress bar
    st.markdown(
        f"<div style='margin-bottom:1.5rem;'>"
        f"<div style='display:flex;justify-content:space-between;"
        f"font-size:0.72rem;color:#556480;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem;'>"
        f"<span>{title}: Step {step} of 3</span>"
        f"<span>{'Restaurant details' if step==1 else 'Connect data' if step==2 else 'Passport ready'}</span>"
        f"</div>"
        f"<div style='background:#DDE4EE;border-radius:999px;height:6px;'>"
        f"<div style='background:linear-gradient(90deg,#0B6B56,#C49A2E);"
        f"border-radius:999px;height:6px;width:{33*step}%;'></div>"
        f"</div></div>",
        unsafe_allow_html=True,
    )

    # ── STEP 1 ────────────────────────────────────────────────────────────────
    if step == 1:
        st.markdown(
            "<div style='font-size:1.4rem;font-weight:800;color:#0D1F3C;"
            "margin-bottom:0.25rem;'>Tell us about your restaurant</div>"
            "<div style='color:#556480;font-size:0.88rem;margin-bottom:1.5rem;'>"
            "This helps us match you with the right lenders.</div>",
            unsafe_allow_html=True,
        )
        col1, col2 = st.columns(2)
        col1.text_input("Restaurant name", key="w_name",
                        value=st.session_state.get("w_name",
                              st.session_state.get("display_name", "")))
        cities = ["Amsterdam", "Rotterdam", "Utrecht",
                  "The Hague", "Eindhoven", "Groningen", "Other"]
        default_city = st.session_state.get("w_city_val", "Rotterdam")
        col2.selectbox("City", cities, key="w_city",
                       index=cities.index(default_city) if default_city in cities else 0)
        cuisines = ["French", "Italian", "Dutch", "Asian",
                    "Mediterranean", "American", "Other"]
        col1.selectbox("Cuisine type", cuisines, key="w_cuisine",
                       index=cuisines.index("Italian"))
        col2.number_input("Number of seats", min_value=10, max_value=500,
                          value=48, step=5, key="w_seats")
        col3, col4 = st.columns(2)
        col3.number_input("Loan amount needed (EUR)", min_value=25000,
                          max_value=500000, value=75000, step=5000, key="w_loan")
        purposes = ["Working capital", "Equipment", "Renovation",
                    "Term loan", "Expansion"]
        col4.selectbox("Loan purpose", purposes, key="w_purpose",
                       index=purposes.index("Renovation"))
        st.slider("Years in operation", 0, 20, 8, key="w_years")

        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
        if st.button("Continue →", key="wizard_s1"):
            if not st.session_state.get("w_name", "").strip():
                st.error("Please enter your restaurant name.")
            else:
                st.session_state["wizard_step"] = 2
                st.rerun()

    # ── STEP 2 ────────────────────────────────────────────────────────────────
    elif step == 2:
        st.markdown(
            "<div style='font-size:1.4rem;font-weight:800;color:#0D1F3C;"
            "margin-bottom:0.25rem;'>Connect your data sources</div>"
            "<div style='color:#556480;font-size:0.88rem;margin-bottom:1.5rem;'>"
            "More data = higher completeness score = more lender interest.</div>",
            unsafe_allow_html=True,
        )
        bank = st.toggle("🏦  Bank account (PSD2 open banking)", value=True, key="w_bank")
        pos  = st.toggle("💳  POS / payment terminal data",       value=True, key="w_pos")
        acct = st.toggle("📊  Accounting software (Exact, Twinfield…)", value=False, key="w_acct")

        n_conn = sum([bank, pos, acct])
        pct    = {0: 40, 1: 65, 2: 85, 3: 100}[n_conn]
        label  = ("Excellent: lender-ready" if pct == 100
                  else "Good: most lenders will accept" if pct >= 80
                  else "Acceptable: consider adding more" if pct >= 60
                  else "Low: add more data sources")

        st.markdown(
            f"<div style='margin-top:1.25rem;background:#0D1F3C;border-radius:10px;"
            f"padding:1rem 1.25rem;'>"
            f"<div style='font-size:0.68rem;font-weight:700;color:#7A93B4;"
            f"text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.4rem;'>"
            f"Data completeness score</div>"
            f"<div style='display:flex;align-items:center;gap:1rem;'>"
            f"<div style='font-size:2rem;font-weight:800;color:#FFFFFF;'>{pct}%</div>"
            f"<div><div style='background:#1A3560;border-radius:999px;"
            f"height:8px;width:200px;'>"
            f"<div style='background:linear-gradient(90deg,#0B6B56,#C49A2E);"
            f"border-radius:999px;height:8px;width:{pct}%;'></div></div>"
            f"<div style='font-size:0.75rem;color:#7A93B4;margin-top:0.3rem;'>"
            f"{label}</div></div></div></div>",
            unsafe_allow_html=True,
        )

        if not bank:
            st.warning("Bank data is the most important signal for lenders.")

        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
        back_col, next_col = st.columns([1, 3])
        if back_col.button("← Back", key="wizard_s2_back"):
            st.session_state["wizard_step"] = 1
            st.rerun()
        if next_col.button("Generate my Credit Passport →",
                           use_container_width=True, key="wizard_s2"):
            st.session_state["w_bank_connected"] = bank
            st.session_state["w_pos_connected"]  = pos
            st.session_state["w_acct_connected"] = acct
            # Trigger post-wizard verification
            st.session_state["wizard_step"]          = 3
            st.session_state["showing_verification"] = True
            st.session_state["verification_type"]    = "restaurant_wizard"
            st.rerun()

    # ── STEP 3: Passport reveal (after verification completes) ────────────────
    elif step == 3:
        scored = data["scored"]

        # Name-to-ID mapping for known demo restaurants
        KNOWN_DEMO_IDS = {"Trattoria Pietro": 41}

        entered_name = st.session_state.get("w_name", "").strip()
        demo_name    = st.session_state.get("demo_restaurant_name", "Trattoria Pietro")

        # Resolve restaurant ID: prefer exact name match, then known mapping, then grade C
        if entered_name in KNOWN_DEMO_IDS:
            restaurant_id = KNOWN_DEMO_IDS[entered_name]
        elif demo_name in KNOWN_DEMO_IDS:
            restaurant_id = KNOWN_DEMO_IDS[demo_name]
        else:
            matches = scored[scored["legal_name"] == (entered_name or demo_name)]
            if matches.empty:
                matches = scored[scored["grade"] == "C"]
            restaurant_id = int(matches.iloc[0]["restaurant_id"])

        scored_row = scored[scored["restaurant_id"] == restaurant_id].iloc[0]
        st.session_state["selected_restaurant_id"] = restaurant_id
        st.session_state["demo_restaurant_name"]   = "Trattoria Pietro"

        user_name = entered_name or st.session_state.get("display_name", "Trattoria Pietro")

        st.markdown(
            f"<div style='font-size:1.4rem;font-weight:800;color:#0D1F3C;"
            f"margin-bottom:0.25rem;'>Your Credit Passport is ready!</div>"
            f"<div style='color:#556480;font-size:0.88rem;margin-bottom:1.5rem;'>"
            f"Based on your connected data, here is your ForkFund profile.</div>",
            unsafe_allow_html=True,
        )

        grade     = html_escape(scored_row["grade"])
        grade_css = grade_class(scored_row["grade"])
        score     = format_score(scored_row["total_score"])
        rev       = format_eur(scored_row["annual_revenue"])
        peer      = format_pct(scored_row["peer_percentile"], 0, already_percent=True)
        risk_b    = risk_badge(scored_row["risk_label"])
        offers    = generate_lender_offers(scored_row, data["lenders"])
        loan_amt  = int(st.session_state.get("w_loan", 75000))
        purpose   = st.session_state.get("w_purpose", "Working capital")

        st.markdown(
            "<div style='background:#0D1F3C;border-radius:14px;padding:1.5rem 2rem;"
            "position:relative;overflow:hidden;margin-bottom:1rem;'>"
            "<div style='position:absolute;top:0;left:0;right:0;height:4px;"
            "background:linear-gradient(90deg,#0B6B56,#C49A2E);'></div>"
            "<div style='display:flex;align-items:center;justify-content:space-between;'>"
            "<div>"
            f"<div style='font-size:1.5rem;font-weight:800;color:#FFFFFF;'>"
            f"{html_escape(user_name)}</div>"
            "<div style='color:#7A93B4;font-size:0.82rem;margin:0.3rem 0 0.6rem 0;'>"
            "ForkFund Credit Passport</div>"
            f"<span class='ff-badge {grade_css}' style='font-size:0.8rem;"
            f"padding:0.25rem 0.8rem;'>Grade {grade}</span>"
            f"{risk_b}"
            "<div style='margin-top:1rem;display:flex;gap:2rem;'>"
            f"<div><div style='font-size:1.3rem;font-weight:800;color:#FFFFFF;'>{rev}</div>"
            "<div style='font-size:0.7rem;color:#7A93B4;text-transform:uppercase;"
            "letter-spacing:0.05em;'>Annual revenue</div></div>"
            f"<div><div style='font-size:1.3rem;font-weight:800;color:#FFFFFF;'>"
            f"Top {peer}</div>"
            "<div style='font-size:0.7rem;color:#7A93B4;text-transform:uppercase;"
            "letter-spacing:0.05em;'>Peer percentile</div></div>"
            f"<div><div style='font-size:1.3rem;font-weight:800;color:#C49A2E;'>"
            f"{len(offers)} offers</div>"
            "<div style='font-size:0.7rem;color:#7A93B4;text-transform:uppercase;"
            "letter-spacing:0.05em;'>Lenders responded</div></div>"
            "</div></div>"
            f"<div style='text-align:center;'>"
            f"<div style='width:90px;height:90px;border-radius:50%;background:#0B6B56;"
            "display:flex;align-items:center;justify-content:center;"
            "box-shadow:0 0 0 4px rgba(11,107,86,0.3);margin:0 auto 0.4rem auto;'>"
            f"<div style='font-size:1.8rem;font-weight:800;color:#FFFFFF;'>{grade}</div>"
            "</div>"
            f"<div style='color:#FFFFFF;font-weight:700;font-size:1.1rem;'>{score}/100</div>"
            "</div>"
            "</div></div>",
            unsafe_allow_html=True,
        )

        if st.button("Go to my dashboard →", use_container_width=True,
                     key="wizard_done_btn"):
            import datetime
            existing = st.session_state.get("loan_requests", [])
            new_id   = max((r["id"] for r in existing), default=0) + 1
            existing.append({
                "id": new_id,
                "loan_amount":   loan_amt,
                "loan_purpose":  purpose,
                "status":        "Active",
                "n_offers":      len(offers),
                "created_at":    str(datetime.date.today()),
                "restaurant_id": restaurant_id,
            })
            st.session_state["loan_requests"]      = existing
            st.session_state["onboarding_complete"] = True
            st.session_state["showing_wizard"]      = False
            st.session_state["wizard_step"]         = 1
            st.rerun()



def render_restaurant_passport_page(data):
    scored = data["scored"]
    restaurant_id = selected_restaurant_id(scored)
    scored_row = row_for(scored, restaurant_id)
    metrics = data["metrics"]
    metrics_row = metrics.loc[metrics["restaurant_id"] == restaurant_id].iloc[0]
    offers = generate_lender_offers(scored_row, data["lenders"])

    grade     = html_escape(scored_row["grade"])
    grade_css = grade_class(scored_row["grade"])
    score     = format_score(scored_row["total_score"])
    rev       = format_eur(scored_row["annual_revenue"])
    dscr      = format_score(scored_row["dscr_proxy"], 2)
    cv_pct    = format_pct(scored_row["revenue_cv"])
    compl     = format_pct(scored_row["data_completeness"], 0, already_percent=True)
    prof_text = html_escape(risk_profile_text(scored_row))
    loan_req  = format_eur(scored_row["requested_loan_amount"])
    loan_purp = html_escape(scored_row["loan_purpose"])
    peer      = format_pct(scored_row["peer_percentile"], 0, already_percent=True)
    name      = html_escape(scored_row["legal_name"])
    city      = html_escape(scored_row["city"])
    kvk       = int(scored_row["kvk_number"])
    yrs       = scored_row["years_active"]
    risk_b    = risk_badge(scored_row["risk_label"])
    n_off     = len(offers)

    html = (
        "<div style='background:#0D1F3C;border-radius:14px;padding:2rem 2.25rem;"
        "margin-bottom:1.5rem;position:relative;overflow:hidden;'>"
        "<div style='position:absolute;top:0;left:0;right:0;height:4px;"
        "background:linear-gradient(90deg,#0B6B56,#C49A2E);'></div>"
        "<div style='font-size:0.68rem;font-weight:700;letter-spacing:0.1em;"
        "text-transform:uppercase;color:#7A93B4;margin-bottom:0.6rem;'>"
        "My Credit Passport</div>"
        "<div style='display:flex;align-items:flex-start;gap:2rem;'>"
        "<div style='flex:1;'>"
        f"<div style='font-size:1.9rem;font-weight:800;color:#FFFFFF;"
        f"letter-spacing:-0.02em;line-height:1.15;margin-bottom:0.5rem;'>"
        f"{name} <span style='color:#7A93B4;font-weight:400;'>·</span> "
        f"<span style='color:#A8B8D0;font-size:1.4rem;font-weight:600;'>{city}</span></div>"
        f"<div style='font-size:0.82rem;color:#7A93B4;margin-bottom:1rem;'>"
        f"KvK {kvk:08d} &nbsp;&middot;&nbsp; {yrs:.1f} yrs operating &nbsp;&middot;&nbsp; PSD2 verified</div>"
        f"<div style='margin-bottom:1.25rem;'>"
        f"<span class='ff-badge {grade_css}' style='font-size:0.8rem;padding:0.25rem 0.8rem;'>Grade {grade}</span>"
        f"{risk_b}</div>"
        "<div style='display:flex;gap:2.5rem;'>"
        f"<div><div style='font-size:1.6rem;font-weight:800;color:#FFFFFF;letter-spacing:-0.02em;'>{rev}</div>"
        "<div style='font-size:0.72rem;color:#7A93B4;font-weight:600;"
        "text-transform:uppercase;letter-spacing:0.05em;'>Annual revenue</div></div>"
        f"<div><div style='font-size:1.6rem;font-weight:800;color:#FFFFFF;letter-spacing:-0.02em;'>{cv_pct}</div>"
        "<div style='font-size:0.72rem;color:#7A93B4;font-weight:600;"
        "text-transform:uppercase;letter-spacing:0.05em;'>Revenue volatility</div></div>"
        f"<div><div style='font-size:1.6rem;font-weight:800;color:#FFFFFF;letter-spacing:-0.02em;'>{dscr}&times;</div>"
        "<div style='font-size:0.72rem;color:#7A93B4;font-weight:600;"
        "text-transform:uppercase;letter-spacing:0.05em;'>DSCR proxy</div></div>"
        f"<div><div style='font-size:1.6rem;font-weight:800;color:#FFFFFF;letter-spacing:-0.02em;'>{compl}</div>"
        "<div style='font-size:0.72rem;color:#7A93B4;font-weight:600;"
        "text-transform:uppercase;letter-spacing:0.05em;'>Data completeness</div></div>"
        "</div></div>"
        "<div style='text-align:center;min-width:140px;'>"
        f"<div style='width:110px;height:110px;border-radius:50%;background:#0B6B56;"
        "display:flex;flex-direction:column;align-items:center;justify-content:center;"
        "margin:0 auto 0.6rem auto;box-shadow:0 0 0 4px rgba(11,107,86,0.3);'>"
        f"<div style='font-size:2.2rem;font-weight:800;color:#FFFFFF;line-height:1;'>{grade}</div></div>"
        "<div style='color:#A8B8D0;font-size:0.78rem;'>ForkFund Score</div>"
        f"<div style='color:#FFFFFF;font-size:1.3rem;font-weight:800;'>{score} "
        "<span style='color:#7A93B4;font-size:0.9rem;'>/100</span></div>"
        f"<div style='color:#7A93B4;font-size:0.72rem;margin-top:0.3rem;'>Peer top {peer}</div>"
        "</div></div>"
        "<div style='margin-top:1.5rem;padding-top:1rem;border-top:1px solid #1A3560;'>"
        f"<div style='color:#7A93B4;font-size:0.82rem;'>{loan_purp} request of "
        f"<strong style='color:#FFFFFF;'>{loan_req}</strong> &nbsp;&middot;&nbsp; {prof_text}</div>"
        "</div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)

    btn_cols = st.columns([3, 1])
    with btn_cols[1]:
        st.markdown('<div class="ff-gold-btn">', unsafe_allow_html=True)
        if st.button(
            f"View my {n_off} lender offers",
            key="restaurant_view_offers_btn",
            use_container_width=True,
        ):
            st.session_state["current_page"] = "My Lender Offers"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    pop_context = build_pop_context(metrics)
    breakdown = score_restaurant(metrics_row, pop_context)
    driver_result = generate_score_drivers(metrics_row, breakdown)

    st.markdown("### What is helping your score")
    if driver_result["top_positive"]:
        for driver in driver_result["top_positive"][:3]:
            st.markdown(driver_card(driver, "positive"), unsafe_allow_html=True)

    st.markdown("### What to improve")
    if driver_result["top_risk"]:
        for driver in driver_result["top_risk"][:3]:
            st.markdown(driver_card(driver, "risk"), unsafe_allow_html=True)


def render_my_offers_page(data):
    import random
    scored      = data["scored"]
    restaurant_id = selected_restaurant_id(scored)
    scored_row  = row_for(scored, restaurant_id)
    rid_key     = int(restaurant_id)

    live_offers      = st.session_state.get("live_offers", {}).get(rid_key, [])
    synthetic_offers = generate_lender_offers(scored_row, data["lenders"])

    # Enrich synthetic offers with loan type + auto-message
    loan_types = ["Term loan", "Working capital", "Renovation loan",
                  "Equipment finance", "Revenue-based finance"]
    auto_messages = [
        "We reviewed your profile and would like to discuss a financing arrangement.",
        "Your revenue stability and data quality stand out. We'd welcome a call.",
        "Based on your Credit Passport, we see potential for a renovation loan.",
        "We would like to learn more about your business before making a firm offer.",
        "Your profile meets our lending criteria. Please reach out to discuss next steps.",
    ]
    rng = random.Random(rid_key)
    for i, o in enumerate(synthetic_offers):
        if "loan_type" not in o:
            o["loan_type"] = rng.choice(loan_types)
        if "note" not in o:
            o["note"] = auto_messages[i % len(auto_messages)]
        if "term" not in o:
            o["term"] = rng.choice(["12 months", "24 months", "36 months"])

    all_offers = live_offers + synthetic_offers
    n          = len(all_offers)
    n_live     = len(live_offers)

    # Restaurant responses stored in session state
    responses = st.session_state.get(f"offer_responses_{rid_key}", {})

    st.title("My Lender Offers")

    if n_live > 0:
        st.markdown(
            f"<div style='background:#E6F4F1;border:1px solid #0B6B56;"
            f"border-left:4px solid #0B6B56;border-radius:8px;"
            f"padding:0.75rem 1rem;margin-bottom:1rem;font-size:0.9rem;color:#0D1F3C;'>"
            f"🔔 <strong>{n_live} new offer{'s' if n_live>1 else ''}</strong> "
            f"received since your last visit!</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div style='color:#556480;font-size:0.95rem;margin-bottom:1.5rem;'>"
        f"Offers for <strong style='color:#0D1F3C;'>{html_escape(scored_row['legal_name'])}"
        f"</strong> &nbsp;·&nbsp; Grade {html_escape(scored_row['grade'])}"
        f" &nbsp;·&nbsp; {n} lender{'s' if n!=1 else ''} responded</div>",
        unsafe_allow_html=True,
    )

    # Summary metrics
    submitted  = sum(1 for o in all_offers if o.get("status") == "Offer submitted")
    interested = sum(1 for o in all_offers if o.get("status") == "Interested")
    rates      = [(o["rate_lo"] + o["rate_hi"]) / 2
                  for o in all_offers if "rate_lo" in o and "rate_hi" in o]
    avg_rate   = sum(rates) / len(rates) if rates else 0

    s_cols = st.columns(3)
    s_cols[0].markdown(metric_card("Offers submitted", str(submitted), "Ready to review"), unsafe_allow_html=True)
    s_cols[1].markdown(metric_card("Lenders interested", str(interested), "Reviewing your profile"), unsafe_allow_html=True)
    s_cols[2].markdown(metric_card("Avg. rate", f"{avg_rate:.1f}%", "Across all responses"), unsafe_allow_html=True)

    st.markdown("### Lender responses")

    for i, offer in enumerate(all_offers):
        is_live    = offer.get("is_live", False)
        lname      = html_escape(offer["lender_name"])
        status     = offer.get("status", "Interested")
        ltype      = html_escape(offer.get("lender_type") or offer.get("loan_type", ""))
        note       = offer.get("note", "")
        valid      = offer.get("valid_until", "")
        term       = html_escape(offer.get("term", ""))
        loan_type  = html_escape(offer.get("loan_type", ""))
        amount     = offer.get("offer_amount") or offer.get("offer_amount", 0)
        rate_lo    = offer.get("rate_lo", 0)
        rate_hi    = offer.get("rate_hi", 0)
        conditions = offer.get("conditions", [])
        response   = responses.get(i)

        # Status badge colours
        status_colors = {
            "Offer submitted":     ("#0B6B56", "#E6F4F1"),
            "Interested":          ("#1565A8", "#E8F4FD"),
            "Awaiting data":       ("#C49A2E", "#FBF4E0"),
            "Conditional interest": ("#B45309", "#FEF3C7"),
        }
        sfg, sbg = status_colors.get(status, ("#556480", "#F2F5F9"))

        # Response badge
        resp_html = ""
        if response == "interested":
            resp_html = ("<span style='background:#E6F4F1;color:#0B6B56;border:1px solid #0B6B56;"
                        "border-radius:6px;padding:0.2rem 0.7rem;font-size:0.78rem;font-weight:700;'>"
                        "✅ You expressed interest</span>")
        elif response == "declined":
            resp_html = ("<span style='background:#FDECEB;color:#C0392B;border:1px solid #C0392B;"
                        "border-radius:6px;padding:0.2rem 0.7rem;font-size:0.78rem;font-weight:700;'>"
                        "✗ Not a fit</span>")

        conditions_html = ""
        if conditions:
            conds = " &nbsp;·&nbsp; ".join(conditions)
            conditions_html = (f"<div style='margin-top:0.5rem;font-size:0.82rem;color:#B45309;'>"
                               f"&#9888; {conds}</div>")

        note_html = ""
        if note:
            note_html = (f"<div style='margin-top:0.75rem;padding:0.65rem 0.9rem;"
                         f"background:#F2F5F9;border-radius:8px;border-left:3px solid #DDE4EE;"
                         f"font-size:0.88rem;color:#0D1F3C;font-style:italic;'>"
                         f"💬 &nbsp;{html_escape(note)}</div>")

        rate_str = (f"{rate_lo}%" if rate_lo == rate_hi
                    else f"{rate_lo}% – {rate_hi}%")
        border = "2px solid #0B6B56" if is_live else "1px solid #DDE4EE"
        shadow = "0 2px 8px rgba(11,107,86,0.12)" if is_live else "0 1px 4px rgba(13,31,60,0.06)"

        new_badge = ("<span style='background:#FFE066;color:#0D1F3C;border-radius:6px;"
                     "padding:0.15rem 0.6rem;font-size:0.72rem;font-weight:800;'>"
                     "🔴 NEW</span> " if is_live else "")

        st.markdown(
            f"<div style='background:#FFFFFF;border:{border};border-radius:10px;"
            f"padding:1.1rem 1.3rem;margin-bottom:1rem;box-shadow:{shadow};'>"
            # Header row: name + badges
            f"<div style='display:flex;align-items:center;justify-content:space-between;"
            f"margin-bottom:0.75rem;'>"
            f"<div>"
            f"<span style='font-size:1.05rem;font-weight:700;color:#0D1F3C;'>{lname}</span>"
            f"{'<span style=\"font-size:0.82rem;color:#556480;\"> &nbsp;·&nbsp; ' + ltype + '</span>' if ltype else ''}"
            f"</div>"
            f"<div style='display:flex;gap:0.5rem;align-items:center;'>"
            f"{new_badge}"
            f"<span style='background:{sbg};color:{sfg};border:1px solid {sfg}33;"
            f"border-radius:6px;padding:0.2rem 0.7rem;font-size:0.78rem;font-weight:700;'>"
            f"{html_escape(status)}</span>"
            f"{resp_html}"
            f"</div></div>"
            # Key terms
            f"<div style='display:flex;gap:2.5rem;flex-wrap:wrap;margin-bottom:0.5rem;'>"
            f"<div><div style='font-size:0.7rem;color:#556480;font-weight:700;"
            f"text-transform:uppercase;letter-spacing:0.05em;'>Amount</div>"
            f"<div style='font-size:1.15rem;font-weight:800;color:#0D1F3C;'>"
            f"EUR {amount:,}</div></div>"
            f"<div><div style='font-size:0.7rem;color:#556480;font-weight:700;"
            f"text-transform:uppercase;letter-spacing:0.05em;'>Rate</div>"
            f"<div style='font-size:1.15rem;font-weight:800;color:#0D1F3C;'>{rate_str}</div></div>"
            f"<div><div style='font-size:0.7rem;color:#556480;font-weight:700;"
            f"text-transform:uppercase;letter-spacing:0.05em;'>Term</div>"
            f"<div style='font-size:1.15rem;font-weight:800;color:#0D1F3C;'>{term}</div></div>"
            f"<div><div style='font-size:0.7rem;color:#556480;font-weight:700;"
            f"text-transform:uppercase;letter-spacing:0.05em;'>Loan type</div>"
            f"<div style='font-size:1.15rem;font-weight:800;color:#0D1F3C;'>{loan_type}</div></div>"
            f"<div><div style='font-size:0.7rem;color:#556480;font-weight:700;"
            f"text-transform:uppercase;letter-spacing:0.05em;'>Valid until</div>"
            f"<div style='font-size:1.15rem;font-weight:800;color:#0D1F3C;'>{valid}</div></div>"
            f"</div>"
            f"{conditions_html}"
            f"{note_html}"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Response buttons: only show if not yet responded
        if response is None:
            r_col1, r_col2, _ = st.columns([1.5, 1.5, 4])
            if r_col1.button("✅ I'm interested", key=f"offer_yes_{i}",
                             use_container_width=True):
                responses[i] = "interested"
                st.session_state[f"offer_responses_{rid_key}"] = responses
                st.success(f"Your interest in {offer['lender_name']}'s offer has been noted. "
                           f"They will contact you at your registered email.")
                st.rerun()
            if r_col2.button("✗ Not a fit", key=f"offer_no_{i}",
                             use_container_width=True):
                responses[i] = "declined"
                st.session_state[f"offer_responses_{rid_key}"] = responses
                st.rerun()
        else:
            st.markdown("<div style='margin-bottom:0.5rem;'></div>",
                        unsafe_allow_html=True)

    st.markdown(
        '<div class="ff-section-note">Live offers are submitted in real time by lenders '
        "on the platform. Background offers are indicative and generated from synthetic "
        "lender data to illustrate the marketplace. Responding here notifies the lender "
        "via your registered email in the live product.</div>",
        unsafe_allow_html=True,
    )


def render_home_page(data: dict[str, Any]) -> None:
    scored = data["scored"]

    st.title("Restaurant Credit Intelligence")
    st.markdown(
        """
        <div class="ff-hero">
            <div class="ff-mini-label">ForkFund &nbsp;·&nbsp; RSM FinTech MVP &nbsp;·&nbsp; Netherlands 2026</div>
            <div class="ff-value">The credit passport for restaurant finance.</div>
            <div class="ff-muted" style="margin-top:0.5rem; max-width:640px;">
                ForkFund aggregates bank, POS, and accounting data into a standardised,
                lender-ready Credit Passport, connecting finance-ready Dutch restaurants
                with professional lenders.
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


def render_submit_offer_page(data: dict) -> None:
    """Dedicated full-page offer submission form for lenders."""
    import datetime
    scored = data["scored"]
    restaurant_id = selected_restaurant_id(scored)
    scored_row = row_for(scored, restaurant_id)
    rid_key = int(restaurant_id)

    # Back button
    if st.button("← Back to Credit Passport", key="offer_page_back"):
        st.session_state["current_page"] = "Credit Passport"
        st.session_state["show_offer_form"] = False
        st.rerun()

    st.title("Submit a Financing Offer")
    st.markdown(
        f"<div style='color:#556480;font-size:1rem;margin-bottom:1.5rem;'>"
        f"Submitting offer to <strong style='color:#0D1F3C;'>"
        f"{html_escape(scored_row['legal_name'])}</strong>"
        f" &nbsp;·&nbsp; {html_escape(scored_row['city'])}"
        f" &nbsp;·&nbsp; Grade {html_escape(scored_row['grade'])}"
        f" &nbsp;·&nbsp; Score {format_score(scored_row['total_score'])}/100"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Restaurant request summary
    st.markdown(
        f"<div style='background:#F2F5F9;border:1px solid #DDE4EE;"
        f"border-radius:10px;padding:1rem 1.2rem;margin-bottom:1.5rem;'>"
        f"<div style='font-size:0.75rem;font-weight:700;color:#556480;"
        f"text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem;'>"
        f"Restaurant request</div>"
        f"<div style='font-size:1rem;color:#0D1F3C;'>"
        f"{html_escape(scored_row['loan_purpose'])} &nbsp;·&nbsp; "
        f"<strong>{format_eur(scored_row['requested_loan_amount'])}</strong>"
        f" requested</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.markdown("### Your offer terms")

    col1, col2, col3 = st.columns(3)
    offer_amount = col1.number_input(
        "Offer amount (EUR)",
        min_value=10000, max_value=1000000,
        value=int(scored_row["requested_loan_amount"]),
        step=5000, key="offer_amount_input",
    )
    offer_rate = col2.number_input(
        "Indicative interest rate (%)",
        min_value=1.0, max_value=25.0,
        value=7.5, step=0.25, key="offer_rate_input",
    )
    offer_validity = col3.number_input(
        "Offer valid for (days)",
        min_value=7, max_value=90,
        value=30, step=7, key="offer_validity_input",
    )

    col4, col5 = st.columns(2)
    offer_term = col4.selectbox(
        "Loan term",
        ["12 months", "24 months", "36 months", "48 months", "60 months"],
        index=1, key="offer_term_input",
    )
    offer_type = col5.selectbox(
        "Loan type",
        ["Term loan", "Working capital", "Equipment finance",
         "Renovation loan", "Revenue-based finance"],
        key="offer_type_input",
    )

    offer_conditions = st.multiselect(
        "Conditions (optional)",
        ["Subject to site visit", "Requires personal guarantee",
         "Additional P&L documentation needed",
         "Subject to final credit approval",
         "Business plan required"],
        key="offer_conditions_input",
    )

    offer_note = st.text_area(
        "Message to restaurant (optional)",
        placeholder="e.g. We'd like to schedule a call to discuss your renovation plans.",
        key="offer_note_input", height=100,
    )

    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    cancel_col, submit_col = st.columns([1, 2])

    if cancel_col.button("Cancel", key="offer_page_cancel"):
        st.session_state["current_page"] = "Credit Passport"
        st.session_state["show_offer_form"] = False
        st.rerun()

    if submit_col.button(
        "Submit offer →", key="offer_page_submit", use_container_width=True
    ):
        lender_name = st.session_state.get("display_name", "Lender")
        lender_type = st.session_state.get("lender_type", "")
        valid_until = str(
            datetime.date.today() + datetime.timedelta(days=int(offer_validity))
        )
        new_offer = {
            "lender_name": lender_name,
            "lender_type": lender_type,
            "status": "Offer submitted",
            "offer_amount": int(offer_amount),
            "rate_lo": float(offer_rate),
            "rate_hi": float(offer_rate),
            "term": offer_term,
            "loan_type": offer_type,
            "conditions": offer_conditions,
            "note": offer_note.strip(),
            "valid_until": valid_until,
            "is_live": True,
        }
        live = st.session_state.get("live_offers", {})
        existing = live.get(rid_key, [])
        existing = [o for o in existing if o["lender_name"] != lender_name]
        existing.insert(0, new_offer)
        live[rid_key] = existing
        st.session_state["live_offers"] = live
        st.session_state[f"offer_just_submitted_{rid_key}"] = new_offer
        st.session_state["show_offer_form"] = False
        st.session_state["current_page"] = "Credit Passport"
        st.rerun()


def render_credit_passport_page(data: dict[str, Any]) -> None:
    raw = data["raw"]
    metrics = data["metrics"]
    scored = data["scored"]
    options = restaurant_options(scored)
    current_id = selected_restaurant_id(scored)
    index = options.index(current_id) if current_id in options else 0

    st.title("Credit Passport")
    # Scroll to top when navigating here
    st.components.v1.html(
        "<script>window.parent.document.querySelector('section.main').scrollTo(0,0);</script>",
        height=0,
    )

    restaurant_id = st.selectbox(
        "Passport restaurant",
        options,
        index=index,
        format_func=lambda rid: restaurant_label(scored, rid),
    )
    set_selected_restaurant(restaurant_id)

    scored_row = row_for(scored, restaurant_id)
    metrics_row = metrics.loc[metrics["restaurant_id"] == restaurant_id].iloc[0]

    # Credit Passport hero card (slide-5 style)
    grade     = html_escape(scored_row["grade"])
    grade_css = grade_class(scored_row["grade"])
    score     = format_score(scored_row["total_score"])
    rev       = format_eur(scored_row["annual_revenue"])
    dscr      = format_score(scored_row["dscr_proxy"], 2)
    cv_pct    = format_pct(scored_row["revenue_cv"])
    compl     = format_pct(scored_row["data_completeness"], 0, already_percent=True)
    prof_text = html_escape(risk_profile_text(scored_row))
    loan_req  = format_eur(scored_row["requested_loan_amount"])
    loan_purp = html_escape(scored_row["loan_purpose"])
    peer      = format_pct(scored_row["peer_percentile"], 0, already_percent=True)
    name      = html_escape(scored_row["legal_name"])
    city      = html_escape(scored_row["city"])
    kvk       = int(scored_row["kvk_number"])
    yrs       = scored_row["years_active"]
    risk_b    = risk_badge(scored_row["risk_label"])

    passport_html = (
        "<div style='background:#0D1F3C;border-radius:14px;padding:2rem 2.25rem;"
        "margin-bottom:1.5rem;position:relative;overflow:hidden;'>"
        "<div style='position:absolute;top:0;left:0;right:0;height:4px;"
        "background:linear-gradient(90deg,#0B6B56,#C49A2E);'></div>"
        "<div style='font-size:0.68rem;font-weight:700;letter-spacing:0.1em;"
        "text-transform:uppercase;color:#7A93B4;margin-bottom:0.6rem;'>"
        "Restaurant Credit Passport</div>"
        "<div style='display:flex;align-items:flex-start;gap:2rem;'>"
        "<div style='flex:1;'>"
        f"<div style='font-size:1.9rem;font-weight:800;color:#FFFFFF;"
        f"letter-spacing:-0.02em;line-height:1.15;margin-bottom:0.5rem;'>"
        f"{name} <span style='color:#7A93B4;font-weight:400;'>·</span> "
        f"<span style='color:#A8B8D0;font-size:1.4rem;font-weight:600;'>{city}</span></div>"
        f"<div style='font-size:0.82rem;color:#7A93B4;margin-bottom:1rem;'>"
        f"KvK {kvk:08d} &nbsp;&middot;&nbsp; {yrs:.1f} yrs operating &nbsp;&middot;&nbsp; PSD2 verified</div>"
        f"<div style='margin-bottom:1.25rem;'>"
        f"<span class='ff-badge {grade_css}' style='font-size:0.8rem;padding:0.25rem 0.8rem;'>Grade {grade}</span>"
        f"{risk_b}</div>"
        "<div style='display:flex;gap:2.5rem;'>"
        f"<div><div style='font-size:1.6rem;font-weight:800;color:#FFFFFF;letter-spacing:-0.02em;'>{rev}</div>"
        "<div style='font-size:0.72rem;color:#7A93B4;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;'>Annual revenue</div></div>"
        f"<div><div style='font-size:1.6rem;font-weight:800;color:#FFFFFF;letter-spacing:-0.02em;'>{cv_pct}</div>"
        "<div style='font-size:0.72rem;color:#7A93B4;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;'>Revenue volatility</div></div>"
        f"<div><div style='font-size:1.6rem;font-weight:800;color:#FFFFFF;letter-spacing:-0.02em;'>{dscr}&times;</div>"
        "<div style='font-size:0.72rem;color:#7A93B4;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;'>DSCR proxy</div></div>"
        f"<div><div style='font-size:1.6rem;font-weight:800;color:#FFFFFF;letter-spacing:-0.02em;'>{compl}</div>"
        "<div style='font-size:0.72rem;color:#7A93B4;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;'>Data completeness</div></div>"
        "</div></div>"
        f"<div style='text-align:center;min-width:140px;'>"
        f"<div style='width:110px;height:110px;border-radius:50%;background:#0B6B56;"
        f"display:flex;flex-direction:column;align-items:center;justify-content:center;"
        f"margin:0 auto 0.6rem auto;box-shadow:0 0 0 4px rgba(11,107,86,0.3);'>"
        f"<div style='font-size:2.2rem;font-weight:800;color:#FFFFFF;line-height:1;'>{grade}</div></div>"
        f"<div style='color:#A8B8D0;font-size:0.78rem;'>ForkFund Score</div>"
        f"<div style='color:#FFFFFF;font-size:1.3rem;font-weight:800;'>{score} "
        f"<span style='color:#7A93B4;font-size:0.9rem;'>/100</span></div>"
        f"<div style='color:#7A93B4;font-size:0.72rem;margin-top:0.3rem;'>Peer top {peer}</div>"
        "</div></div>"
        "<div style='margin-top:1.5rem;padding-top:1rem;border-top:1px solid #1A3560;"
        "display:flex;align-items:center;justify-content:space-between;'>"
        f"<div style='color:#7A93B4;font-size:0.82rem;'>{loan_purp} request of "
        f"<strong style='color:#FFFFFF;'>{loan_req}</strong> &nbsp;&middot;&nbsp; {prof_text}</div>"
        "</div></div>"
    )
    st.markdown(passport_html, unsafe_allow_html=True)

    # Gold button styled to match the navy card, sits just below the card bottom bar
    st.markdown(
        """
        <style>
        div[data-testid="stButton"][id="passport-lender-btn"] > button,
        #passport-lender-btn-wrap button {
            background-color: #C49A2E !important;
            color: #0D1F3C !important;
            font-weight: 700 !important;
            font-size: 0.85rem !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 0.5rem 1.25rem !important;
            margin-top: -0.5rem !important;
            float: right !important;
        }
        div[data-testid="stButton"][id="passport-lender-btn"] > button:hover,
        #passport-lender-btn-wrap button:hover {
            background-color: #B8891F !important;
            color: #0D1F3C !important;
        }
        </style>
        <div id="passport-lender-btn-wrap"></div>
        """,
        unsafe_allow_html=True,
    )

    btn_cols = st.columns([3, 1])
    with btn_cols[1]:
        role = st.session_state.get("role", "lender")
        if role == "lender":
            st.markdown('<div class="ff-gold-btn">', unsafe_allow_html=True)
            if st.button(
                "Submit an offer →",
                key="lender_submit_offer_btn",
                use_container_width=True,
            ):
                st.session_state["current_page"] = "Submit Offer"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            # Restaurant sees "View lender offers" button
            st.markdown('<div class="ff-gold-btn">', unsafe_allow_html=True)
            if st.button(
                "Lender offers available →",
                key="passport_to_lender_btn",
                use_container_width=True,
            ):
                st.session_state["lender_prefill_grade"] = scored_row["grade"]
                st.session_state["lender_prefill_id"] = int(restaurant_id)
                st.session_state["current_page"] = "Lender Dashboard"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # ── Success banner if offer was just submitted ────────────────────────────
    rid_key = int(restaurant_id)
    if st.session_state.get(f"offer_just_submitted_{rid_key}"):
        sub = st.session_state[f"offer_just_submitted_{rid_key}"]
        st.success(
            f"✅ Offer submitted to {html_escape(scored_row['legal_name'])}! "
            f"EUR {sub['offer_amount']:,} at {sub['rate_lo']}% for {sub['term']}. "
            f"The restaurant will see this in their Lender Offers page."
        )
        # Clear after showing once
        del st.session_state[f"offer_just_submitted_{rid_key}"]

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

    # Check if we arrived from the Credit Passport "View lender offers" button
    prefill_grade = st.session_state.pop("lender_prefill_grade", None)
    prefill_id    = st.session_state.pop("lender_prefill_id", None)

    if prefill_grade and prefill_id:
        prefill_name = row_for(scored, prefill_id)["legal_name"]
        st.markdown(
            f"""
            <div style='background:#0D1F3C;border-left:4px solid #C49A2E;border-radius:8px;
                        padding:0.9rem 1.1rem;margin-bottom:1rem;'>
                <div style='font-size:0.7rem;color:#7A93B4;font-weight:700;
                            text-transform:uppercase;letter-spacing:0.06em;'>
                    Arrived from Credit Passport
                </div>
                <div style='color:#FFFFFF;font-weight:700;font-size:1rem;margin-top:0.2rem;'>
                    {html_escape(prefill_name)}
                </div>
                <div style='color:#7A93B4;font-size:0.82rem;margin-top:0.2rem;'>
                    Dashboard pre-filtered to Grade {html_escape(prefill_grade)} matches
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        default_grades = [prefill_grade]
        default_id     = prefill_id
    else:
        default_grades = GRADE_ORDER
        default_id     = None

    st.write("Filter the restaurant pool and open a selected Credit Passport.")

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
            "Grade", GRADE_ORDER, default=default_grades
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

    if filtered.empty:
        st.warning("No restaurants match the selected filters.")
    else:
        st.markdown(
            "<div style='color:#556480;font-size:0.85rem;margin-bottom:0.5rem;'>"
            "Click a restaurant to open its Credit Passport.</div>",
            unsafe_allow_html=True,
        )

        # Column headers
        h1, h2, h3, h4 = st.columns([3, 1.5, 1.5, 1.5])
        for col, label in zip([h1, h2, h3, h4],
                               ["Restaurant", "City", "Grade", ""]):
            col.markdown(
                f"<div style='font-size:0.68rem;font-weight:700;color:#556480;"
                f"text-transform:uppercase;letter-spacing:0.06em;"
                f"padding-bottom:0.4rem;border-bottom:2px solid #DDE4EE;'>"
                f"{label}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-bottom:0.25rem;'></div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)

        for _, row in filtered.iterrows():
            rid       = int(row["restaurant_id"])
            grade_css = grade_class(row["grade"])
            grade     = html_escape(row["grade"])

            c_name, c_city, c_grade, c_btn = st.columns([3, 1.5, 1.5, 1.5])

            c_name.markdown(
                f"<div style='padding:0.6rem 0;font-size:0.95rem;font-weight:700;"
                f"color:#0D1F3C;'>{html_escape(row['legal_name'])}</div>",
                unsafe_allow_html=True,
            )
            c_city.markdown(
                f"<div style='padding:0.6rem 0;font-size:0.88rem;color:#556480;'>"
                f"{html_escape(row['city'])}</div>",
                unsafe_allow_html=True,
            )
            c_grade.markdown(
                f"<div style='padding:0.5rem 0;'>"
                f"<span class='ff-badge {grade_css}' style='font-size:0.78rem;'>"
                f"Grade {grade}</span></div>",
                unsafe_allow_html=True,
            )
            if c_btn.button("View passport →", key=f"lender_open_{rid}",
                            use_container_width=True):
                set_selected_restaurant(rid)
                st.session_state["current_page"] = "Credit Passport"
                st.session_state["show_offer_form"] = False
                st.rerun()

            st.markdown(
                "<hr style='margin:0;border:none;border-top:1px solid #EEF1F6;'>",
                unsafe_allow_html=True,
            )



def render_methodology_page() -> None:
    role = st.session_state.get("role", "lender")
    is_restaurant = role == "restaurant"

    st.title("How ForkFund Works")
    st.markdown(
        f"<div style='color:#556480;font-size:1rem;margin-bottom:1.5rem;'>"
        f"{'Understanding your Credit Passport score and what lenders see.' if is_restaurant else 'Understanding how restaurant scores are built and what they mean for underwriting.'}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # How the score is built
    with st.expander("How the ForkFund score is calculated", expanded=True):
        st.markdown(
            "<div style='color:#556480;font-size:0.9rem;margin-bottom:1rem;'>"
            "The ForkFund score is a rules-based, explainable score from 0 to 100. "
            "It is built from nine dimensions drawn from bank, POS, and accounting data. "
            "It is designed as a pre-underwriting support tool, not a final credit decision.</div>",
            unsafe_allow_html=True,
        )
        weights_df = pd.DataFrame(
            [
                {"Dimension": DIMENSION_LABELS[key], "Weight": f"{weight*100:.0f}%",
                 "What it measures": {
                     "data_completeness": "How many data sources are connected (bank, POS, accounting)",
                     "revenue_stability": "How stable monthly revenues are. Lower volatility scores higher.",
                     "cashflow_strength": "Cash-flow margin: bank inflows minus outflows over revenue",
                     "debt_burden": "Debt service coverage. Can the restaurant service its existing debt?",
                     "prime_cost": "Food plus labour cost as a share of revenue. A key restaurant metric.",
                     "rent_pressure": "Rent as a share of revenue. Occupancy cost pressure.",
                     "pos_demand": "POS sales quality: card/cash split and delivery platform dependency",
                     "seasonality": "Revenue concentration risk across months",
                     "business_maturity": "Years in operation. Longer track record scores higher.",
                 }.get(key, "")}
                for key, weight in WEIGHTS.items()
            ]
        )
        st.dataframe(weights_df, hide_index=True, use_container_width=True)

    # Grade thresholds
    with st.expander("Grade scale and risk bands", expanded=False):
        grade_df = pd.DataFrame(
            [
                ("A", "85 – 100", "Low risk", "Strong fundamentals across most dimensions"),
                ("B", "70 – 84", "Low-to-medium risk", "Solid profile with minor watch points"),
                ("C", "55 – 69", "Medium risk", "Reviewable profile; lender should inspect key drivers"),
                ("D", "40 – 54", "High risk", "Significant concerns. Additional documentation needed."),
                ("E", "0 – 39",  "Very high risk", "Material weaknesses across multiple dimensions"),
            ],
            columns=["Grade", "Score range", "Risk band", "Interpretation"],
        )
        st.dataframe(grade_df, hide_index=True, use_container_width=True)

    # What the score is NOT
    with st.expander("What the score is and what it is not", expanded=False):
        st.markdown(
            """
            **The ForkFund score is:**
            - A standardised, comparable pre-underwriting signal across all restaurants on the platform
            - Built from verified, consent-based financial data (bank, POS, accounting, KvK)
            - Explainable: every score has a written driver explanation
            - Useful for lender screening and restaurant financing readiness

            **The ForkFund score is NOT:**
            - A final credit decision. Lenders retain full underwriting responsibility.
            - A predictive machine-learning default model (no historical repayment data yet)
            - A guarantee of loan approval or specific interest rates
            - A replacement for lender due diligence, site visits, or legal review

            In this MVP, all restaurant data is synthetic and scores are computed at runtime for demonstration purposes.
            """,
            unsafe_allow_html=True if False else False,
        )

    if is_restaurant:
        with st.expander("How to improve your score", expanded=False):
            st.markdown(
                """
                **Connect more data sources:** each additional connection (bank, POS, accounting) raises your data completeness score directly.

                **Improve cash-flow margin:** reduce unnecessary outflows and maintain consistent bank inflows.

                **Manage debt burden:** a lower debt-service ratio signals stronger repayment capacity to lenders.

                **Reduce prime cost:** food and labour costs below 65% of revenue are viewed positively.

                **Operate longer:** business maturity improves automatically over time.

                **Reduce revenue volatility:** consistent monthly sales signal operational stability.
                """,
            )


def render_sidebar(data: dict, role: str) -> str:
    """Render branded sidebar and return selected page."""
    is_restaurant = role == "restaurant"
    display_name  = st.session_state.get("display_name", "")

    st.sidebar.markdown(
        f"""
        <div style="padding:0.25rem 0 1.25rem 0;border-bottom:1px solid #1A3560;
                    margin-bottom:1.25rem;">
            <div style="font-size:1.35rem;font-weight:800;color:#FFFFFF;
                        letter-spacing:-0.02em;">🍴 ForkFund</div>
            <div style="font-size:0.68rem;color:#7A93B4;font-weight:600;
                        letter-spacing:0.07em;text-transform:uppercase;
                        margin-top:0.2rem;">Credit Passport · Netherlands</div>
        </div>
        <div style="background:#1A3560;border-radius:8px;padding:0.65rem 0.9rem;
                    margin-bottom:1.25rem;border-left:3px solid
                    {'#0B6B56' if is_restaurant else '#C49A2E'};">
            <div style="font-size:0.65rem;color:#7A93B4;font-weight:700;
                        text-transform:uppercase;letter-spacing:0.06em;
                        margin-bottom:0.2rem;">
                Signed in as {'🍴 Restaurant' if is_restaurant else '🏦 Lender'}
            </div>
            <div style="color:#FFFFFF;font-weight:700;font-size:0.88rem;">
                {html_escape(display_name)}
            </div>
            {f"<div style='color:#7A93B4;font-size:0.75rem;margin-top:0.2rem;'>{html_escape(st.session_state.get('lender_type',''))} &nbsp;·&nbsp; DNB verified</div>" if not is_restaurant and st.session_state.get('lender_type') else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )

    page_list = PAGES_RESTAURANT if is_restaurant else PAGES_LENDER

    # current_page is the single source of truth for routing
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = page_list[0]
    # Ensure current_page is valid for this role
    valid_pages = page_list + [
        "Credit Passport", "My Lender Offers", "My Dashboard", "Submit Offer"
    ]
    if st.session_state["current_page"] not in valid_pages:
        st.session_state["current_page"] = page_list[0]

    sidebar_pick = st.sidebar.radio(
        "Navigate", page_list, label_visibility="collapsed",
        index=page_list.index(st.session_state["current_page"])
              if st.session_state["current_page"] in page_list else 0,
    )

    # Update current_page from sidebar only if user changed it
    if sidebar_pick != st.session_state.get("_last_sidebar_pick"):
        st.session_state["current_page"] = sidebar_pick
    st.session_state["_last_sidebar_pick"] = sidebar_pick

    selected = st.session_state["current_page"]

    # Active profile chip (lender view)
    if not is_restaurant and "selected_restaurant_id" in st.session_state:
        row = row_for(data["scored"], int(st.session_state["selected_restaurant_id"]))
        st.sidebar.markdown(
            f"<div style='background:#1A3560;border-radius:8px;padding:0.8rem 0.9rem;"
            f"margin-top:1rem;border-left:3px solid #0B6B56;'>"
            f"<div style='font-size:0.65rem;color:#7A93B4;font-weight:700;"
            f"text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.2rem;'>"
            f"Active Profile</div>"
            f"<div style='color:#FFFFFF;font-weight:700;font-size:0.88rem;'>"
            f"{html_escape(row['legal_name'])}</div>"
            f"<div style='color:#7A93B4;font-size:0.76rem;margin-top:0.2rem;'>"
            f"Grade {html_escape(row['grade'])} &nbsp;·&nbsp; "
            f"Score {format_score(row['total_score'])}</div></div>",
            unsafe_allow_html=True,
        )

    # Sign out
    st.sidebar.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)
    if st.sidebar.button("Sign out", key="signout_btn"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.sidebar.markdown(
        "<div style='font-size:0.68rem;color:#3A5070;margin-top:1rem;line-height:1.6;'>"
        "Synthetic data only<br>Scores computed at runtime<br>"
        "RSM FinTech MVP · 2026</div>",
        unsafe_allow_html=True,
    )
    return selected


def main() -> None:
    inject_styles()

    # ── 1. Auth gate ──────────────────────────────────────────────────────────
    if not st.session_state.get("logged_in"):
        render_login_page()
        return

    data          = load_app_data(DATA_DIR)
    role          = st.session_state.get("role", "lender")
    is_restaurant = role == "restaurant"

    # ── 2. Verification screen (register flow) ────────────────────────────────
    if st.session_state.get("showing_verification"):
        vtype = st.session_state.get("verification_type", "restaurant_register")
        render_verification_screen(vtype)
        return

    # ── 3. Restaurant wizard (first onboarding OR new loan request) ───────────
    if is_restaurant and (
        not st.session_state.get("onboarding_complete")
        or st.session_state.get("showing_wizard")
    ):
        render_restaurant_onboarding_wizard(data)
        return

    # ── 4. Sidebar + page routing ─────────────────────────────────────────────
    selected_page = render_sidebar(data, role)

    if selected_page == "My Dashboard":
        render_restaurant_dashboard(data)
    elif selected_page == "My Credit Passport":
        render_restaurant_passport_page(data)
    elif selected_page == "My Lender Offers":
        render_my_offers_page(data)
    elif selected_page == "Lender Dashboard":
        render_lender_dashboard_page(data)
    elif selected_page == "Credit Passport":
        render_credit_passport_page(data)
    elif selected_page == "Submit Offer":
        render_submit_offer_page(data)
    elif selected_page == "How it works":
        render_methodology_page()
    elif selected_page == "Home / Concept Overview":
        render_home_page(data)


if __name__ == "__main__":
    main()