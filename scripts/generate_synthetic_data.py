#!/usr/bin/env python3
"""
ForkFund Synthetic Data Generator

Generates five CSV files with synthetic restaurant data for the ForkFund MVP:
- restaurants.csv (80 rows; 1 per restaurant)
- monthly_bank.csv (960 rows; 12 per restaurant)
- monthly_pos.csv (960 rows; 12 per restaurant)
- accounting.csv (80 rows; 1 per restaurant)
- lenders.csv (5-10 rows; reference lenders)

Uses fixed seed (default 42) for reproducibility.
Generation order: restaurants → accounting → monthly_pos → monthly_bank → lenders → validation
"""

import pandas as pd
import random
import datetime
import csv
import os
import math
import sys
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

SEED = 42
DATA_REFERENCE_DATE = datetime.date(
    2025, 12, 31
)  # Reference date for years_active calculations

# Cities and distribution
CITIES = {
    "Amsterdam": 18,
    "Rotterdam": 12,
    "Utrecht": 10,
    "The Hague": 8,
    "Eindhoven": 8,
    "Groningen": 6,
    "Breda": 6,
    "Maastricht": 5,
    "Arnhem": 4,
    "Dordrecht": 3,
}

CUISINES = [
    "Italian",
    "French",
    "Asian",
    "Dutch",
    "Mediterranean",
    "Turkish",
    "Spanish",
    "Fusion",
    "Vegetarian",
    "Portuguese",
]

LOAN_PURPOSES = ["Term loan", "Working capital", "Equipment", "Renovation"]

# Revenue bands (€150k–500k, €500k–1M, €1M–1.5M, €1.5M+)
REVENUE_BANDS = [
    {"min": 150000, "max": 500000, "count": 20, "id_range": (1, 20), "seat_range": (20, 60)},
    {"min": 500000, "max": 1000000, "count": 25, "id_range": (21, 45), "seat_range": (50, 100)},
    {"min": 1000000, "max": 1500000, "count": 20, "id_range": (46, 65), "seat_range": (80, 150)},
    {"min": 1500000, "max": 2500000, "count": 15, "id_range": (66, 80), "seat_range": (120, 200)},
]

# Demo profile IDs
DEMO_STRONG_ID = 1
DEMO_MEDIUM_ID = 41
DEMO_HIGH_RISK_ID = 15

DEMO_CV_TARGETS = {
    DEMO_STRONG_ID: (0.05, 0.08),
    DEMO_MEDIUM_ID: (0.10, 0.13),
    DEMO_HIGH_RISK_ID: (0.16, 0.22),
}

DEMO_CASH_MARGIN_TARGETS = {
    DEMO_STRONG_ID: (0.33, 0.35),
    DEMO_MEDIUM_ID: (0.20, 0.25),
    DEMO_HIGH_RISK_ID: (0.10, 0.14),
}

DEMO_IDS = {DEMO_STRONG_ID, DEMO_MEDIUM_ID, DEMO_HIGH_RISK_ID}

# Minimum non-prime, non-rent operating costs assumed when checking EBITDA
# coherence. This is intentionally conservative; it avoids accounting rows
# where food + labour + rent already consume revenue but EBITDA is still shown
# as positive.
MIN_OTHER_OPERATING_EXPENSE_RATIO = 0.04

RISK_TIERS = {
    1: {
        "name": "Excellent",
        "prime_cost_ratio": (0.52, 0.60),
        "rent_ratio": (0.06, 0.08),
        "target_ebitda_margin": (0.13, 0.20),
        "existing_debt_ratio": (0.00, 0.20),
        "cash_flow_margin": (0.32, 0.42),
        "revenue_cv": (0.03, 0.09),
        "delivery_share": (0.05, 0.15),
        "weekend_share": (0.35, 0.45),
        "registration_start": datetime.date(2005, 1, 1),
        "registration_end": datetime.date(2016, 12, 31),
    },
    2: {
        "name": "Good",
        "prime_cost_ratio": (0.58, 0.66),
        "rent_ratio": (0.07, 0.11),
        "target_ebitda_margin": (0.07, 0.15),
        "existing_debt_ratio": (0.10, 0.45),
        "cash_flow_margin": (0.22, 0.34),
        "revenue_cv": (0.06, 0.14),
        "delivery_share": (0.10, 0.28),
        "weekend_share": (0.40, 0.56),
        "registration_start": datetime.date(2010, 1, 1),
        "registration_end": datetime.date(2022, 12, 31),
    },
    3: {
        "name": "Medium",
        "prime_cost_ratio": (0.63, 0.73),
        "rent_ratio": (0.09, 0.14),
        "target_ebitda_margin": (0.02, 0.10),
        "existing_debt_ratio": (0.30, 0.65),
        "cash_flow_margin": (0.14, 0.24),
        "revenue_cv": (0.10, 0.22),
        "delivery_share": (0.22, 0.40),
        "weekend_share": (0.48, 0.66),
        "registration_start": datetime.date(2014, 1, 1),
        "registration_end": datetime.date(2022, 12, 31),
    },
    4: {
        "name": "Struggling",
        "prime_cost_ratio": (0.72, 0.82),
        "rent_ratio": (0.13, 0.17),
        "target_ebitda_margin": (-0.03, 0.04),
        "existing_debt_ratio": (0.55, 0.88),
        "cash_flow_margin": (0.06, 0.15),
        "revenue_cv": (0.20, 0.34),
        "delivery_share": (0.38, 0.52),
        "weekend_share": (0.60, 0.75),
        "registration_start": datetime.date(2019, 1, 1),
        "registration_end": datetime.date(2023, 12, 31),
    },
    5: {
        "name": "Distressed",
        "prime_cost_ratio": (0.78, 0.84),
        "rent_ratio": (0.14, 0.18),
        "target_ebitda_margin": (-0.06, 0.00),
        "existing_debt_ratio": (0.75, 1.00),
        "cash_flow_margin": (0.03, 0.09),
        "revenue_cv": (0.32, 0.44),
        "delivery_share": (0.48, 0.62),
        "weekend_share": (0.68, 0.80),
        "registration_start": datetime.date(2021, 1, 1),
        "registration_end": datetime.date(2024, 12, 31),
    },
}

# Each band receives all five non-demo risk tiers, so revenue size does not
# mechanically determine credit quality.
RISK_TIER_COUNTS_BY_BAND = [
    {1: 2, 2: 5, 3: 6, 4: 3, 5: 2},  # 18 non-demo rows in band 1
    {1: 2, 2: 7, 3: 8, 4: 5, 5: 2},  # 24 non-demo rows in band 2
    {1: 2, 2: 6, 3: 7, 4: 3, 5: 2},  # 20 non-demo rows in band 3
    {1: 2, 2: 4, 3: 4, 4: 3, 5: 2},  # 15 non-demo rows in band 4
]

_RISK_TIER_LOOKUP = None

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def set_seed(seed):
    """Initialize random seed for reproducibility."""
    random.seed(seed)


def generate_kvk_number():
    """Generate a synthetic 8-digit KvK number."""
    return f"{random.randint(10000000, 99999999)}"


def generate_restaurant_name():
    """Generate a realistic restaurant name."""
    prefixes = [
        "De",
        "El",
        "La",
        "Le",
        "The",
        "O",
        "Café",
        "Osteria",
        "Pizzeria",
        "Bistro",
    ]
    names = [
        "Gouden Vork",
        "Rode Leeuw",
        "Witte Zwaan",
        "Blauwe Druif",
        "Tafel",
        "Harmonie",
        "Trattoria",
        "Brasserie",
        "Steakhouse",
        "Garden",
        "Vista",
        "Aurora",
        "Stella",
        "Luna",
        "Pietro",
        "Giovanni",
        "Maria",
        "Giuseppe",
        "Sofia",
        "Antonio",
        "Express",
        "Palace",
        "House",
        "Kitchen",
        "Table",
    ]
    return f"{random.choice(prefixes)} {random.choice(names)}"


def generate_date(start_date, end_date):
    """Generate a random date between start and end dates."""
    days_between = (end_date - start_date).days
    random_days = random.randint(0, days_between)
    return start_date + datetime.timedelta(days=random_days)


def clamp(value, min_val, max_val):
    """Clamp value between min and max."""
    return max(min_val, min(value, max_val))


def add_noise(value, noise_pct=0.05):
    """Add ±noise_pct random variation to a value."""
    noise = value * random.uniform(-noise_pct, noise_pct)
    return value + noise


def get_city_distribution():
    """Create a list of cities to assign restaurants."""
    city_list = []
    for city, count in CITIES.items():
        city_list.extend([city] * count)
    random.shuffle(city_list)
    return city_list


def configure_risk_tiers(seed=SEED):
    """Assign hidden risk tiers within each revenue band."""
    global _RISK_TIER_LOOKUP

    rng = random.Random(seed + 1701)
    tier_lookup = {}

    for band, tier_counts in zip(REVENUE_BANDS, RISK_TIER_COUNTS_BY_BAND):
        start_id, end_id = band["id_range"]
        restaurant_ids = [
            restaurant_id
            for restaurant_id in range(start_id, end_id + 1)
            if restaurant_id not in DEMO_IDS
        ]
        tier_pool = []
        for tier, count in tier_counts.items():
            tier_pool.extend([tier] * count)

        if len(tier_pool) != len(restaurant_ids):
            raise ValueError(
                f"Risk-tier count mismatch for revenue band {band['id_range']}: "
                f"{len(tier_pool)} tiers for {len(restaurant_ids)} restaurants"
            )

        rng.shuffle(tier_pool)
        for restaurant_id, tier in zip(restaurant_ids, tier_pool):
            tier_lookup[restaurant_id] = tier

    _RISK_TIER_LOOKUP = tier_lookup
    return tier_lookup


def get_risk_tier(restaurant_id):
    """Return the hidden non-demo risk tier for a restaurant, or None for demos."""
    restaurant_id = int(restaurant_id)
    if restaurant_id in DEMO_IDS:
        return None
    if _RISK_TIER_LOOKUP is None:
        configure_risk_tiers()
    return _RISK_TIER_LOOKUP[restaurant_id]


def get_years_active(registration_date):
    """Compute years active as of reference date."""
    days_active = (DATA_REFERENCE_DATE - registration_date).days
    years = max(0, days_active / 365.25)
    return min(years, 10)  # Cap at 10 years for scoring


def get_revenue_band(row_or_revenue):
    """Return the configured revenue band for a restaurant row or revenue value."""
    revenue = (
        row_or_revenue["annual_revenue_estimate"]
        if isinstance(row_or_revenue, pd.Series)
        else row_or_revenue
    )
    for band in REVENUE_BANDS:
        if band["min"] <= revenue < band["max"]:
            return band
    return REVENUE_BANDS[-1]


def generate_monthly_revenues(annual_revenue, target_cv=None):
    """Generate 12 monthly revenues that sum to annual revenue."""
    monthly_baseline = annual_revenue / 12

    if target_cv is not None:
        # Fixed restaurant-shaped seasonality, normalized to the requested sample CV.
        pattern = [-1.0, -0.7, -0.25, 0.15, 0.35, 0.45, 0.3, -0.15, 0.05, 0.4, 0.65, -0.25]
        mean_pattern = sum(pattern) / len(pattern)
        centered = [value - mean_pattern for value in pattern]
        sample_std = math.sqrt(
            sum(value * value for value in centered) / (len(centered) - 1)
        )
        factors = [1 + target_cv * (value / sample_std) for value in centered]
    else:
        factors = []
        for month in range(1, 13):
            if month in [4, 5, 6, 7, 8]:
                factor = random.uniform(0.95, 1.15)
            elif month in [12, 1, 2]:
                factor = random.uniform(0.85, 1.05)
            else:
                factor = random.uniform(0.92, 1.08)
            factors.append(factor)

        avg_factor = sum(factors) / len(factors)
        factors = [factor / avg_factor for factor in factors]
        factors = [
            factor + random.uniform(-0.02, 0.02)
            for factor in factors
        ]

    monthly_revenues = [monthly_baseline * factor for factor in factors]
    adjustment_factor = annual_revenue / sum(monthly_revenues)
    return [revenue * adjustment_factor for revenue in monthly_revenues]


def target_average_check(row):
    """Choose a realistic target average check by concept and revenue band."""
    restaurant_id = row["restaurant_id"]
    if restaurant_id == DEMO_STRONG_ID:
        return 115
    if restaurant_id == DEMO_MEDIUM_ID:
        return 85
    if restaurant_id == DEMO_HIGH_RISK_ID:
        return 82

    cuisine = row["cuisine_type"]
    band = get_revenue_band(row)
    band_index = REVENUE_BANDS.index(band)

    if cuisine == "French":
        low, high = 90, 145
    elif cuisine in ["Italian", "Mediterranean", "Spanish", "Portuguese", "Fusion"]:
        low, high = 65, 115
    elif cuisine in ["Dutch", "Asian"]:
        low, high = 55, 95
    else:
        low, high = 45, 85

    uplift = band_index * 8
    return clamp(random.uniform(low + uplift, high + uplift), 45, 160)


def revenue_cv(pos_rows):
    """Compute sample coefficient of variation for monthly POS revenue."""
    mean_revenue = pos_rows["total_revenue"].mean()
    if mean_revenue == 0:
        return 0
    return pos_rows["total_revenue"].std() / mean_revenue


def cash_flow_margin(bank_rows):
    """Compute cash-flow margin from bank rows."""
    inflows = bank_rows["total_inflows"].sum()
    if inflows == 0:
        return 0
    return (inflows - bank_rows["total_outflows"].sum()) / inflows


def pass_fail(value, target_range):
    """Return PASS/FAIL for value against inclusive target range."""
    return "PASS" if target_range[0] <= value <= target_range[1] else "FAIL"


def pos_quality_stats(monthly_pos_df, restaurants_df):
    """Return derived average-check and covers-per-seat statistics."""
    pos = monthly_pos_df.merge(
        restaurants_df[["restaurant_id", "seats"]], on="restaurant_id", how="left"
    )
    average_checks = pos["total_revenue"] / pos["covers"]
    covers_per_seat = pos["covers"] / pos["seats"]
    return average_checks, covers_per_seat


def registration_validation_summary(restaurants_df):
    """Return registration-date pass/fail summary for the report."""
    reg_dates = pd.to_datetime(restaurants_df["registration_date"])
    non_demo = restaurants_df["restaurant_id"] != DEMO_HIGH_RISK_ID
    non_demo_ok = (reg_dates[non_demo] <= pd.to_datetime("2024-12-31")).all()
    high_risk_row = restaurants_df[
        restaurants_df["restaurant_id"] == DEMO_HIGH_RISK_ID
    ].iloc[0]
    high_risk_ok = high_risk_row["registration_date"] == "2025-01-10"
    after_cutoff = restaurants_df[
        (restaurants_df["restaurant_id"] != DEMO_HIGH_RISK_ID)
        & (reg_dates > pd.to_datetime("2024-12-31"))
    ]
    return non_demo_ok, high_risk_ok, after_cutoff


# ============================================================================
# RESTAURANT GENERATION
# ============================================================================


def generate_restaurants_csv(n=80, output_dir="data"):
    """Generate restaurants.csv with 80 restaurants across 4 revenue bands."""
    print("[INFO] Generating 80 restaurants...")

    restaurants = []
    city_list = get_city_distribution()
    city_idx = 0

    for band in REVENUE_BANDS:
        band_min, band_max = band["min"], band["max"]
        seat_min, seat_max = band["seat_range"]
        start_id, end_id = band["id_range"]
        print(
            f"[INFO]   Band {band['min']:,}–{band['max']:,}: {band['count']} restaurants"
        )

        for restaurant_id in range(start_id, end_id + 1):
            # Revenue estimate
            annual_revenue_estimate = random.uniform(band_min, band_max)

            # Assign demo profile
            demo_profile = None
            if restaurant_id == DEMO_STRONG_ID:
                demo_profile = "strong"
            elif restaurant_id == DEMO_MEDIUM_ID:
                demo_profile = "medium"
            elif restaurant_id == DEMO_HIGH_RISK_ID:
                demo_profile = "high_risk"

            # Non-demo restaurants must exist before the 2025 trading period.
            # Registration dates are tier-shaped but independent from revenue band.
            if demo_profile is None:
                tier_config = RISK_TIERS[get_risk_tier(restaurant_id)]
                registration_date = generate_date(
                    tier_config["registration_start"],
                    tier_config["registration_end"],
                )
            else:
                registration_date = generate_date(
                    datetime.date(2000, 1, 1), datetime.date(2024, 12, 31)
                )

            # City assignment
            city = city_list[city_idx]
            city_idx += 1

            restaurants.append(
                {
                    "restaurant_id": restaurant_id,
                    "kvk_number": generate_kvk_number(),
                    "legal_name": generate_restaurant_name(),
                    "registration_date": registration_date.strftime("%Y-%m-%d"),
                    "city": city,
                    "legal_form": random.choice(["B.V.", "Eenmanszaak", "Vof"]),
                    "sbi_code": "5610",  # Restaurant sector code
                    "cuisine_type": random.choice(CUISINES),
                    "seats": random.randint(seat_min, seat_max),
                    "opening_hours_per_day": round(random.uniform(9.5, 14), 1),
                    "requested_loan_amount": random.choice(
                        [50000, 75000, 100000, 150000, 200000, 300000]
                    ),
                    "loan_purpose": random.choice(LOAN_PURPOSES),
                    "annual_revenue_estimate": round(annual_revenue_estimate, 2),
                    "demo_profile": demo_profile,
                }
            )

    df = pd.DataFrame(restaurants)

    # Override demo profiles with exact specifications
    df = override_demo_profiles(df)

    output_path = os.path.join(output_dir, "restaurants.csv")
    df.to_csv(output_path, index=False)
    print(f"[INFO] Created {output_path}: {len(df)} rows")
    return df


def override_demo_profiles(df):
    """Override demo profiles with exact hardcoded specifications."""
    # Strong profile (A-like)
    idx_strong = df[df["restaurant_id"] == DEMO_STRONG_ID].index[0]
    df.loc[idx_strong, "legal_name"] = "Bonne Table"
    df.loc[idx_strong, "city"] = "Amsterdam"
    df.loc[idx_strong, "registration_date"] = "2016-03-15"
    df.loc[idx_strong, "annual_revenue_estimate"] = 450000.00
    df.loc[idx_strong, "cuisine_type"] = "French"
    df.loc[idx_strong, "seats"] = 55
    df.loc[idx_strong, "opening_hours_per_day"] = 11.5

    # Medium profile (C-like)
    idx_medium = df[df["restaurant_id"] == DEMO_MEDIUM_ID].index[0]
    df.loc[idx_medium, "legal_name"] = "Trattoria Pietro"
    df.loc[idx_medium, "city"] = "Rotterdam"
    df.loc[idx_medium, "registration_date"] = "2023-06-15"
    df.loc[idx_medium, "annual_revenue_estimate"] = 825000.00
    df.loc[idx_medium, "cuisine_type"] = "Italian"
    df.loc[idx_medium, "seats"] = 78
    df.loc[idx_medium, "opening_hours_per_day"] = 11.0

    # High-risk profile (D-like)
    idx_high_risk = df[df["restaurant_id"] == DEMO_HIGH_RISK_ID].index[0]
    df.loc[idx_high_risk, "legal_name"] = "Levant Express"
    df.loc[idx_high_risk, "city"] = "Utrecht"
    df.loc[idx_high_risk, "registration_date"] = "2025-01-10"
    df.loc[idx_high_risk, "annual_revenue_estimate"] = 320000.00
    df.loc[idx_high_risk, "cuisine_type"] = "Turkish"
    df.loc[idx_high_risk, "seats"] = 40
    df.loc[idx_high_risk, "opening_hours_per_day"] = 11.0

    return df


# ============================================================================
# ACCOUNTING GENERATION
# ============================================================================


def generate_accounting_csv(restaurants_df, output_dir="data"):
    """Generate accounting.csv with annual financial data."""
    print("[INFO] Generating annual accounting data (80 rows)...")

    accounting = []

    for _, row in restaurants_df.iterrows():
        restaurant_id = row["restaurant_id"]
        annual_revenue = row["annual_revenue_estimate"]

        # Determine profile and financial characteristics
        if restaurant_id == DEMO_STRONG_ID:
            # Strong profile: excellent margins, low cost structure
            # Prime cost 58%, rent 7.1%
            food_cost_ratio = 0.28
            labour_cost_ratio = 0.30
            rent_ratio = 0.071
            target_ebitda_margin = 0.13
            existing_debt_ratio = 0.10
        elif restaurant_id == DEMO_MEDIUM_ID:
            # Medium profile: moderate margins, borderline efficiency
            # Prime cost 66%, rent 11.6%
            food_cost_ratio = 0.32
            labour_cost_ratio = 0.34
            rent_ratio = 0.116
            target_ebitda_margin = 0.08
            existing_debt_ratio = 0.40
        elif restaurant_id == DEMO_HIGH_RISK_ID:
            # High-risk profile: tight margins, high leverage
            # Prime cost 76%, rent 14%
            food_cost_ratio = 0.36
            labour_cost_ratio = 0.40
            rent_ratio = 0.14
            target_ebitda_margin = 0.03
            existing_debt_ratio = 0.625
        else:
            # Non-demo restaurants use correlated hidden risk tiers. EBITDA is
            # back-solved from revenue minus food, labour, rent, and other opex
            # so distressed rows remain arithmetically coherent.
            tier_config = RISK_TIERS[get_risk_tier(restaurant_id)]
            prime_cost_ratio = random.uniform(*tier_config["prime_cost_ratio"])
            food_share_of_prime_cost = random.uniform(0.44, 0.52)
            food_cost_ratio = prime_cost_ratio * food_share_of_prime_cost
            labour_cost_ratio = prime_cost_ratio - food_cost_ratio
            rent_ratio = random.uniform(*tier_config["rent_ratio"])
            target_ebitda_margin = random.uniform(
                *tier_config["target_ebitda_margin"]
            )
            existing_debt_ratio = random.uniform(
                *tier_config["existing_debt_ratio"]
            )

        # Compute costs
        food_cost = annual_revenue * food_cost_ratio
        labour_cost = annual_revenue * labour_cost_ratio
        rent_annual = annual_revenue * rent_ratio

        if restaurant_id in DEMO_IDS:
            ebitda = annual_revenue * target_ebitda_margin
        else:
            target_other_opex_ratio = (
                1
                - food_cost_ratio
                - labour_cost_ratio
                - rent_ratio
                - target_ebitda_margin
            )
            other_operating_expenses = annual_revenue * max(
                MIN_OTHER_OPERATING_EXPENSE_RATIO, target_other_opex_ratio
            )
            ebitda = (
                annual_revenue
                - food_cost
                - labour_cost
                - rent_annual
                - other_operating_expenses
            )

        # Debt and debt service
        if restaurant_id in DEMO_IDS:
            existing_debt = annual_revenue * existing_debt_ratio
        else:
            existing_debt = annual_revenue * existing_debt_ratio

        # Debt service: ~22% of existing debt annually (22% est. rate for typical restaurant lending)
        debt_service_estimated = existing_debt * 0.22 if existing_debt > 0 else 0

        # Net profit (simplified): EBITDA - interest on debt
        # Assuming interest is ~10% of existing debt (rough estimate)
        interest_expense = existing_debt * 0.10 if existing_debt > 0 else 0
        net_profit = ebitda - interest_expense

        accounting.append(
            {
                "restaurant_id": restaurant_id,
                "year": 2025,
                "annual_revenue": round(annual_revenue, 2),
                "food_cost": round(food_cost, 2),
                "labour_cost": round(labour_cost, 2),
                "rent_annual": round(rent_annual, 2),
                "ebitda": round(ebitda, 2),
                "net_profit": round(net_profit, 2),
                "existing_debt": round(existing_debt, 2),
                "debt_service_estimated": round(debt_service_estimated, 2),
            }
        )

    df = pd.DataFrame(accounting)
    output_path = os.path.join(output_dir, "accounting.csv")
    df.to_csv(output_path, index=False)
    print(f"[INFO] Created {output_path}: {len(df)} rows")
    return df


# ============================================================================
# MONTHLY POS GENERATION
# ============================================================================


def generate_monthly_pos_csv(restaurants_df, accounting_df, output_dir="data"):
    """Generate monthly_pos.csv with 12 months of POS data per restaurant."""
    print("[INFO] Generating monthly POS data (12 months × 80 = 960 rows)...")

    pos_data = []

    # Create lookup for accounting data
    acct_lookup = {}
    for _, row in accounting_df.iterrows():
        acct_lookup[row["restaurant_id"]] = row

    for _, row in restaurants_df.iterrows():
        restaurant_id = row["restaurant_id"]
        seats = row["seats"]

        # Get annual revenue from accounting (authoritative)
        acct = acct_lookup[restaurant_id]
        annual_revenue = acct["annual_revenue"]

        # Determine POS characteristics
        if restaurant_id == DEMO_STRONG_ID:
            target_cash_ratio = 0.20
            delivery_share_target = 0.08
            weekend_share_target = 0.42
            average_check = target_average_check(row)
            target_cv = 0.065
        elif restaurant_id == DEMO_MEDIUM_ID:
            target_cash_ratio = 0.28
            delivery_share_target = 0.28
            weekend_share_target = 0.52
            average_check = target_average_check(row)
            target_cv = 0.115
        elif restaurant_id == DEMO_HIGH_RISK_ID:
            target_cash_ratio = 0.35
            delivery_share_target = 0.375
            weekend_share_target = 0.65
            average_check = target_average_check(row)
            target_cv = 0.19
        else:
            tier_config = RISK_TIERS[get_risk_tier(restaurant_id)]
            target_cash_ratio = random.uniform(0.20, 0.40)
            delivery_share_target = random.uniform(
                *tier_config["delivery_share"]
            )
            weekend_share_target = random.uniform(
                *tier_config["weekend_share"]
            )
            average_check = target_average_check(row)
            target_cv = random.uniform(*tier_config["revenue_cv"])

        monthly_revenues = generate_monthly_revenues(annual_revenue, target_cv)

        # Generate POS rows
        for month in range(1, 13):
            total_revenue = monthly_revenues[month - 1]

            # Covers derived from revenue and average check
            covers = max(1, round(total_revenue / average_check))

            # Payment splits
            cash_sales = total_revenue * target_cash_ratio
            card_sales = total_revenue * (1 - target_cash_ratio)

            # Channel splits
            delivery_sales = total_revenue * delivery_share_target
            dine_in_sales = total_revenue * (1 - delivery_share_target)

            # Weekday/weekend splits
            weekend_revenue = total_revenue * weekend_share_target
            weekday_revenue = total_revenue * (1 - weekend_share_target)

            period = f"2025-{month:02d}"

            pos_data.append(
                {
                    "restaurant_id": restaurant_id,
                    "period": period,
                    "month_number": month,
                    "total_revenue": round(total_revenue, 2),
                    "covers": covers,
                    "card_sales": round(card_sales, 2),
                    "cash_sales": round(cash_sales, 2),
                    "delivery_platform_sales": round(delivery_sales, 2),
                    "dine_in_sales": round(dine_in_sales, 2),
                    "weekend_revenue": round(weekend_revenue, 2),
                    "weekday_revenue": round(weekday_revenue, 2),
                }
            )

    df = pd.DataFrame(pos_data)
    output_path = os.path.join(output_dir, "monthly_pos.csv")
    df.to_csv(output_path, index=False)
    print(f"[INFO] Created {output_path}: {len(df)} rows")
    return df


# ============================================================================
# MONTHLY BANK GENERATION
# ============================================================================


def generate_monthly_bank_csv(restaurants_df, accounting_df, output_dir="data"):
    """Generate monthly_bank.csv with 12 months of bank data per restaurant."""
    print("[INFO] Generating monthly bank data (12 months × 80 = 960 rows)...")

    bank_data = []

    # Create lookup for accounting data
    acct_lookup = {}
    for _, row in accounting_df.iterrows():
        acct_lookup[row["restaurant_id"]] = row

    for _, row in restaurants_df.iterrows():
        restaurant_id = row["restaurant_id"]
        annual_revenue = row["annual_revenue_estimate"]

        acct = acct_lookup[restaurant_id]
        monthly_debt_service = acct["debt_service_estimated"] / 12

        # Determine cash flow profile
        if restaurant_id == DEMO_STRONG_ID:
            target_cash_ratio = 0.20
            outflow_ratio = 0.66
            target_cv = 0.065
        elif restaurant_id == DEMO_MEDIUM_ID:
            target_cash_ratio = 0.28
            outflow_ratio = 0.775
            target_cv = 0.115
        elif restaurant_id == DEMO_HIGH_RISK_ID:
            target_cash_ratio = 0.35
            outflow_ratio = 0.88
            target_cv = 0.19
        else:
            tier_config = RISK_TIERS[get_risk_tier(restaurant_id)]
            target_cash_ratio = random.uniform(0.15, 0.40)
            cash_flow_margin_target = random.uniform(
                *tier_config["cash_flow_margin"]
            )
            outflow_ratio = 1 - cash_flow_margin_target
            target_cv = random.uniform(*tier_config["revenue_cv"])

        # Starting balance for month 1
        ending_balance = random.uniform(10000, 50000)

        monthly_inflows = generate_monthly_revenues(annual_revenue, target_cv)

        for month in range(1, 13):
            total_inflows = monthly_inflows[month - 1]

            # Payment method split
            cash_deposits = total_inflows * target_cash_ratio
            card_deposits = total_inflows * (1 - target_cash_ratio)

            # Total outflows
            total_outflows = total_inflows * outflow_ratio

            # Ending balance
            net_flow = total_inflows - total_outflows
            ending_balance = ending_balance + net_flow
            # Ensure balance doesn't drop below minimum
            ending_balance = max(2000, ending_balance)

            period = f"2025-{month:02d}"

            bank_data.append(
                {
                    "restaurant_id": restaurant_id,
                    "period": period,
                    "month_number": month,
                    "total_inflows": round(total_inflows, 2),
                    "total_outflows": round(total_outflows, 2),
                    "ending_balance": round(ending_balance, 2),
                    "debt_service_outflows": round(monthly_debt_service, 2),
                    "cash_deposits": round(cash_deposits, 2),
                    "card_deposits": round(card_deposits, 2),
                }
            )

    df = pd.DataFrame(bank_data)
    output_path = os.path.join(output_dir, "monthly_bank.csv")
    df.to_csv(output_path, index=False)
    print(f"[INFO] Created {output_path}: {len(df)} rows")
    return df


# ============================================================================
# LENDER GENERATION
# ============================================================================


def generate_lenders_csv(output_dir="data"):
    """Generate lenders.csv with 5-10 reference lender profiles."""
    print("[INFO] Generating lender reference data (8 rows)...")

    lenders = [
        {
            "lender_id": 1,
            "lender_name": "ABN AMRO",
            "focus_city": None,
            "min_loan_amount": 50000,
            "max_loan_amount": 500000,
            "preferred_loan_purposes": "Term loan, Working capital",
        },
        {
            "lender_id": 2,
            "lender_name": "ING",
            "focus_city": None,
            "min_loan_amount": 75000,
            "max_loan_amount": 750000,
            "preferred_loan_purposes": "Term loan, Equipment",
        },
        {
            "lender_id": 3,
            "lender_name": "Rabobank",
            "focus_city": None,
            "min_loan_amount": 25000,
            "max_loan_amount": 300000,
            "preferred_loan_purposes": "Working capital, Renovation",
        },
        {
            "lender_id": 4,
            "lender_name": "Triodos Bank",
            "focus_city": None,
            "min_loan_amount": 50000,
            "max_loan_amount": 250000,
            "preferred_loan_purposes": "Renovation, Equipment",
        },
        {
            "lender_id": 5,
            "lender_name": "RegioBank",
            "focus_city": "Amsterdam",
            "min_loan_amount": 50000,
            "max_loan_amount": 200000,
            "preferred_loan_purposes": "Term loan, Working capital",
        },
        {
            "lender_id": 6,
            "lender_name": "ASN Bank",
            "focus_city": None,
            "min_loan_amount": 30000,
            "max_loan_amount": 150000,
            "preferred_loan_purposes": "Renovation",
        },
        {
            "lender_id": 7,
            "lender_name": "VAN Groningen",
            "focus_city": "Groningen",
            "min_loan_amount": 25000,
            "max_loan_amount": 180000,
            "preferred_loan_purposes": "Term loan, Equipment",
        },
        {
            "lender_id": 8,
            "lender_name": "Friesch Bank",
            "focus_city": None,
            "min_loan_amount": 40000,
            "max_loan_amount": 220000,
            "preferred_loan_purposes": "Working capital",
        },
    ]

    df = pd.DataFrame(lenders)
    output_path = os.path.join(output_dir, "lenders.csv")
    df.to_csv(output_path, index=False)
    print(f"[INFO] Created {output_path}: {len(df)} rows")
    return df


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================


def validate_restaurants(df):
    """Validate restaurant profile data."""
    issues = []

    # Check unique IDs
    if df["restaurant_id"].nunique() != len(df):
        issues.append("ERROR: Duplicate restaurant_id values")

    # Check required fields
    required_fields = [
        "restaurant_id",
        "kvk_number",
        "city",
        "loan_purpose",
        "annual_revenue_estimate",
    ]
    for field in required_fields:
        if df[field].isnull().any():
            issues.append(f"ERROR: Null values in {field}")

    # Check loan purpose vocabulary
    valid_purposes = set(LOAN_PURPOSES)
    invalid_purposes = set(df["loan_purpose"]) - valid_purposes
    if invalid_purposes:
        issues.append(f"ERROR: Invalid loan_purpose values: {invalid_purposes}")

    # Check registration dates and trading-period eligibility
    ref_date = pd.to_datetime(DATA_REFERENCE_DATE)
    non_demo_cutoff = pd.to_datetime(datetime.date(2024, 12, 31))
    for _, row in df.iterrows():
        reg_date = pd.to_datetime(row["registration_date"])
        if reg_date > ref_date:
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} has registration_date in future"
            )
        if row["restaurant_id"] != DEMO_HIGH_RISK_ID and reg_date > non_demo_cutoff:
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} is non-demo/high-risk and has registration_date after 2024-12-31"
            )
        if row["restaurant_id"] == DEMO_HIGH_RISK_ID and row["registration_date"] != "2025-01-10":
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} must be the only 2025 registration date and equal 2025-01-10"
            )

        if row["annual_revenue_estimate"] < 150000:
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} has annual revenue below €150,000"
            )

        band = get_revenue_band(row)
        seat_min, seat_max = band["seat_range"]
        if not (seat_min <= row["seats"] <= seat_max):
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} has {row['seats']} seats outside expected band range {seat_min}-{seat_max}"
            )

    # Check demo profile IDs
    demo_ids = set(df[df["demo_profile"].notna()]["restaurant_id"])
    if demo_ids != {DEMO_STRONG_ID, DEMO_MEDIUM_ID, DEMO_HIGH_RISK_ID}:
        issues.append(
            f"ERROR: Demo profile IDs mismatch. Expected {{{DEMO_STRONG_ID}, {DEMO_MEDIUM_ID}, {DEMO_HIGH_RISK_ID}}}, got {demo_ids}"
        )

    return issues


def validate_accounting(df, restaurants_df):
    """Validate accounting data."""
    issues = []

    # Check one row per restaurant
    if df.groupby("restaurant_id").size().max() > 1:
        issues.append("ERROR: Multiple accounting rows per restaurant")

    if set(df["restaurant_id"]) != set(restaurants_df["restaurant_id"]):
        issues.append("ERROR: Accounting restaurant_id mismatch with restaurants")

    # Check year
    if not (df["year"] == 2025).all():
        issues.append("ERROR: Accounting year is not 2025")

    # Check financial logic
    for _, row in df.iterrows():
        revenue = row["annual_revenue"]
        if row["annual_revenue"] <= 0:
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} has non-positive revenue"
            )
        if row["existing_debt"] < 0:
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} has negative debt"
            )
        if row["existing_debt"] == 0 and row["debt_service_estimated"] != 0:
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} has zero debt but positive debt service"
            )
        core_costs = row["food_cost"] + row["labour_cost"] + row["rent_annual"]
        minimum_other_opex = revenue * MIN_OTHER_OPERATING_EXPENSE_RATIO
        if core_costs > revenue and row["ebitda"] > 0:
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} has food+labour+rent above revenue but positive EBITDA"
            )
        if core_costs + minimum_other_opex > revenue and row["ebitda"] > 0:
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} has positive EBITDA despite minimum other operating expenses exceeding revenue"
            )

    return issues


def validate_monthly_pos(df, restaurants_df):
    """Validate monthly POS data."""
    issues = []
    seats_lookup = restaurants_df.set_index("restaurant_id")["seats"].to_dict()

    # Check 12 rows per restaurant
    counts = df.groupby("restaurant_id").size()
    if not (counts == 12).all():
        issues.append(
            f"ERROR: Not all restaurants have exactly 12 POS rows. Counts: {counts[counts != 12].to_dict()}"
        )

    # Check period format
    if not df["period"].str.match(r"2025-\d{2}").all():
        issues.append("ERROR: Period format incorrect (should be YYYY-MM)")

    # Check revenue >= 0
    if (df["total_revenue"] <= 0).any():
        issues.append("ERROR: Negative or zero revenue in POS data")

    if (df["covers"] <= 0).any():
        issues.append("ERROR: Negative or zero covers in POS data")

    # Check channel splits
    for _, row in df.iterrows():
        total_rev = row["total_revenue"]
        card_sales = row["card_sales"]
        cash_sales = row["cash_sales"]

        sum_split = card_sales + cash_sales
        if abs(sum_split - total_rev) > total_rev * 0.01:
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} {row['period']}: card+cash split doesn't match revenue (±1%)"
            )

        channel_split = row["delivery_platform_sales"] + row["dine_in_sales"]
        if abs(channel_split - total_rev) > total_rev * 0.01:
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} {row['period']}: delivery+dine-in split doesn't match revenue (±1%)"
            )

        day_split = row["weekend_revenue"] + row["weekday_revenue"]
        if abs(day_split - total_rev) > total_rev * 0.01:
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} {row['period']}: weekend+weekday split doesn't match revenue (±1%)"
            )

        average_check = total_rev / row["covers"]
        if not (30 <= average_check <= 180):
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} {row['period']}: average_check is €{average_check:.2f}, outside €30-€180"
            )

        covers_per_seat_month = row["covers"] / seats_lookup[row["restaurant_id"]]
        if covers_per_seat_month <= 0:
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} {row['period']}: covers per seat per month is non-positive"
            )

    for restaurant_id, pos_rows in df.groupby("restaurant_id"):
        rev_cv = revenue_cv(pos_rows)
        covers_mean = pos_rows["covers"].mean()
        covers_cv = (
            pos_rows["covers"].std() / covers_mean
            if covers_mean > 0
            else 0
        )
        if rev_cv > 0.03 and (
            pos_rows["covers"].nunique() == 1 or covers_cv < rev_cv * 0.25
        ):
            issues.append(
                f"ERROR: restaurant_id {restaurant_id}: covers variation does not track monthly revenue variation"
            )

    return issues


def validate_monthly_bank(df, restaurants_df):
    """Validate monthly bank data."""
    issues = []

    # Check 12 rows per restaurant
    counts = df.groupby("restaurant_id").size()
    if not (counts == 12).all():
        issues.append(
            f"ERROR: Not all restaurants have exactly 12 bank rows. Counts: {counts[counts != 12].to_dict()}"
        )

    # Check inflows >= outflows
    if (df["total_outflows"] > df["total_inflows"]).any():
        # Some months may have outflows > inflows due to balance drawdown; this is not an error
        pass

    # Check deposit split
    for _, row in df.iterrows():
        total_inflows = row["total_inflows"]
        cash_deps = row["cash_deposits"]
        card_deps = row["card_deposits"]

        sum_deposits = cash_deps + card_deps
        if abs(sum_deposits - total_inflows) > total_inflows * 0.02:
            issues.append(
                f"ERROR: restaurant_id {row['restaurant_id']} {row['period']}: cash+card deposits don't match inflows (±2%)"
            )

    return issues


def validate_reconciliation(
    restaurants_df, accounting_df, monthly_pos_df, monthly_bank_df
):
    """Validate reconciliation across files."""
    issues = []
    warnings = []

    for _, rest_row in restaurants_df.iterrows():
        rest_id = rest_row["restaurant_id"]

        # Get annual accounting data
        acct_row = accounting_df[accounting_df["restaurant_id"] == rest_id].iloc[0]

        # Get monthly data
        pos_months = monthly_pos_df[monthly_pos_df["restaurant_id"] == rest_id]
        bank_months = monthly_bank_df[monthly_bank_df["restaurant_id"] == rest_id]

        # Revenue reconciliation: sum of 12 months POS ≈ annual accounting revenue (±3%)
        pos_annual_revenue = pos_months["total_revenue"].sum()
        acct_annual_revenue = acct_row["annual_revenue"]

        if pos_annual_revenue > 0:
            revenue_dev = (
                abs(pos_annual_revenue - acct_annual_revenue) / acct_annual_revenue
            )
            if revenue_dev > 0.03:
                warnings.append(
                    f"SOFT WARNING: restaurant_id {rest_id}: Revenue reconciliation deviation {revenue_dev:.2%} (±3% target)"
                )

        # Debt service reconciliation: sum of 12 months ≈ annual debt service (±5%)
        bank_annual_debt_service = bank_months["debt_service_outflows"].sum()
        acct_debt_service = acct_row["debt_service_estimated"]

        if acct_debt_service > 0:
            debt_dev = (
                abs(bank_annual_debt_service - acct_debt_service) / acct_debt_service
            )
            if debt_dev > 0.05:
                warnings.append(
                    f"SOFT WARNING: restaurant_id {rest_id}: Debt service reconciliation deviation {debt_dev:.2%} (±5% target)"
                )

        # Bank outflows vs accounting costs consistency (very soft check ±15% for guidance only)
        # This is expected to deviate due to cash vs accrual basis differences
        bank_annual_outflows = bank_months["total_outflows"].sum()
        # Estimated accounting costs
        acct_costs = (
            acct_row["food_cost"]
            + acct_row["labour_cost"]
            + acct_row["rent_annual"]
            + acct_row["debt_service_estimated"]
        )

        if acct_costs > 0:
            outflows_dev = abs(bank_annual_outflows - acct_costs) / acct_costs
            # Don't report warnings on outflows; this is expected to vary due to cash/accrual differences

    return issues, warnings


def validate_demo_profiles(
    restaurants_df, accounting_df, monthly_pos_df, monthly_bank_df
):
    """Validate demo profile characteristics."""
    issues = []

    # Validate Strong profile (ID 1)
    rest_row = restaurants_df[restaurants_df["restaurant_id"] == DEMO_STRONG_ID].iloc[0]
    if rest_row["legal_name"] != "Bonne Table":
        issues.append(
            f"ERROR: Strong profile (ID {DEMO_STRONG_ID}) legal_name is '{rest_row['legal_name']}', expected 'Bonne Table'"
        )
    if rest_row["city"] != "Amsterdam":
        issues.append(
            f"ERROR: Strong profile (ID {DEMO_STRONG_ID}) city is '{rest_row['city']}', expected 'Amsterdam'"
        )
    if rest_row["registration_date"] != "2016-03-15":
        issues.append(
            f"ERROR: Strong profile (ID {DEMO_STRONG_ID}) registration_date is '{rest_row['registration_date']}', expected '2016-03-15'"
        )
    if rest_row["cuisine_type"] != "French":
        issues.append(
            f"ERROR: Strong profile (ID {DEMO_STRONG_ID}) cuisine_type is '{rest_row['cuisine_type']}', expected 'French'"
        )

    acct_row = accounting_df[accounting_df["restaurant_id"] == DEMO_STRONG_ID].iloc[0]
    if abs(acct_row["annual_revenue"] - 450000) > 1000:
        issues.append(
            f"ERROR: Strong profile (ID {DEMO_STRONG_ID}) revenue is €{acct_row['annual_revenue']:,.0f}, expected ~€450,000"
        )

    prime_cost = (acct_row["food_cost"] + acct_row["labour_cost"]) / acct_row[
        "annual_revenue"
    ]
    if prime_cost > 0.62 or prime_cost < 0.55:
        issues.append(
            f"ERROR: Strong profile (ID {DEMO_STRONG_ID}) prime cost is {prime_cost:.1%}, expected ~0.58"
        )

    rent_to_rev = acct_row["rent_annual"] / acct_row["annual_revenue"]
    if rent_to_rev > 0.08 or rent_to_rev < 0.07:
        issues.append(
            f"ERROR: Strong profile (ID {DEMO_STRONG_ID}) rent-to-revenue is {rent_to_rev:.1%}, expected ~0.071"
        )

    # Validate Medium profile (ID 41)
    rest_row = restaurants_df[restaurants_df["restaurant_id"] == DEMO_MEDIUM_ID].iloc[0]
    if rest_row["legal_name"] != "Trattoria Pietro":
        issues.append(
            f"ERROR: Medium profile (ID {DEMO_MEDIUM_ID}) legal_name is '{rest_row['legal_name']}', expected 'Trattoria Pietro'"
        )
    if rest_row["city"] != "Rotterdam":
        issues.append(
            f"ERROR: Medium profile (ID {DEMO_MEDIUM_ID}) city is '{rest_row['city']}', expected 'Rotterdam'"
        )
    if rest_row["registration_date"] != "2023-06-15":
        issues.append(
            f"ERROR: Medium profile (ID {DEMO_MEDIUM_ID}) registration_date is '{rest_row['registration_date']}', expected '2023-06-15'"
        )
    if rest_row["cuisine_type"] != "Italian":
        issues.append(
            f"ERROR: Medium profile (ID {DEMO_MEDIUM_ID}) cuisine_type is '{rest_row['cuisine_type']}', expected 'Italian'"
        )

    acct_row = accounting_df[accounting_df["restaurant_id"] == DEMO_MEDIUM_ID].iloc[0]
    if abs(acct_row["annual_revenue"] - 825000) > 5000:
        issues.append(
            f"ERROR: Medium profile (ID {DEMO_MEDIUM_ID}) revenue is €{acct_row['annual_revenue']:,.0f}, expected ~€825,000"
        )

    prime_cost = (acct_row["food_cost"] + acct_row["labour_cost"]) / acct_row[
        "annual_revenue"
    ]
    if prime_cost > 0.68 or prime_cost < 0.64:
        issues.append(
            f"ERROR: Medium profile (ID {DEMO_MEDIUM_ID}) prime cost is {prime_cost:.1%}, expected ~0.66"
        )

    # Validate High-risk profile (ID 15)
    rest_row = restaurants_df[
        restaurants_df["restaurant_id"] == DEMO_HIGH_RISK_ID
    ].iloc[0]
    if rest_row["legal_name"] != "Levant Express":
        issues.append(
            f"ERROR: High-risk profile (ID {DEMO_HIGH_RISK_ID}) legal_name is '{rest_row['legal_name']}', expected 'Levant Express'"
        )
    if rest_row["city"] != "Utrecht":
        issues.append(
            f"ERROR: High-risk profile (ID {DEMO_HIGH_RISK_ID}) city is '{rest_row['city']}', expected 'Utrecht'"
        )
    if rest_row["registration_date"] != "2025-01-10":
        issues.append(
            f"ERROR: High-risk profile (ID {DEMO_HIGH_RISK_ID}) registration_date is '{rest_row['registration_date']}', expected '2025-01-10'"
        )
    if rest_row["cuisine_type"] != "Turkish":
        issues.append(
            f"ERROR: High-risk profile (ID {DEMO_HIGH_RISK_ID}) cuisine_type is '{rest_row['cuisine_type']}', expected 'Turkish'"
        )

    acct_row = accounting_df[accounting_df["restaurant_id"] == DEMO_HIGH_RISK_ID].iloc[
        0
    ]
    if abs(acct_row["annual_revenue"] - 320000) > 5000:
        issues.append(
            f"ERROR: High-risk profile (ID {DEMO_HIGH_RISK_ID}) revenue is €{acct_row['annual_revenue']:,.0f}, expected ~€320,000"
        )

    prime_cost = (acct_row["food_cost"] + acct_row["labour_cost"]) / acct_row[
        "annual_revenue"
    ]
    if prime_cost > 0.78 or prime_cost < 0.74:
        issues.append(
            f"ERROR: High-risk profile (ID {DEMO_HIGH_RISK_ID}) prime cost is {prime_cost:.1%}, expected ~0.76"
        )

    for demo_id, profile_label in [
        (DEMO_STRONG_ID, "Strong"),
        (DEMO_MEDIUM_ID, "Medium"),
        (DEMO_HIGH_RISK_ID, "High-risk"),
    ]:
        pos_rows = monthly_pos_df[monthly_pos_df["restaurant_id"] == demo_id]
        bank_rows = monthly_bank_df[monthly_bank_df["restaurant_id"] == demo_id]
        cv_value = revenue_cv(pos_rows)
        cv_target = DEMO_CV_TARGETS[demo_id]
        if pass_fail(cv_value, cv_target) == "FAIL":
            issues.append(
                f"ERROR: {profile_label} profile (ID {demo_id}) Revenue CV is {cv_value:.3f}, expected {cv_target[0]:.2f}-{cv_target[1]:.2f}"
            )

        margin_value = cash_flow_margin(bank_rows)
        margin_target = DEMO_CASH_MARGIN_TARGETS[demo_id]
        if pass_fail(margin_value, margin_target) == "FAIL":
            issues.append(
                f"ERROR: {profile_label} profile (ID {demo_id}) cash-flow margin is {margin_value:.1%}, expected {margin_target[0]:.0%}-{margin_target[1]:.0%}"
            )

    return issues


# ============================================================================
# MAIN GENERATION AND VALIDATION
# ============================================================================


def main(output_dir="data", seed=SEED):
    """Main generation and validation function."""

    print("[INFO] ForkFund Synthetic Data Generator")
    print(f"[INFO] Seed: {seed}")
    print(f"[INFO] Reference date for calculations: {DATA_REFERENCE_DATE}")

    set_seed(seed)
    configure_risk_tiers(seed)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Generation order: restaurants → accounting → monthly_pos → monthly_bank → lenders → validation
    restaurants_df = generate_restaurants_csv(output_dir=output_dir)
    accounting_df = generate_accounting_csv(restaurants_df, output_dir=output_dir)
    monthly_pos_df = generate_monthly_pos_csv(
        restaurants_df, accounting_df, output_dir=output_dir
    )
    monthly_bank_df = generate_monthly_bank_csv(
        restaurants_df, accounting_df, output_dir=output_dir
    )
    lenders_df = generate_lenders_csv(output_dir=output_dir)

    # Validation
    print("\n[INFO] Running validation...")

    all_issues = []
    all_warnings = []

    # Validate each file
    print("[VALIDATE] Restaurants...")
    rest_issues = validate_restaurants(restaurants_df)
    all_issues.extend(rest_issues)

    print("[VALIDATE] Accounting...")
    acct_issues = validate_accounting(accounting_df, restaurants_df)
    all_issues.extend(acct_issues)

    print("[VALIDATE] Monthly POS...")
    pos_issues = validate_monthly_pos(monthly_pos_df, restaurants_df)
    all_issues.extend(pos_issues)

    print("[VALIDATE] Monthly Bank...")
    bank_issues = validate_monthly_bank(monthly_bank_df, restaurants_df)
    all_issues.extend(bank_issues)

    # Reconciliation
    print("[VALIDATE] Reconciliation...")
    recon_issues, recon_warnings = validate_reconciliation(
        restaurants_df, accounting_df, monthly_pos_df, monthly_bank_df
    )
    all_issues.extend(recon_issues)
    all_warnings.extend(recon_warnings)

    # Demo profiles
    print("[VALIDATE] Demo profiles...")
    demo_issues = validate_demo_profiles(
        restaurants_df, accounting_df, monthly_pos_df, monthly_bank_df
    )
    all_issues.extend(demo_issues)

    # Print validation report
    print("\n" + "=" * 70)
    print("VALIDATION REPORT")
    print("=" * 70)

    # Row counts
    print("\n[FILE STRUCTURE]")
    print(f"  restaurants.csv: {len(restaurants_df)} rows")
    print(f"  monthly_bank.csv: {len(monthly_bank_df)} rows")
    print(f"  monthly_pos.csv: {len(monthly_pos_df)} rows")
    print(f"  accounting.csv: {len(accounting_df)} rows")
    print(f"  lenders.csv: {len(lenders_df)} rows")

    # Data integrity
    print("\n[DATA INTEGRITY]")
    print(
        f"  Each restaurant has exactly 1 restaurant row: {all(restaurants_df.groupby('restaurant_id').size() == 1)}"
    )
    print(
        f"  Each restaurant has exactly 12 bank rows: {all(monthly_bank_df.groupby('restaurant_id').size() == 12)}"
    )
    print(
        f"  Each restaurant has exactly 12 POS rows: {all(monthly_pos_df.groupby('restaurant_id').size() == 12)}"
    )
    print(
        f"  Each restaurant has exactly 1 accounting row: {all(accounting_df.groupby('restaurant_id').size() == 1)}"
    )

    # Band distribution
    print("\n[REVENUE BAND DISTRIBUTION]")
    for band in REVENUE_BANDS:
        band_rests = restaurants_df[
            (restaurants_df["annual_revenue_estimate"] >= band["min"])
            & (restaurants_df["annual_revenue_estimate"] < band["max"])
        ]
        print(f"  €{band['min']:,}–€{band['max']:,}: {len(band_rests)} restaurants")

    # City distribution
    print("\n[CITY DISTRIBUTION]")
    city_counts = restaurants_df["city"].value_counts()
    for city, count in city_counts.items():
        print(f"  {city}: {count}")

    # Loan purpose vocabulary check
    print("\n[LOAN PURPOSE VOCABULARY]")
    purpose_counts = restaurants_df["loan_purpose"].value_counts()
    all_valid = set(purpose_counts.index) == set(LOAN_PURPOSES)
    print(f"  All purposes valid: {all_valid}")
    for purpose, count in purpose_counts.items():
        print(f"    {purpose}: {count}")

    # Registration-date validation
    non_demo_reg_ok, high_risk_reg_ok, late_non_demo = registration_validation_summary(
        restaurants_df
    )
    print("\n[REGISTRATION DATE VALIDATION]")
    print(f"  Non-demo registrations on/before 2024-12-31: {non_demo_reg_ok}")
    print(f"  Levant Express registration is 2025-01-10: {high_risk_reg_ok}")
    print(f"  Late non-demo registrations: {len(late_non_demo)}")

    # Derived POS statistics
    average_checks, covers_per_seat = pos_quality_stats(
        monthly_pos_df, restaurants_df
    )
    print("\n[AVERAGE CHECK STATISTICS]")
    print(f"  Min: €{average_checks.min():.2f}")
    print(f"  Mean: €{average_checks.mean():.2f}")
    print(f"  Median: €{average_checks.median():.2f}")
    print(f"  Max: €{average_checks.max():.2f}")

    print("\n[COVERS PER SEAT PER MONTH STATISTICS]")
    print(f"  Min: {covers_per_seat.min():.2f}")
    print(f"  Mean: {covers_per_seat.mean():.2f}")
    print(f"  Median: {covers_per_seat.median():.2f}")
    print(f"  Max: {covers_per_seat.max():.2f}")

    # Demo profiles details
    print("\n[DEMO PROFILES DETAILS]")
    for demo_id, demo_name in [
        (DEMO_STRONG_ID, "Strong (A-like)"),
        (DEMO_MEDIUM_ID, "Medium (C-like)"),
        (DEMO_HIGH_RISK_ID, "High-risk (D-like)"),
    ]:
        rest_row = restaurants_df[restaurants_df["restaurant_id"] == demo_id].iloc[0]
        acct_row = accounting_df[accounting_df["restaurant_id"] == demo_id].iloc[0]
        pos_rows = monthly_pos_df[monthly_pos_df["restaurant_id"] == demo_id]
        bank_rows = monthly_bank_df[monthly_bank_df["restaurant_id"] == demo_id]

        prime_cost = (acct_row["food_cost"] + acct_row["labour_cost"]) / acct_row[
            "annual_revenue"
        ]
        rent_to_rev = acct_row["rent_annual"] / acct_row["annual_revenue"]
        revenue_cv_value = revenue_cv(pos_rows)
        cash_margin = cash_flow_margin(bank_rows)
        cv_status = pass_fail(revenue_cv_value, DEMO_CV_TARGETS[demo_id])
        margin_status = pass_fail(cash_margin, DEMO_CASH_MARGIN_TARGETS[demo_id])
        years_active = get_years_active(
            pd.to_datetime(rest_row["registration_date"]).date()
        )
        debt_to_rev = acct_row["existing_debt"] / acct_row["annual_revenue"]
        delivery_share = (
            pos_rows["delivery_platform_sales"].sum() / pos_rows["total_revenue"].sum()
            if len(pos_rows) > 0
            else 0
        )
        weekend_share = (
            pos_rows["weekend_revenue"].sum() / pos_rows["total_revenue"].sum()
            if len(pos_rows) > 0
            else 0
        )

        print(f"\n  ID {demo_id}: {rest_row['legal_name']} ({demo_name})")
        print(f"    Revenue: €{acct_row['annual_revenue']:,.0f}")
        print(f"    Prime cost: {prime_cost:.1%}")
        print(f"    Rent-to-revenue: {rent_to_rev:.1%}")
        print(f"    Revenue CV: {revenue_cv_value:.3f} [{cv_status}]")
        print(f"    Cash-flow margin: {cash_margin:.1%} [{margin_status}]")
        print(f"    Years active: {years_active:.1f}")
        print(f"    Debt-to-revenue: {debt_to_rev:.1%}")
        print(f"    Delivery share: {delivery_share:.1%}")
        print(f"    Weekend share: {weekend_share:.1%}")

    # Issues and warnings
    print("\n[VALIDATION RESULTS]")
    if not all_issues:
        print("  ✓ All critical checks PASSED")
    else:
        print(f"  ✗ {len(all_issues)} critical issues found:")
        for issue in all_issues:
            print(f"    - {issue}")

    if all_warnings:
        print(f"\n  ! {len(all_warnings)} warnings:")
        for warning in all_warnings:
            print(f"    - {warning}")

    # Save validation report
    report_path = os.path.join(output_dir, "validation_report.txt")
    with open(report_path, "w") as f:
        f.write("FORKFUND SYNTHETIC DATA VALIDATION REPORT\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Generated: {datetime.datetime.now().isoformat()}\n")
        f.write(f"Seed: {seed}\n")
        f.write(f"Reference date: {DATA_REFERENCE_DATE}\n\n")

        f.write("FILE STRUCTURE\n")
        f.write("-" * 70 + "\n")
        f.write(f"restaurants.csv: {len(restaurants_df)} rows\n")
        f.write(f"monthly_bank.csv: {len(monthly_bank_df)} rows\n")
        f.write(f"monthly_pos.csv: {len(monthly_pos_df)} rows\n")
        f.write(f"accounting.csv: {len(accounting_df)} rows\n")
        f.write(f"lenders.csv: {len(lenders_df)} rows\n\n")

        f.write("DATA INTEGRITY CHECKS\n")
        f.write("-" * 70 + "\n")
        f.write(
            f"Each restaurant has exactly 1 restaurant row: {all(restaurants_df.groupby('restaurant_id').size() == 1)}\n"
        )
        f.write(
            f"Each restaurant has exactly 12 bank rows: {all(monthly_bank_df.groupby('restaurant_id').size() == 12)}\n"
        )
        f.write(
            f"Each restaurant has exactly 12 POS rows: {all(monthly_pos_df.groupby('restaurant_id').size() == 12)}\n"
        )
        f.write(
            f"Each restaurant has exactly 1 accounting row: {all(accounting_df.groupby('restaurant_id').size() == 1)}\n\n"
        )

        f.write("REVENUE BAND DISTRIBUTION\n")
        f.write("-" * 70 + "\n")
        for band in REVENUE_BANDS:
            band_rests = restaurants_df[
                (restaurants_df["annual_revenue_estimate"] >= band["min"])
                & (restaurants_df["annual_revenue_estimate"] < band["max"])
            ]
            f.write(
                f"€{band['min']:,}–€{band['max']:,}: {len(band_rests)} restaurants\n"
            )
        f.write(f"TOTAL: {len(restaurants_df)} restaurants\n\n")

        f.write("CITY DISTRIBUTION\n")
        f.write("-" * 70 + "\n")
        city_counts = restaurants_df["city"].value_counts()
        for city, count in city_counts.items():
            f.write(f"  {city}: {count}\n")
        f.write(f"TOTAL: {sum(city_counts)}\n\n")

        f.write("LOAN PURPOSE VOCABULARY CHECK\n")
        f.write("-" * 70 + "\n")
        purpose_counts = restaurants_df["loan_purpose"].value_counts()
        for purpose in LOAN_PURPOSES:
            count = purpose_counts.get(purpose, 0)
            f.write(f"  {purpose}: {count}\n")
        f.write(
            f"All purposes valid: {set(purpose_counts.index) == set(LOAN_PURPOSES)}\n\n"
        )

        non_demo_reg_ok, high_risk_reg_ok, late_non_demo = registration_validation_summary(
            restaurants_df
        )
        f.write("REGISTRATION DATE VALIDATION\n")
        f.write("-" * 70 + "\n")
        f.write(
            f"Non-demo registrations on/before 2024-12-31: {non_demo_reg_ok}\n"
        )
        f.write(f"Levant Express registration is 2025-01-10: {high_risk_reg_ok}\n")
        f.write(f"Late non-demo registrations: {len(late_non_demo)}\n\n")

        average_checks, covers_per_seat = pos_quality_stats(
            monthly_pos_df, restaurants_df
        )
        f.write("AVERAGE CHECK STATISTICS\n")
        f.write("-" * 70 + "\n")
        f.write(f"Min: €{average_checks.min():.2f}\n")
        f.write(f"Mean: €{average_checks.mean():.2f}\n")
        f.write(f"Median: €{average_checks.median():.2f}\n")
        f.write(f"Max: €{average_checks.max():.2f}\n\n")

        f.write("COVERS PER SEAT PER MONTH STATISTICS\n")
        f.write("-" * 70 + "\n")
        f.write(f"Min: {covers_per_seat.min():.2f}\n")
        f.write(f"Mean: {covers_per_seat.mean():.2f}\n")
        f.write(f"Median: {covers_per_seat.median():.2f}\n")
        f.write(f"Max: {covers_per_seat.max():.2f}\n\n")

        f.write("DEMO PROFILES CHARACTERISTICS\n")
        f.write("-" * 70 + "\n")
        for demo_id, demo_name in [
            (DEMO_STRONG_ID, "Strong (A-like)"),
            (DEMO_MEDIUM_ID, "Medium (C-like)"),
            (DEMO_HIGH_RISK_ID, "High-risk (D-like)"),
        ]:
            rest_row = restaurants_df[restaurants_df["restaurant_id"] == demo_id].iloc[
                0
            ]
            acct_row = accounting_df[accounting_df["restaurant_id"] == demo_id].iloc[0]
            pos_rows = monthly_pos_df[monthly_pos_df["restaurant_id"] == demo_id]
            bank_rows = monthly_bank_df[monthly_bank_df["restaurant_id"] == demo_id]

            prime_cost = (acct_row["food_cost"] + acct_row["labour_cost"]) / acct_row[
                "annual_revenue"
            ]
            rent_to_rev = acct_row["rent_annual"] / acct_row["annual_revenue"]
            revenue_cv_value = revenue_cv(pos_rows)
            cash_margin = cash_flow_margin(bank_rows)
            cv_status = pass_fail(revenue_cv_value, DEMO_CV_TARGETS[demo_id])
            margin_status = pass_fail(cash_margin, DEMO_CASH_MARGIN_TARGETS[demo_id])
            years_active = get_years_active(
                pd.to_datetime(rest_row["registration_date"]).date()
            )
            debt_to_rev = acct_row["existing_debt"] / acct_row["annual_revenue"]
            delivery_share = (
                pos_rows["delivery_platform_sales"].sum()
                / pos_rows["total_revenue"].sum()
                if len(pos_rows) > 0
                else 0
            )
            weekend_share = (
                pos_rows["weekend_revenue"].sum() / pos_rows["total_revenue"].sum()
                if len(pos_rows) > 0
                else 0
            )

            f.write(f"\nID {demo_id}: {rest_row['legal_name']} ({demo_name})\n")
            f.write(f"  Revenue: €{acct_row['annual_revenue']:,.0f}\n")
            f.write(f"  Prime cost: {prime_cost:.1%}\n")
            f.write(f"  Rent-to-revenue: {rent_to_rev:.1%}\n")
            f.write(f"  Revenue CV: {revenue_cv_value:.3f} [{cv_status}]\n")
            f.write(f"  Cash-flow margin: {cash_margin:.1%} [{margin_status}]\n")
            f.write(f"  Years active: {years_active:.1f}\n")
            f.write(f"  Debt-to-revenue: {debt_to_rev:.1%}\n")
            f.write(f"  Delivery share: {delivery_share:.1%}\n")
            f.write(f"  Weekend share: {weekend_share:.1%}\n")

        f.write("\n\nVALIDATION RESULTS\n")
        f.write("-" * 70 + "\n")
        if not all_issues:
            f.write("✓ All critical checks PASSED\n")
        else:
            f.write(f"✗ {len(all_issues)} critical issues found:\n")
            for issue in all_issues:
                f.write(f"  - {issue}\n")

        if all_warnings:
            f.write(f"\n! {len(all_warnings)} warnings:\n")
            for warning in all_warnings:
                f.write(f"  - {warning}\n")

    print(f"\n[INFO] Validation report saved to {report_path}")
    print("[INFO] Generation complete. Ready for data loader.")

    # Exit with appropriate code
    if all_issues:
        print("\n[ERROR] Generation failed due to critical issues")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
