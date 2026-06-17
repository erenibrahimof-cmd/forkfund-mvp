"""
ForkFund rules-based scoring engine.

Public API
----------
score_all_restaurants(metrics_df)            -> scored DataFrame (55 columns)
score_restaurant(row, pop_context)           -> score-breakdown dict
build_pop_context(metrics_df)                -> population context dict for s7
assign_grade(score)                          -> str (A/B/C/D/E)
assign_risk_label(score)                     -> str
generate_score_drivers(row, score_breakdown) -> dict of scored drivers
"""

import bisect

import pandas as pd

# ---------------------------------------------------------------------------
# Scoring weights (must sum to 1.0)
# ---------------------------------------------------------------------------

WEIGHTS = {
    "data_completeness": 0.100,
    "revenue_stability": 0.125,
    "cashflow_strength": 0.150,
    "debt_burden":       0.150,
    "prime_cost":        0.150,
    "rent_pressure":     0.100,
    "pos_quality":       0.100,
    "seasonality":       0.075,
    "business_maturity": 0.050,
}

_DIM_KEYS = list(WEIGHTS.keys())

NEUTRAL = 50.0  # assigned when required source data is absent

_SCORE_COL = {
    "data_completeness": "s1_data_completeness",
    "revenue_stability": "s2_revenue_stability",
    "cashflow_strength": "s3_cashflow_strength",
    "debt_burden":       "s4_debt_burden",
    "prime_cost":        "s5_prime_cost",
    "rent_pressure":     "s6_rent_pressure",
    "pos_quality":       "s7_pos_quality",
    "seasonality":       "s8_seasonality",
    "business_maturity": "s9_business_maturity",
}

# ---------------------------------------------------------------------------
# Grade and risk label
# ---------------------------------------------------------------------------

def assign_grade(score: float) -> str:
    """Map composite score (0–100) to a grade letter (A–E)."""
    if score >= 85: return "A"
    if score >= 70: return "B"
    if score >= 55: return "C"
    if score >= 40: return "D"
    return "E"


def assign_risk_label(score: float) -> str:
    """Map composite score to a risk band label."""
    return {
        "A": "Low risk",
        "B": "Low-to-medium risk",
        "C": "Medium risk",
        "D": "High risk",
        "E": "Very high risk",
    }[assign_grade(score)]


# ---------------------------------------------------------------------------
# Population context
# ---------------------------------------------------------------------------

def build_pop_context(metrics_df: pd.DataFrame) -> dict:
    """
    Build sorted population lists for the three s7 POS-quality percentile
    components.  Call once on the full 80-restaurant dataset; pass the result
    to score_restaurant when scoring individual restaurants.
    """
    return {
        "average_check":         sorted(metrics_df["average_check"].dropna().tolist()),
        "covers_per_seat_month": sorted(metrics_df["covers_per_seat_month"].dropna().tolist()),
        "revpash":               sorted(metrics_df["revpash"].dropna().tolist()),
    }


# ---------------------------------------------------------------------------
# Percentile helper
# ---------------------------------------------------------------------------

def _percentile_score(value: float, sorted_pop: list) -> float:
    """
    Score a value as its percentile rank (0–100) in a pre-sorted population.

    Uses bisect_left so the minimum element scores 0 and the maximum scores 100.
    Clamps to [0, 100] as a safety guard.
    """
    n = len(sorted_pop)
    if n <= 1:
        return 50.0
    rank = bisect.bisect_left(sorted_pop, value)
    return max(0.0, min(100.0, rank / (n - 1) * 100.0))


# ---------------------------------------------------------------------------
# Sub-score functions
# ---------------------------------------------------------------------------

def _s1(row) -> float:
    return float(row["data_completeness"])


def _s2(row) -> float:
    if not row["pos_present"]:
        return NEUTRAL
    return max(0.0, min(100.0, 100.0 * (1.0 - float(row["revenue_cv"]))))


def _s3(row) -> float:
    if not row["bank_present"]:
        return NEUTRAL
    return max(0.0, min(100.0, 100.0 * float(row["cash_flow_margin"]) / 0.30))


def _s4(row) -> float:
    if not row["accounting_present"]:
        return NEUTRAL
    s4a = 100.0 * (1.0 - min(float(row["debt_to_revenue"]), 1.0))
    # dscr_proxy is already 100 for debt-free restaurants (set by data_loader);
    # min(100, 100 × 100 / 1.5) = 100, so no special case is needed here.
    s4b = max(0.0, min(100.0, 100.0 * float(row["dscr_proxy"]) / 1.50))
    return 0.5 * s4a + 0.5 * s4b


def _s5(row) -> float:
    if not row["accounting_present"]:
        return NEUTRAL
    pcr = float(row["prime_cost_ratio"])
    if pcr <= 0.60: return 100.0
    if pcr <= 0.65: return  75.0
    if pcr <= 0.70: return  50.0
    if pcr <= 0.80: return  25.0
    return 0.0


def _s6(row) -> float:
    if not row["accounting_present"]:
        return NEUTRAL
    rtr = float(row["rent_to_revenue"])
    if rtr <= 0.08: return 100.0
    if rtr <= 0.10: return  80.0
    if rtr <= 0.12: return  60.0
    if rtr <= 0.15: return  30.0
    return 0.0


def _s7(row, pop_context: dict) -> float:
    """
    POS demand quality: 3 components, 1/3 weight each:
      average_check, covers_per_seat_month, revpash.

    A fourth component (covers_vol = covers_per_seat_month × seats) was
    omitted because it is nearly perfectly correlated with covers_per_seat_month
    within any revenue band (both derived from the same monthly covers count).
    See docs/mvp_design.md §6.2 dimension 7 for the full rationale.
    """
    if not row["pos_present"]:
        return NEUTRAL
    s_avg = _percentile_score(float(row["average_check"]),         pop_context["average_check"])
    s_cov = _percentile_score(float(row["covers_per_seat_month"]), pop_context["covers_per_seat_month"])
    s_rev = _percentile_score(float(row["revpash"]),               pop_context["revpash"])
    return (s_avg + s_cov + s_rev) / 3.0


def _s8(row) -> float:
    """Seasonality and concentration risk: step functions per docs/mvp_design.md §6.2."""
    if not row["pos_present"]:
        return NEUTRAL

    cv = float(row["revenue_cv"])
    if   cv <= 0.10: s_seas = 100.0
    elif cv <= 0.15: s_seas =  75.0
    elif cv <= 0.20: s_seas =  50.0
    elif cv <= 0.30: s_seas =  25.0
    else:            s_seas =   0.0

    ds = float(row["delivery_share"])
    if   ds <= 0.15: s_del = 100.0
    elif ds <= 0.25: s_del =  75.0
    elif ds <= 0.35: s_del =  50.0
    elif ds <= 0.45: s_del =  25.0
    else:            s_del =   0.0

    ws = float(row["weekend_share"])
    if   ws <= 0.45: s_wknd = 100.0
    elif ws <= 0.55: s_wknd =  75.0
    elif ws <= 0.60: s_wknd =  50.0
    elif ws <= 0.70: s_wknd =  25.0
    else:            s_wknd =   0.0

    return 0.4 * s_seas + 0.3 * s_del + 0.3 * s_wknd


def _s9(row) -> float:
    # years_active is already capped at 10 by data_loader; min(100, ...) is a safety guard.
    return min(100.0, 100.0 * float(row["years_active"]) / 10.0)


# ---------------------------------------------------------------------------
# Public: score a single restaurant
# ---------------------------------------------------------------------------

def score_restaurant(row: pd.Series, pop_context: dict) -> dict:
    """
    Score one restaurant row from compute_restaurant_metrics().

    Parameters
    ----------
    row         : pd.Series, one row of the metrics DataFrame
    pop_context : dict, from build_pop_context(), used for s7 percentile scoring

    Returns
    -------
    dict:
        "sub_scores"  : {dim_key: float}
        "total_score" : float
        "grade"       : str
        "risk_label"  : str
    """
    sub_scores = {
        "data_completeness": _s1(row),
        "revenue_stability": _s2(row),
        "cashflow_strength": _s3(row),
        "debt_burden":       _s4(row),
        "prime_cost":        _s5(row),
        "rent_pressure":     _s6(row),
        "pos_quality":       _s7(row, pop_context),
        "seasonality":       _s8(row),
        "business_maturity": _s9(row),
    }
    total = sum(WEIGHTS[k] * sub_scores[k] for k in _DIM_KEYS)
    return {
        "sub_scores":  sub_scores,
        "total_score": total,
        "grade":       assign_grade(total),
        "risk_label":  assign_risk_label(total),
    }


# ---------------------------------------------------------------------------
# Public: score all restaurants
# ---------------------------------------------------------------------------

def score_all_restaurants(metrics_df: pd.DataFrame) -> pd.DataFrame:
    """
    Score all restaurants and return the augmented DataFrame.

    Adds to the 42-column metrics DataFrame:
      s1_data_completeness … s9_business_maturity  (9 raw sub-scores)
      total_score, grade, risk_label, peer_percentile

    Total: 55 columns.  peer_percentile is within the restaurant's revenue_band.
    """
    pop_context = build_pop_context(metrics_df)

    records = []
    for _, row in metrics_df.iterrows():
        bd     = score_restaurant(row, pop_context)
        record = {"restaurant_id": int(row["restaurant_id"])}
        for dim_key in _DIM_KEYS:
            record[_SCORE_COL[dim_key]] = bd["sub_scores"][dim_key]
        record["total_score"] = bd["total_score"]
        record["grade"]       = bd["grade"]
        record["risk_label"]  = bd["risk_label"]
        records.append(record)

    scores_df = pd.DataFrame(records)
    result    = metrics_df.merge(scores_df, on="restaurant_id", how="left").copy()

    # Peer percentile within revenue_band (0 = lowest scorer in band, 100 = highest)
    peer_pct = pd.Series(index=result.index, dtype=float)
    for _band, group in result.groupby("revenue_band"):
        n = len(group)
        if n <= 1:
            peer_pct.loc[group.index] = 50.0
        else:
            ranks = group["total_score"].rank(method="average")  # 1-indexed
            peer_pct.loc[group.index] = (ranks - 1) / (n - 1) * 100.0
    result["peer_percentile"] = peer_pct

    return result


# ---------------------------------------------------------------------------
# Score drivers: helper sentiment
# ---------------------------------------------------------------------------

def _sentiment(sub_score: float) -> str:
    if sub_score >= 70.0: return "positive"
    if sub_score >= 50.0: return "neutral"
    return "risk"


# ---------------------------------------------------------------------------
# Per-dimension driver functions
# ---------------------------------------------------------------------------

def _d1(row, score: float):
    dc = float(row["data_completeness"])
    if dc >= 100:
        return _sentiment(score), "All three data sources connected: maximum lender confidence."
    if dc >= 67:
        return "neutral", "Two of three data sources connected. Lender confidence is reduced."
    if dc >= 33:
        return "neutral", "Only one data source connected. Score is indicative only."
    return "risk", "No data sources connected. Score cannot be reliably assessed."


def _d2(row, score: float):
    if not row["pos_present"]:
        return "neutral", "POS data not connected. Revenue stability assessed with lower confidence (neutral 50)."
    cv   = float(row["revenue_cv"])
    sent = _sentiment(score)
    if sent == "positive":
        return sent, f"Monthly revenue is stable (CV {cv:.1%}), supporting predictable repayment capacity."
    if sent == "neutral":
        return sent, f"Moderate revenue volatility (CV {cv:.1%}) . Note the impact on repayment predictability."
    return sent, f"High revenue instability (CV {cv:.1%}) creates significant repayment uncertainty."


def _d3(row, score: float):
    if not row["bank_present"]:
        return "neutral", "Bank data not connected. Cash-flow strength assessed with lower confidence (neutral 50)."
    margin = float(row["cash_flow_margin"])
    if margin >= 0.30:
        return "positive", f"Strong net cash inflow margin of {margin:.0%}: exceeds the 30% benchmark."
    sent = _sentiment(score)
    if sent == "positive":
        # score=75 means margin is approaching but below 30%
        return sent, f"Solid cash inflow margin of {margin:.0%}: approaching the 30% benchmark."
    if sent == "neutral":
        return sent, f"Adequate cash inflow margin of {margin:.0%}: below the 30% benchmark target."
    return sent, f"Weak cash inflow margin of {margin:.0%}: may be insufficient to service new debt."


def _d4(row, score: float):
    if not row["accounting_present"]:
        return "neutral", "Accounting data not connected. Debt burden assessed with lower confidence (neutral 50)."
    dtr  = float(row["debt_to_revenue"])
    dscr = float(row["dscr_proxy"])
    debt = float(row["existing_debt"])
    if debt == 0:
        return "positive", "No existing debt: full repayment capacity available for new borrowing."
    sent = _sentiment(score)
    if sent == "positive":
        return sent, f"Low debt burden ({dtr:.0%} debt-to-revenue) and strong repayment capacity (DSCR {dscr:.2f}×)."
    if sent == "neutral":
        return sent, f"Moderate debt levels ({dtr:.0%} debt-to-revenue). DSCR of {dscr:.2f}x is below the 1.5x benchmark."
    return sent, f"High debt-to-revenue ({dtr:.0%}) and weak DSCR ({dscr:.2f}x): limited capacity for new borrowing."


def _d5(row, score: float):
    if not row["accounting_present"]:
        return "neutral", "Accounting data not connected. Prime cost assessed with lower confidence (neutral 50)."
    pcr = float(row["prime_cost_ratio"])
    if score >= 100.0:
        return "positive", f"Prime cost of {pcr:.0%}: within the healthy benchmark (under 60%)."
    if score >= 75.0:
        return "positive", f"Prime cost of {pcr:.0%}: in the caution band (60-65%). Margins are under mild pressure."
    if score >= 50.0:
        return "neutral",  f"Prime cost of {pcr:.0%}: in the warning zone (65-70%). Operating efficiency is below benchmark."
    if score >= 25.0:
        return "risk",     f"Prime cost of {pcr:.0%}: above the risk threshold (70-80%). Margins are heavily compressed."
    return "risk", f"Prime cost of {pcr:.0%}: in the danger zone (above 80%). Operating margins are critically compressed."


def _d6(row, score: float):
    if not row["accounting_present"]:
        return "neutral", "Accounting data not connected. Rent pressure assessed with lower confidence (neutral 50)."
    rtr = float(row["rent_to_revenue"])
    if score >= 80.0:
        return "positive", f"Rent-to-revenue of {rtr:.1%}: low fixed-cost occupancy pressure."
    if score >= 60.0:
        return "neutral",  f"Rent-to-revenue of {rtr:.1%}: in the occupancy caution band (10-12%)."
    if score >= 30.0:
        # score=30 has sentiment "risk" (30 < 40 threshold)
        return "risk",     f"Rent-to-revenue of {rtr:.1%}: high fixed-cost pressure (12-15%)."
    return "risk", f"Rent-to-revenue of {rtr:.1%}: very high occupancy pressure, exceeds the 15% risk threshold."


def _d7(row, score: float):
    if not row["pos_present"]:
        return "neutral", "POS data not connected. Demand quality assessed with lower confidence (neutral 50)."
    avg_check = float(row["average_check"])
    covers    = float(row["covers_per_seat_month"])
    revpash   = float(row["revpash"])
    sent      = _sentiment(score)
    if sent == "positive":
        return sent, (
            f"Strong POS demand quality: average check €{avg_check:.0f}, "
            f"{covers:.1f} covers/seat/month, RevPASH €{revpash:.2f}/seat-hour "
            f", all above-average relative to peer restaurants."
        )
    if sent == "neutral":
        return sent, (
            f"Moderate POS demand quality: average check €{avg_check:.0f}, "
            f"{covers:.1f} covers/seat/month relative to peer restaurants."
        )
    return sent, (
        f"Below-average POS demand quality: average check €{avg_check:.0f}, "
        f"{covers:.1f} covers/seat/month, RevPASH €{revpash:.2f}/seat-hour "
        f"relative to peer restaurants."
    )


def _d8(row, score: float):
    if not row["pos_present"]:
        return "neutral", "POS data not connected. Concentration risk assessed with lower confidence (neutral 50)."
    ds   = float(row["delivery_share"])
    ws   = float(row["weekend_share"])
    cv   = float(row["revenue_cv"])
    sent = _sentiment(score)
    flags = []
    if ds > 0.35: flags.append(f"delivery dependency {ds:.0%}")
    if ws > 0.60: flags.append(f"weekend revenue share {ws:.0%}")
    if cv > 0.20: flags.append(f"high seasonality CV {cv:.1%}")
    if sent == "positive":
        return sent, "Low concentration risk: revenue is stable and spread across time and channels."
    if sent == "neutral":
        flag_text = "; ".join(flags) if flags else f"delivery share {ds:.0%} and weekend share {ws:.0%}"
        return sent, f"Moderate concentration risk: {flag_text}."
    flag_text = "; ".join(flags) if flags else "multiple concentration factors"
    return sent, f"High concentration risk: {flag_text}."


def _d9(row, score: float):
    years = float(row["years_active"])
    if years < 1.0:
        return "risk", (
            f"Restaurant opened less than 1 year ago ({years:.2f} years): "
            "below common lender eligibility thresholds."
        )
    sent = _sentiment(score)
    if sent == "positive":
        return sent, f"Well-established restaurant with {years:.1f} years of operating history."
    if sent == "neutral":
        return sent, f"Restaurant has {years:.1f} years of operating history. Some maturity established."
    return sent, f"Limited operating history ({years:.1f} years). Lenders may require additional evidence."


_DRIVER_FNS = [
    ("data_completeness", _d1),
    ("revenue_stability", _d2),
    ("cashflow_strength", _d3),
    ("debt_burden",       _d4),
    ("prime_cost",        _d5),
    ("rent_pressure",     _d6),
    ("pos_quality",       _d7),
    ("seasonality",       _d8),
    ("business_maturity", _d9),
]


# ---------------------------------------------------------------------------
# Public: generate score drivers
# ---------------------------------------------------------------------------

def generate_score_drivers(row: pd.Series, score_breakdown: dict) -> dict:
    """
    Generate written driver texts for one restaurant.

    Parameters
    ----------
    row            : restaurant row (from metrics or scored DataFrame)
    score_breakdown: dict returned by score_restaurant (must contain "sub_scores")

    Returns
    -------
    dict:
        "drivers"      : list of 9 dicts, one per dimension:
                           {dimension, weight, sub_score, sentiment, text}
        "top_positive" : up to 3 highest-scoring positive drivers
        "top_risk"     : up to 3 lowest-scoring risk drivers
    """
    sub_scores = score_breakdown["sub_scores"]
    drivers    = []
    for dim_key, fn in _DRIVER_FNS:
        score           = sub_scores[dim_key]
        sentiment, text = fn(row, score)
        drivers.append({
            "dimension": dim_key,
            "weight":    WEIGHTS[dim_key],
            "sub_score": score,
            "sentiment": sentiment,
            "text":      text,
        })

    top_positive = sorted(
        [d for d in drivers if d["sentiment"] == "positive"],
        key=lambda d: -d["sub_score"],
    )[:3]

    explicit_risks = sorted(
        [d for d in drivers if d["sentiment"] == "risk"],
        key=lambda d: d["sub_score"],
    )

    # Always ensure at least 2 watch points for lenders:
    # if fewer than 2 explicit risk drivers, add the lowest-scoring neutral dims
    if len(explicit_risks) < 2:
        neutral_sorted = sorted(
            [d for d in drivers if d["sentiment"] == "neutral"],
            key=lambda d: d["sub_score"],
        )
        needed = 2 - len(explicit_risks)
        watch_points = []
        for d in neutral_sorted[:needed]:
            watch_points.append({
                **d,
                "sentiment": "watch",
                "text": d["text"] + " — monitor this dimension before lending.",
            })
        top_risk = (explicit_risks + watch_points)[:3]
    else:
        top_risk = explicit_risks[:3]

    return {
        "drivers":      drivers,
        "top_positive": top_positive,
        "top_risk":     top_risk,
    }


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.data_loader import get_lender_dashboard_data  # noqa: E402

    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"

    SEP  = "=" * 64
    SEP2 = "-" * 64

    print(SEP)
    print("ForkFund scoring engine: smoke test")
    print(SEP)

    metrics = get_lender_dashboard_data(data_dir)
    print(f"\nLoaded {len(metrics)} restaurant metrics.")

    scored = score_all_restaurants(metrics)
    print(f"Scored  {len(scored)} restaurants.")
    print(f"Output columns: {len(scored.columns)}")

    SUB_COLS = [
        "s1_data_completeness", "s2_revenue_stability", "s3_cashflow_strength",
        "s4_debt_burden",       "s5_prime_cost",        "s6_rent_pressure",
        "s7_pos_quality",       "s8_seasonality",       "s9_business_maturity",
    ]

    print(f"\n{SEP2}")
    print("Demo restaurant scores")
    print(SEP2)

    demo_results = {}
    for rid, name in [(1, "Bonne Table"), (41, "Trattoria Pietro"), (15, "Levant Express")]:
        row = scored[scored["restaurant_id"] == rid].iloc[0]
        ts  = row["total_score"]
        demo_results[rid] = {"total_score": ts, "grade": row["grade"]}

        print(f"\n── ID {rid}: {name}")
        print(f"  total_score     : {ts:.2f}")
        print(f"  grade           : {row['grade']}")
        print(f"  risk_label      : {row['risk_label']}")
        print(f"  peer_percentile : {row['peer_percentile']:.1f}%")
        print("  Sub-scores:")
        for col in SUB_COLS:
            label = col.split("_", 1)[1].replace("_", " ")
            print(f"    {label:<28}: {row[col]:.1f}")

    print(f"\n{SEP2}")
    print("Assertions")
    print(SEP2)

    r1, r41, r15 = demo_results[1], demo_results[41], demo_results[15]

    assert r1["total_score"] >= 85 and r1["grade"] == "A", (
        f"FAIL Bonne Table: score={r1['total_score']:.2f} grade={r1['grade']}"
    )
    print(f"  PASS  Bonne Table       : {r1['total_score']:.2f}  grade={r1['grade']}  (expected A, ≥85)")

    assert 55 <= r41["total_score"] <= 75 and r41["grade"] in {"B", "C"}, (
        f"FAIL Trattoria Pietro: score={r41['total_score']:.2f} grade={r41['grade']}"
    )
    print(f"  PASS  Trattoria Pietro  : {r41['total_score']:.2f}  grade={r41['grade']}  (expected B or C, 55–75)")

    assert r15["total_score"] < 55 and r15["grade"] in {"C", "D"}, (
        f"FAIL Levant Express: score={r15['total_score']:.2f} grade={r15['grade']}"
    )
    print(f"  PASS  Levant Express    : {r15['total_score']:.2f}  grade={r15['grade']}  (expected C or D, <55)")

    print(f"\n{SEP2}")
    print("Grade distribution (80 restaurants)")
    print(SEP2)
    for grade in ["A", "B", "C", "D", "E"]:
        count = int((scored["grade"] == grade).sum())
        bar   = "█" * count
        print(f"  {grade}: {count:>3}  {bar}")

    print(f"\n{SEP2}")
    print("Score drivers: demo restaurants")
    print(SEP2)

    pop_ctx = build_pop_context(metrics)
    icon_map = {"positive": "+", "neutral": "~", "risk": "!"}

    for rid, name in [(1, "Bonne Table"), (41, "Trattoria Pietro"), (15, "Levant Express")]:
        row_m   = metrics[metrics["restaurant_id"] == rid].iloc[0]
        bd      = score_restaurant(row_m, pop_ctx)
        result  = generate_score_drivers(row_m, bd)

        print(f"\n── ID {rid}: {name}")
        for d in result["drivers"]:
            icon = icon_map[d["sentiment"]]
            print(f"  [{icon}] {d['dimension']:<20} score={d['sub_score']:>5.1f}  {d['text']}")

        if result["top_positive"]:
            print("  Top positives :", ", ".join(d["dimension"] for d in result["top_positive"]))
        if result["top_risk"]:
            print("  Top risks     :", ", ".join(d["dimension"] for d in result["top_risk"]))

    print(f"\n{SEP}")
    print("All assertions passed.")
    print(SEP)
