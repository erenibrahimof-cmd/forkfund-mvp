"""
ForkFund data loader.

Public API
----------
load_raw_data(data_dir)          -> dict of five raw DataFrames
validate_raw_data(raw_data)      -> None  (raises ValueError on failure)
compute_restaurant_metrics(raw)  -> wide DataFrame, one row per restaurant
get_restaurant_profile(id, dir)  -> pd.Series for one restaurant
get_lender_dashboard_data(dir)   -> wide DataFrame for all restaurants
"""

import datetime
import os

import pandas as pd

# ── Constants ─────────────────────────────────────────────────────────────────

REFERENCE_DATE = datetime.date(2025, 12, 31)

_RESTAURANTS_COLS = {
    "restaurant_id", "kvk_number", "legal_name", "registration_date",
    "city", "legal_form", "sbi_code", "cuisine_type", "seats",
    "opening_hours_per_day", "requested_loan_amount", "loan_purpose",
    "annual_revenue_estimate", "demo_profile",
}

_MONTHLY_BANK_COLS = {
    "restaurant_id", "period", "month_number", "total_inflows",
    "total_outflows", "ending_balance", "debt_service_outflows",
    "cash_deposits", "card_deposits",
}

_MONTHLY_POS_COLS = {
    "restaurant_id", "period", "month_number", "total_revenue",
    "covers", "card_sales", "cash_sales", "delivery_platform_sales",
    "dine_in_sales", "weekend_revenue", "weekday_revenue",
}

_ACCOUNTING_COLS = {
    "restaurant_id", "year", "annual_revenue", "food_cost", "labour_cost",
    "rent_annual", "ebitda", "net_profit", "existing_debt",
    "debt_service_estimated",
}

_LENDERS_COLS = {
    "lender_id", "lender_name", "focus_city", "min_loan_amount",
    "max_loan_amount", "preferred_loan_purposes",
}

# ── Private helpers ────────────────────────────────────────────────────────────


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _check_columns(table_name: str, actual_cols: set, required_cols: set) -> None:
    missing = required_cols - actual_cols
    if missing:
        raise ValueError(
            f"{table_name}: missing required columns: {sorted(missing)}"
        )


def _years_active(registration_date) -> float:
    """
    Compute years active as of REFERENCE_DATE.

    Matches the generator convention exactly:
        max(0, (REFERENCE_DATE - registration_date).days / 365.25)
    capped at 10 (consistent with get_years_active() in generate_synthetic_data.py).

    Levant Express (registered 2025-01-10): raw ≈ 0.972, displays as 1.0 when
    rounded to one decimal place — matching the validation report.
    """
    if isinstance(registration_date, str):
        registration_date = datetime.date.fromisoformat(registration_date)
    days = (REFERENCE_DATE - registration_date).days
    years = max(0.0, days / 365.25)
    return min(years, 10.0)


def _revenue_band(annual_revenue_estimate: float) -> str:
    """Map annual_revenue_estimate to a revenue-band label."""
    if annual_revenue_estimate < 500_000:
        return "€150k–€500k"
    elif annual_revenue_estimate < 1_000_000:
        return "€500k–€1M"
    elif annual_revenue_estimate < 1_500_000:
        return "€1M–€1.5M"
    else:
        return "€1.5M+"


# ── Public API ────────────────────────────────────────────────────────────────


def load_raw_data(data_dir: str = "data") -> dict:
    """
    Read all five CSV files from data_dir.

    Returns a dict with keys:
        restaurants, monthly_bank, monthly_pos, accounting, lenders

    registration_date is parsed to Python date objects here so that
    all downstream code receives a consistent type.
    No values are derived; this function only reads and returns.
    """
    file_map = {
        "restaurants": "restaurants.csv",
        "monthly_bank": "monthly_bank.csv",
        "monthly_pos":  "monthly_pos.csv",
        "accounting":   "accounting.csv",
        "lenders":      "lenders.csv",
    }

    raw: dict = {}
    for key, filename in file_map.items():
        path = os.path.join(data_dir, filename)
        if not os.path.exists(path):
            raise ValueError(f"Required file not found: {path}")
        raw[key] = pd.read_csv(path)

    raw["restaurants"]["registration_date"] = (
        pd.to_datetime(raw["restaurants"]["registration_date"]).dt.date
    )

    return raw


def validate_raw_data(raw_data: dict) -> None:
    """
    Validate raw_data dict produced by load_raw_data.

    Raises ValueError with a descriptive message the moment any check fails.

    Checks performed
    ----------------
    1. Row counts (80 / 960 / 960 / 80 / 5–10)
    2. Required columns present in every table
    3. No duplicate primary keys
    4. Foreign-key consistency (all restaurant_ids reference restaurants.csv)
    5. Every restaurant has exactly 12 bank rows, 12 POS rows, 1 accounting row
    6. No zero-or-negative denominators required for derived metrics
    """
    rest = raw_data["restaurants"]
    bank = raw_data["monthly_bank"]
    pos  = raw_data["monthly_pos"]
    acct = raw_data["accounting"]
    lend = raw_data["lenders"]

    # ── 1. Row counts ──────────────────────────────────────────────────────
    _check(len(rest) == 80,
           f"restaurants.csv must have exactly 80 rows, got {len(rest)}")
    _check(len(bank) == 960,
           f"monthly_bank.csv must have exactly 960 rows, got {len(bank)}")
    _check(len(pos) == 960,
           f"monthly_pos.csv must have exactly 960 rows, got {len(pos)}")
    _check(len(acct) == 80,
           f"accounting.csv must have exactly 80 rows, got {len(acct)}")
    _check(5 <= len(lend) <= 10,
           f"lenders.csv must have 5–10 rows, got {len(lend)}")

    # ── 2. Required columns ────────────────────────────────────────────────
    _check_columns("restaurants",  set(rest.columns), _RESTAURANTS_COLS)
    _check_columns("monthly_bank", set(bank.columns), _MONTHLY_BANK_COLS)
    _check_columns("monthly_pos",  set(pos.columns),  _MONTHLY_POS_COLS)
    _check_columns("accounting",   set(acct.columns), _ACCOUNTING_COLS)
    _check_columns("lenders",      set(lend.columns), _LENDERS_COLS)

    # ── 3. Duplicate primary keys ──────────────────────────────────────────
    _check(rest["restaurant_id"].nunique() == len(rest),
           "restaurants.csv contains duplicate restaurant_id values")
    _check(bank.duplicated(["restaurant_id", "period"]).sum() == 0,
           "monthly_bank.csv contains duplicate (restaurant_id, period) keys")
    _check(pos.duplicated(["restaurant_id", "period"]).sum() == 0,
           "monthly_pos.csv contains duplicate (restaurant_id, period) keys")
    _check(acct.duplicated(["restaurant_id", "year"]).sum() == 0,
           "accounting.csv contains duplicate (restaurant_id, year) keys")
    _check(lend["lender_id"].nunique() == len(lend),
           "lenders.csv contains duplicate lender_id values")

    # ── 4. Foreign-key consistency ─────────────────────────────────────────
    valid_ids = set(rest["restaurant_id"])
    for table_name, df in [
        ("monthly_bank", bank),
        ("monthly_pos",  pos),
        ("accounting",   acct),
    ]:
        orphans = set(df["restaurant_id"]) - valid_ids
        _check(
            not orphans,
            f"{table_name}.csv contains restaurant_ids absent from "
            f"restaurants.csv: {sorted(orphans)}",
        )

    # ── 5. Per-restaurant row counts ───────────────────────────────────────
    bank_counts = bank.groupby("restaurant_id").size()
    wrong_bank  = bank_counts[bank_counts != 12]
    _check(len(wrong_bank) == 0,
           f"These restaurant_ids do not have exactly 12 bank rows: "
           f"{wrong_bank.to_dict()}")

    pos_counts = pos.groupby("restaurant_id").size()
    wrong_pos  = pos_counts[pos_counts != 12]
    _check(len(wrong_pos) == 0,
           f"These restaurant_ids do not have exactly 12 POS rows: "
           f"{wrong_pos.to_dict()}")

    acct_counts = acct.groupby("restaurant_id").size()
    wrong_acct  = acct_counts[acct_counts != 1]
    _check(len(wrong_acct) == 0,
           f"These restaurant_ids do not have exactly 1 accounting row: "
           f"{wrong_acct.to_dict()}")

    # ── 6. Zero-denominator guards ─────────────────────────────────────────
    bad_seats = rest.loc[rest["seats"] <= 0, "restaurant_id"].tolist()
    _check(not bad_seats,
           f"restaurants with seats <= 0: {bad_seats}")

    bad_hours = rest.loc[rest["opening_hours_per_day"] <= 0,
                         "restaurant_id"].tolist()
    _check(not bad_hours,
           f"restaurants with opening_hours_per_day <= 0: {bad_hours}")

    bad_revenue = acct.loc[acct["annual_revenue"] <= 0, "restaurant_id"].tolist()
    _check(not bad_revenue,
           f"restaurants with annual_revenue <= 0 in accounting.csv: {bad_revenue}")

    bad_pos_rev = (
        pos.loc[pos["total_revenue"] <= 0, ["restaurant_id", "period"]]
        .values.tolist()
    )
    _check(not bad_pos_rev,
           f"POS rows with total_revenue <= 0: {bad_pos_rev}")

    bad_covers = (
        pos.loc[pos["covers"] <= 0, ["restaurant_id", "period"]]
        .values.tolist()
    )
    _check(not bad_covers,
           f"POS rows with covers <= 0: {bad_covers}")

    bad_inflows = (
        bank.loc[bank["total_inflows"] <= 0, ["restaurant_id", "period"]]
        .values.tolist()
    )
    _check(not bad_inflows,
           f"Bank rows with total_inflows <= 0: {bad_inflows}")

    debt_no_service = acct.loc[
        (acct["existing_debt"] > 0) & (acct["debt_service_estimated"] <= 0),
        "restaurant_id",
    ].tolist()
    _check(not debt_no_service,
           f"restaurants with existing_debt > 0 but debt_service_estimated <= 0: "
           f"{debt_no_service}")


def compute_restaurant_metrics(raw_data: dict) -> pd.DataFrame:
    """
    Compute all derived per-restaurant metrics from validated raw_data.

    Returns a wide DataFrame with one row per restaurant containing:
    - all raw columns from restaurants.csv
    - all raw columns from accounting.csv
    - data-source presence flags: bank_present, pos_present, accounting_present
    - data_completeness (percentage, 0/33/67/100 for pre-loaded data always 100)
    - opening_hours_per_month (intermediate; exposed for downstream use)
    - derived metrics: years_active, revenue_band, average_check,
      delivery_share, weekend_share, prime_cost_ratio, rent_to_revenue,
      debt_to_revenue, ebitda_margin, dscr_proxy, revenue_cv,
      cash_flow_margin, covers_per_seat_month, revpash
    """
    rest = raw_data["restaurants"].copy()
    bank = raw_data["monthly_bank"]
    pos  = raw_data["monthly_pos"]
    acct = raw_data["accounting"]

    # ── Aggregate monthly POS to restaurant level ──────────────────────────
    pos_agg = (
        pos.groupby("restaurant_id")
        .agg(
            _pos_revenue_sum=("total_revenue", "sum"),
            _pos_covers_sum=("covers", "sum"),
            _pos_delivery_sum=("delivery_platform_sales", "sum"),
            _pos_weekend_sum=("weekend_revenue", "sum"),
            _pos_revenue_std=("total_revenue", lambda x: x.std(ddof=1)),
            _pos_revenue_mean=("total_revenue", "mean"),
        )
        .reset_index()
    )

    # ── Aggregate monthly bank to restaurant level ─────────────────────────
    bank_agg = (
        bank.groupby("restaurant_id")
        .agg(
            _bank_inflows_sum=("total_inflows", "sum"),
            _bank_outflows_sum=("total_outflows", "sum"),
        )
        .reset_index()
    )

    # ── Data-source presence flags ─────────────────────────────────────────
    bank_ids = set(bank["restaurant_id"])
    pos_ids  = set(pos["restaurant_id"])
    acct_ids = set(acct["restaurant_id"])

    rest["bank_present"]       = rest["restaurant_id"].isin(bank_ids)
    rest["pos_present"]        = rest["restaurant_id"].isin(pos_ids)
    rest["accounting_present"] = rest["restaurant_id"].isin(acct_ids)
    rest["data_completeness"]  = (
        rest["bank_present"].astype(int)
        + rest["pos_present"].astype(int)
        + rest["accounting_present"].astype(int)
    ) / 3 * 100

    # ── Merge into one wide DataFrame ─────────────────────────────────────
    df = rest.merge(acct, on="restaurant_id", how="left")
    df = df.merge(pos_agg,  on="restaurant_id", how="left")
    df = df.merge(bank_agg, on="restaurant_id", how="left")

    # ── Derived metrics ────────────────────────────────────────────────────

    # years_active: same convention as generator (max(0, days/365.25), cap 10)
    df["years_active"] = df["registration_date"].apply(_years_active)

    # revenue_band: derived from annual_revenue_estimate
    df["revenue_band"] = df["annual_revenue_estimate"].apply(_revenue_band)

    # opening_hours_per_month: 25 operating days per month
    df["opening_hours_per_month"] = df["opening_hours_per_day"] * 25

    # average_check: revenue-weighted across 12 months
    df["average_check"] = df["_pos_revenue_sum"] / df["_pos_covers_sum"]

    # delivery_share: annual aggregate ratio
    df["delivery_share"] = df["_pos_delivery_sum"] / df["_pos_revenue_sum"]

    # weekend_share: annual aggregate ratio
    df["weekend_share"] = df["_pos_weekend_sum"] / df["_pos_revenue_sum"]

    # prime_cost_ratio
    df["prime_cost_ratio"] = (
        (df["food_cost"] + df["labour_cost"]) / df["annual_revenue"]
    )

    # rent_to_revenue
    df["rent_to_revenue"] = df["rent_annual"] / df["annual_revenue"]

    # debt_to_revenue
    df["debt_to_revenue"] = df["existing_debt"] / df["annual_revenue"]

    # ebitda_margin
    df["ebitda_margin"] = df["ebitda"] / df["annual_revenue"]

    # dscr_proxy: 100 when existing_debt == 0; else ebitda / debt_service_estimated
    df["dscr_proxy"] = df.apply(
        lambda r: 100.0
        if r["existing_debt"] == 0
        else r["ebitda"] / r["debt_service_estimated"],
        axis=1,
    )

    # revenue_cv: sample coefficient of variation across 12 months of POS revenue
    df["revenue_cv"] = df["_pos_revenue_std"] / df["_pos_revenue_mean"]

    # cash_flow_margin: (inflows - outflows) / inflows, annual aggregate
    df["cash_flow_margin"] = (
        (df["_bank_inflows_sum"] - df["_bank_outflows_sum"])
        / df["_bank_inflows_sum"]
    )

    # covers_per_seat_month: average monthly covers per seat
    df["covers_per_seat_month"] = df["_pos_covers_sum"] / (12 * df["seats"])

    # revpash: revenue per available seat hour, annual average
    df["revpash"] = df["_pos_revenue_sum"] / (
        12 * df["seats"] * df["opening_hours_per_month"]
    )

    # Drop internal aggregation columns
    df = df.drop(columns=[c for c in df.columns if c.startswith("_")])

    return df


def get_restaurant_profile(
    restaurant_id: int, data_dir: str = "data"
) -> pd.Series:
    """
    Load, validate, and return computed metrics for a single restaurant.

    Raises ValueError if restaurant_id is not found.
    """
    raw = load_raw_data(data_dir)
    validate_raw_data(raw)
    metrics = compute_restaurant_metrics(raw)
    matches = metrics[metrics["restaurant_id"] == restaurant_id]
    if len(matches) == 0:
        raise ValueError(f"restaurant_id {restaurant_id} not found in data")
    return matches.iloc[0]


def get_lender_dashboard_data(data_dir: str = "data") -> pd.DataFrame:
    """
    Load, validate, and return computed metrics for all 80 restaurants.

    The lender dashboard applies pandas boolean indexing on the returned
    DataFrame to implement filters (city, grade, loan amount, etc.).
    """
    raw = load_raw_data(data_dir)
    validate_raw_data(raw)
    return compute_restaurant_metrics(raw)


# ── Smoke test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"

    print("=" * 60)
    print("ForkFund data-loader smoke test")
    print(f"data_dir = {os.path.abspath(data_dir)}")
    print("=" * 60)

    raw = load_raw_data(data_dir)
    print(f"\nload_raw_data: OK")
    print(f"  restaurants : {len(raw['restaurants'])} rows")
    print(f"  monthly_bank: {len(raw['monthly_bank'])} rows")
    print(f"  monthly_pos : {len(raw['monthly_pos'])} rows")
    print(f"  accounting  : {len(raw['accounting'])} rows")
    print(f"  lenders     : {len(raw['lenders'])} rows")

    validate_raw_data(raw)
    print("\nvalidate_raw_data: OK — all checks passed")

    metrics = compute_restaurant_metrics(raw)
    print(f"\ncompute_restaurant_metrics: OK")
    print(f"  Restaurants in output : {len(metrics)}")
    print(f"  Columns in output     : {len(metrics.columns)}")

    print("\n" + "-" * 60)
    print("Demo restaurant metrics")
    print("-" * 60)

    for rid in [1, 41, 15]:
        row = metrics[metrics["restaurant_id"] == rid].iloc[0]
        years_raw     = row["years_active"]
        years_display = round(years_raw, 1)
        print(f"\n── restaurant_id = {rid} ──────────────────────────────")
        print(f"  legal_name              : {row['legal_name']}")
        print(f"  revenue_band            : {row['revenue_band']}")
        print(f"  annual_revenue_estimate : €{row['annual_revenue_estimate']:,.0f}")
        print(f"  annual_revenue          : €{row['annual_revenue']:,.0f}")
        print(f"  average_check           : €{row['average_check']:.2f}")
        print(f"  covers_per_seat_month   : {row['covers_per_seat_month']:.2f}")
        print(f"  prime_cost_ratio        : {row['prime_cost_ratio']:.1%}")
        print(f"  rent_to_revenue         : {row['rent_to_revenue']:.1%}")
        print(f"  revenue_cv              : {row['revenue_cv']:.3f}")
        print(f"  cash_flow_margin        : {row['cash_flow_margin']:.1%}")
        print(f"  dscr_proxy              : {row['dscr_proxy']:.2f}")
        print(f"  years_active (raw)      : {years_raw:.4f}")
        print(f"  years_active (display)  : {years_display}")
        print(f"  bank_present            : {row['bank_present']}")
        print(f"  pos_present             : {row['pos_present']}")
        print(f"  accounting_present      : {row['accounting_present']}")
        print(f"  data_completeness       : {row['data_completeness']:.0f}%")

    print("\n" + "-" * 60)
    print("Lender dashboard — first 5 rows (selected columns)")
    print("-" * 60)
    dashboard = get_lender_dashboard_data(data_dir)
    display_cols = [
        "restaurant_id", "legal_name", "city",
        "revenue_band", "requested_loan_amount", "loan_purpose",
        "data_completeness", "prime_cost_ratio", "rent_to_revenue",
    ]
    print(dashboard[display_cols].head().to_string(index=False))

    print("\nSmoke test complete.")
