# Synthetic Data Generation Plan

**Purpose:** This document outlines the strategy for the future synthetic data generation script (`scripts/generate_synthetic_data.py`). It defines the approach, constraints, and validation logic that will power the ForkFund MVP's realistic and reproducible restaurant dataset.

**Status:** Plan — awaiting approval before implementation.

---

## 1. File Structure and Fixed Random Seed

### Output directory structure
```
data/
├── restaurants.csv          (80 rows; 1 per restaurant)
├── monthly_bank.csv         (960 rows; 12 per restaurant)
├── monthly_pos.csv          (960 rows; 12 per restaurant)
├── accounting.csv           (80 rows; 1 per restaurant)
└── lenders.csv              (5–10 rows; reference file)
```

### Fixed random seed
- **Seed value:** `seed=42` (or configurable via CLI argument)
- **Applied to:** Python's `random` module for standard randomization; pandas' `random_state` parameter for dataframe sampling; ensures reproducible results across all randomization sources
- **Purpose:** Reproducibility; running the script twice with the same seed produces identical CSVs
- **Documentation:** The seed will be logged to console and documented in README.md and code comments

### Output format
- **File format:** CSV (comma-separated values)
- **Character encoding:** UTF-8
- **Date format:** ISO 8601 (YYYY-MM-DD for dates; YYYY-MM for periods)
- **Currency:** EUR; decimal separator `.` (e.g., 1000.50, not 1000,50)
- **Integers:** No thousand separators
- **Floating-point precision:** 2 decimal places for currency; up to 4 for ratios

---

## 2. Dependencies

### Current dependencies (from `requirements.txt`)
The script will use only:
- Python standard library (`random`, `datetime`, `csv`, `math`)
- **pandas** (already in requirements.txt)

### Additional dependencies needed
- **None.** The script will not require new packages beyond what is already in `requirements.txt`. It will use pandas and Python standard library only.
- No numpy required; random number generation will use Python's `random` module and pandas' built-in randomisation.
- If additional packages become necessary in the future, `requirements.txt` will be explicitly updated.

---

## 3. Restaurant Generation: 80 Total across Four Revenue Bands

### Revenue band distribution

| Revenue band | Annual revenue range | Restaurant count | Characteristics |
|--------------|---------------------|-------------------|-----------------|
| **Band 1** | €0–500k | 20 | Small neighbourhood restaurants, casual/quick-service, limited seats (20–60) |
| **Band 2** | €500k–1M | 25 | Mid-size suburban and city restaurants, mixed concepts, moderate seats (50–100) |
| **Band 3** | €1M–1.5M | 20 | Larger established restaurants, quality focus, more seats (80–150) |
| **Band 4** | €1.5M+ | 15 | Premium and high-volume restaurants, established brands, larger capacity (120–200) |
| **Total** | — | **80** | Distributed across Dutch cities with realistic proportions |

### Restaurant ID assignment
- Sequential `restaurant_id` from 1 to 80
- Distribution order: Band 1 (1–20), Band 2 (21–45), Band 3 (46–65), Band 4 (66–80)
- Three target demo profiles placed strategically:
  - Strong (A-like): restaurant_id = 1 (Band 1, €450k)
  - Medium-risk (C-like): restaurant_id = 41 (Band 2, €825k)
  - High-risk (D-like): restaurant_id = 15 (Band 1, €320k) — both strong and high-risk are in Band 1 to represent different risk profiles within the same peer group

### Within each band: annual revenue sampling
- **Band 1 (€0–500k):** Random uniform distribution within range; sample mean ~€300k
- **Band 2 (€500k–1M):** Random uniform distribution; sample mean ~€750k
- **Band 3 (€1M–1.5M):** Random uniform distribution; sample mean ~€1.25M
- **Band 4 (€1.5M+):** Random uniform distribution (€1.5M–€2.5M range); sample mean ~€2M
- Each restaurant's annual_revenue_estimate becomes the source of truth for its revenue band

---

## 4. City Distribution

**Primary cities (60–70% of restaurants):**
- Amsterdam (18 restaurants)
- Rotterdam (12 restaurants)
- Utrecht (10 restaurants)
- The Hague (8 restaurants)
- Eindhoven (8 restaurants)

**Secondary cities (30–40% of restaurants):**
- Groningen (6 restaurants)
- Breda (6 restaurants)
- Maastricht (5 restaurants)
- Arnhem (4 restaurants)
- Dordrecht (3 restaurants)

**Total:** 18 + 12 + 10 + 8 + 8 + 6 + 6 + 5 + 4 + 3 = **80 restaurants**

### City assignment algorithm
- Distribute restaurants across cities such that:
  - Major cities (Amsterdam, Rotterdam) have mix of all revenue bands
  - Smaller cities have mix but skewed toward Bands 1–2
  - No city has zero restaurants
- Use weighted random sampling to match distribution above

### Cuisine type distribution
- Informational field; no scoring impact
- Variety: Italian (15–20 restaurants), French (8–10), Asian (10–12), Dutch (8–10), Mediterranean (8–10), Turkish (5–7), Spanish (4–6), fusion (3–5), vegetarian (2–3), fine-dining (2–3)
- Vary by city realism (Amsterdam more diverse, smaller towns more traditional)

---

## 5. Monthly Bank Data Generation (12 rows per restaurant)

### Monthly structure
- **Year:** 2025 (fixed for MVP)
- **Months:** January (2025-01) through December (2025-12)
- **Rows per restaurant:** 12 monthly aggregates
- **Total rows:** 80 × 12 = 960 rows in `monthly_bank.csv`

### Column generation strategy

#### `total_inflows` (monthly deposits/income)
- **Derivation:** Anchor to annual_revenue_estimate / 12 (monthly baseline)
- **Variation:** Apply monthly seasonal pattern (e.g., December +15%, February −10%) and random noise (±5% daily variation)
- **Range:** Typically €5k–€20k per month for Band 1; €50k–€200k+ for Band 4
- **Realistic:** Seasonal peaks (summer, December), troughs (January, August)

#### `total_outflows` (expenses and withdrawals)
- **Constraint:** Typically 60–85% of inflows (depending on restaurant profile)
- **Derivation:** For each restaurant, pick a target outflow ratio (60%, 70%, 80%, or 85% depending on profile)
  - Strong profile (A-like): 65% outflows (healthy cash retention)
  - Medium-risk (C-like): 75% outflows
  - High-risk (D-like): 85% outflows (thin margins)
  - Typical: 70–75%
- **Variation:** Monthly noise (±3% around the target ratio)
- **Formula:** `total_outflows = total_inflows × target_ratio × (1 + random_noise)`

#### `cash_deposits` and `card_deposits` (payment method split)
- **Constraint:** `cash_deposits + card_deposits ≈ total_inflows` (within ±2%)
- **Derivation:** Decide cash/card split ratio per restaurant (e.g., 20% cash, 80% card for modern city restaurant; 35% cash, 65% card for traditional)
  - Band 1: 25–40% cash (more traditional)
  - Band 2: 20–35% cash (mixed)
  - Band 3: 15–30% cash (more modern)
  - Band 4: 10–25% cash (premium, mostly card)
  - Vary slightly by month (±3%)
- **Formula:** `cash_deposits = total_inflows × cash_ratio; card_deposits = total_inflows × (1 − cash_ratio)`

#### `debt_service_outflows` (monthly debt payments)
- **Derivation:** Anchor to accounting.existing_debt from the annual accounting file
  - If existing_debt = €0: debt_service_outflows = €0
  - If existing_debt > €0: debt_service_outflows = accounting.debt_service_estimated / 12
- **Typical:** 2–5% of monthly inflows for restaurants with debt
- **Stability:** Constant across all 12 months (debt service is fixed obligation)
- **Reconciliation:** Sum of 12 months = accounting.debt_service_estimated (annually)

#### `ending_balance` (month-end account balance)
- **Derivation:** Running balance tracking
  - Month 1: starting_balance + inflows − outflows (starting_balance ~€10k–€50k)
  - Month N: previous_month_balance + inflows − outflows
  - Apply realistic fluctuations (some months more positive, others draw down)
- **Range:** Typically €5k–€100k (working capital; never below €2k to avoid insolvency)
- **Realism:** Balance fluctuates month-to-month but trend is stable for healthy restaurants; declining for struggling restaurants

### Seasonal and variability patterns
- **Q4 (Oct–Dec):** Inflows +10–20% (holiday season boost)
- **Q1 (Jan–Mar):** Inflows −10% to +5% (post-holiday slowdown, recovery)
- **Summer (Jul–Aug):** Inflows −5–10% (vacation season, reduced foot traffic)
- **Noise:** Add ±2–5% random daily-level variation to smooth month-to-month transitions
- **Consistency:** The three demo profiles will show distinct patterns (strong: stable, medium: moderate volatility, high-risk: high volatility and tight margins)

---

## 6. Monthly POS Data Generation (12 rows per restaurant)

### Monthly structure
- **Year:** 2025 (fixed)
- **Months:** January through December
- **Rows per restaurant:** 12 monthly aggregates
- **Total rows:** 80 × 12 = 960 rows in `monthly_pos.csv`

### Column generation strategy

#### `total_revenue` (monthly sales)
- **Anchor:** annual_revenue_estimate / 12 (baseline per month)
- **Seasonality:** Apply same seasonal pattern as bank inflows (Q4 +15%, Q1 −10%, summer −5%, etc.)
- **Variation:** ±3–5% random daily noise
- **Reconciliation:** Sum of 12 months ≈ accounting.annual_revenue (within ±3%)

#### `covers` (customer count)
- **Derivation:** Derived from total_revenue and target average_check for the restaurant
  - Formula: `covers = total_revenue / average_check` (monthly covers)
  - **Not freely chosen:** Covers are computed; they must be consistent with revenue and average check
- **Validation after generation:** Ensure resulting covers produce realistic restaurant utilization (customers per seat per month)
  - Typical: 10–15 covers per seat per month
  - Example: 55-seat restaurant, €37.5k monthly revenue, €110 average check → 341 covers/month → 6.2 covers/seat/month (realistic)
- **Range (as derived):** Band 1: 200–500/month; Band 4: 1500–3000/month

#### `average_check` (revenue per customer)
- **Derivation:** Generator assigns target average_check based on concept and revenue band, then validates total_revenue / covers results in this range
- **Formula:** `average_check = total_revenue / covers`
- **Authoritative:** This is a **formula**, not freely chosen. It must be consistent with revenue and covers after generation.
- **Target ranges by concept:**
  - Casual/quick-service: €40–€65
  - Mid-range: €65–€100
  - Premium: €100–€150
  - Fine dining: €120–€200
- **Validation:** After generating revenue and covers, verify average_check = revenue/covers falls in expected range; adjust if needed
- **Realism:** Higher average checks correlate with higher revenue bands and premium concepts; lower checks with volume/casual concepts

#### `card_sales` and `cash_sales` (payment method split)
- **Constraint:** `card_sales + cash_sales ≈ total_revenue` (within ±1%)
- **Derivation:** Use same cash/card ratio as bank deposits (consistency)
  - Formula: `cash_sales = total_revenue × cash_ratio; card_sales = total_revenue × (1 − cash_ratio)`
- **Reconciliation:** monthly_pos.card_sales + monthly_pos.cash_sales should approximately match monthly_bank.card_deposits + monthly_bank.cash_deposits (typically very close)

#### `delivery_platform_sales` (third-party delivery revenue)
- **Derivation:** Random sample from 0–40% of total_revenue, depending on restaurant and month
  - Small urban restaurants: higher delivery share (20–35%)
  - Suburban/premium: lower delivery share (5–20%)
  - Demo high-risk profile: 35–40% (concentration risk)
  - Demo strong profile: 5–15% (balanced channels)
- **Monthly variation:** ±3% around restaurant's target share
- **Risk flag:** >35% triggers concentration-risk flag in scoring

#### `dine_in_sales` (on-premise revenue)
- **Derivation:** total_revenue − delivery_platform_sales (approximately; some variance for rounding)
- **Constraint:** dine_in_sales + delivery_platform_sales ≈ total_revenue (within ±1%, allowing for rounding)

#### `weekend_revenue` and `weekday_revenue` (temporal split)
- **Weekend:** Friday–Sunday (3 days); typically 40–55% of monthly revenue for most restaurants
  - Demo strong: 40–45% (balanced week and weekend)
  - Demo medium: 48–55% (slight weekend bias)
  - Demo high-risk: 60–70% (high weekend dependency, concentration risk)
- **Weekday:** Monday–Thursday (4 days); remainder of revenue
- **Constraint:** weekend_revenue + weekday_revenue ≈ total_revenue (exactly or near-exactly)
- **Risk flag:** >60% weekend share triggers seasonality risk in scoring

### Realistic ranges for POS indicators
- **Covers per month:** Derived from total_revenue and average_check; ensure resulting average_check falls in realistic range (€40–€150)
  - Band 1 typical: 250–500 covers/month
  - Band 2 typical: 600–1300 covers/month
  - Band 3 typical: 1000–2200 covers/month
  - Band 4 typical: 2000–3800 covers/month
- **Average check:** €40–€150 (varies by concept; higher for premium)
  - Casual/quick-service: €40–€65
  - Mid-range: €65–€100
  - Premium: €100–€150
  - Fine-dining: €120–€200
- **Consistency requirement:** After generating covers and total_revenue, validate that average_check = total_revenue / covers falls in expected range; adjust if needed
- **Delivery share:** 5–40% (higher for urban; lower for fine dining)
- **Weekend share:** 40–70% (higher for casual; lower for business-lunch establishments)
- **Card share:** 65–90% (modern restaurants); cash share 10–35% (traditional)

---

## 7. Annual Accounting Data Generation (1 row per restaurant)

### Annual structure
- **Year:** 2025 (fixed for MVP)
- **Rows per restaurant:** 1 annual aggregate
- **Total rows:** 80 rows in `accounting.csv`

### Column generation strategy

#### `annual_revenue` (baseline for all restaurants)
- **Source:** Copy annual_revenue_estimate from restaurants.csv
- **Reconciliation:** Should approximately equal sum of 12 monthly_pos.total_revenue rows (within ±3%)

#### `food_cost` (COGS for food and beverages)
- **Derivation:** Decide food-cost ratio per restaurant (typically 25–35% of revenue)
  - Demo strong (A-like): 28–30% (efficient)
  - Demo medium (C-like): 30–33% (borderline)
  - Demo high-risk (D-like): 33–36% (pressure)
  - Typical distribution: 25–35% across portfolio
- **Formula:** `food_cost = annual_revenue × food_cost_ratio`
- **Variation:** ±2% around target ratio

#### `labour_cost` (wages, payroll taxes, benefits)
- **Derivation:** Decide labour-cost ratio per restaurant (typically 30–40% of revenue)
  - Demo strong: 30–32% (efficient scheduling)
  - Demo medium: 32–35% (standard)
  - Demo high-risk: 35–40% (high labour pressure)
  - Typical: 30–35% across portfolio
- **Formula:** `labour_cost = annual_revenue × labour_cost_ratio`
- **Note:** Labour cost + food cost = prime cost; target ≤0.65 for good score, >0.70 for warning

#### `rent_annual` (annual rent/lease payments)
- **Derivation:** Decide rent-to-revenue ratio per restaurant (typically 8–15% of revenue)
  - Demo strong (A-like): 7–8% (low occupancy pressure)
  - Demo medium (C-like): 10–12% (caution zone)
  - Demo high-risk (D-like): 13–15% (high pressure)
  - Typical: 8–14% across portfolio (high rent in central Amsterdam; lower in suburbs)
- **Formula:** `rent_annual = annual_revenue × rent_ratio`
- **Variation:** ±2% around target ratio
- **City variation:** Amsterdam restaurants skew higher (10–14%); suburbs lower (7–10%)

#### `ebitda` (Earnings before interest, tax, depreciation, amortisation)
- **Derivation:** Set a target EBITDA margin first, then compute EBITDA from it.
- **Formula:** `ebitda = annual_revenue × target_ebitda_margin`
- **Target EBITDA margins** (determined by restaurant profile and band):
  - Demo strong: 13% (healthy operations)
  - Demo medium: 8% (adequate)
  - Demo high-risk: 3% (very tight)
  - Typical across portfolio: 2–18%
- **Internal back-solve** (for validation only; not stored in CSV):
  - `other_operating_costs = annual_revenue − food_cost − labour_cost − rent_annual − ebitda`
  - This residual represents supplies, utilities, marketing, maintenance, insurance, and other overhead
- **Why this approach:** Ensures EBITDA margin targets are met, preventing logical contradictions between costs and profitability

#### `net_profit` (net income after tax)
- **Derivation:** EBITDA − depreciation − interest − taxes
- **Assumption:** Net profit ≈ EBITDA × 0.7–0.8 (tax rate ~20%, depreciation and interest ≤10% of EBITDA)
- **Formula:** `net_profit = ebitda × 0.75` (rough approximation)
- **Typical range:** 2–12% of revenue
  - Demo strong: 10–12%
  - Demo medium: 5–7%
  - Demo high-risk: <2% or negative

#### `existing_debt` (outstanding borrowing)
- **Derivation:** Random; depends on restaurant profile and band
  - Band 1: 10–30% of annual_revenue (small loans or no debt)
  - Band 2: 20–50% of annual_revenue (mixed)
  - Band 3: 30–60% of annual_revenue (larger operations, more debt)
  - Band 4: 25–70% of annual_revenue (variable)
  - Demo strong: 5–15% (minimal debt)
  - Demo medium: 30–40% (moderate debt)
  - Demo high-risk: 50–80% (high leverage)
- **Formula:** `existing_debt = annual_revenue × debt_ratio`
- **Zero debt:** Allowed; 15–20% of restaurants have existing_debt = 0

#### `debt_service_estimated` (annual debt service)
- **Derivation:** If existing_debt = 0: debt_service_estimated = 0
  - If existing_debt > 0: estimate annual debt service
  - Assumption: typical restaurant loan at 4–6% interest, 5-year amortisation
  - Rough approximation: debt_service_estimated ≈ existing_debt × 0.22 (or exact from amortisation formula)
- **Formula:** `debt_service_estimated = existing_debt × 0.22` (for 5-year term, 5% interest)
- **Reconciliation:** monthly_bank.debt_service_outflows × 12 ≈ debt_service_estimated (within ±5%)

### Prime cost and rent ratios (validation targets)

**Prime cost ratio = (food_cost + labour_cost) / annual_revenue**
- Target for good score: ≤0.60
- Warning zone: 0.65–0.70
- Danger zone: >0.80
- Generation strategy: Distribute across these zones
  - 40% of restaurants: ≤0.63 (good)
  - 35% of restaurants: 0.63–0.70 (caution)
  - 20% of restaurants: 0.70–0.78 (warning)
  - 5% of restaurants: >0.78 (danger)

**Rent-to-revenue ratio = rent_annual / annual_revenue**
- Target for good score: ≤0.08
- Warning zone: 0.10–0.15
- Danger zone: >0.15
- Generation strategy: Distribute
  - 30% of restaurants: ≤0.08 (good)
  - 45% of restaurants: 0.08–0.12 (typical)
  - 20% of restaurants: 0.12–0.15 (high pressure)
  - 5% of restaurants: >0.15 (very high pressure)

---

## 8. Lender Data Generation (5–10 rows)

### Lender structure
- **Rows:** 5–10 lender profiles (simple reference file; not part of scoring)
- **Purpose:** Dashboard support; lenders filter by their criteria

### Generation strategy

**Lender 1:** Major traditional bank (e.g., ING)
- min_loan_amount: €50,000
- max_loan_amount: €500,000
- focus_city: null (nationwide)
- preferred_loan_purposes: "Term loan, Working capital"

**Lender 2:** Alternative fintech (smaller tickets)
- min_loan_amount: €10,000
- max_loan_amount: €200,000
- focus_city: null
- preferred_loan_purposes: "Working capital, Equipment"

**Lender 3:** Regional bank
- min_loan_amount: €25,000
- max_loan_amount: €300,000
- focus_city: Amsterdam
- preferred_loan_purposes: "Term loan, Renovation"

**Additional lenders (4–10):** Similar variety with different focus cities and loan ranges

### Realistic ranges
- **Min loan:** €10k–€50k
- **Max loan:** €200k–€500k
- **Loan purpose vocabulary (fixed):** "Term loan", "Working capital", "Equipment", "Renovation"

---

## 9. Coherence Constraints and Reconciliation

The script will enforce the following consistency checks during generation and output validation reports:

### 1. Annual-to-monthly revenue reconciliation
- **Constraint:** Sum of monthly_pos.total_revenue (12 rows) ≈ accounting.annual_revenue
- **Tolerance:** Within ±3% (allow for rounding)
- **How enforced:** After generating monthly data, sum across 12 months; if deviation >±3%, apply scaling factor to monthly rows to match annual total

### 2. Bank inflows vs. payment method split
- **Constraint:** cash_deposits + card_deposits ≈ total_inflows
- **Tolerance:** Within ±2%
- **How enforced:** After generating both columns, check sum; adjust card_deposits if needed to match inflows exactly

### 3. POS revenue vs. payment method split
- **Constraint:** card_sales + cash_sales ≈ total_revenue
- **Tolerance:** Within ±1%
- **How enforced:** After generating both, check sum; scale both proportionally if needed

### 4. POS revenue vs. delivery/dine-in split
- **Constraint:** dine_in_sales + delivery_platform_sales ≈ total_revenue
- **Tolerance:** Within ±1%
- **How enforced:** Derive dine_in_sales = total_revenue − delivery_platform_sales; validate post-generation

### 5. POS revenue vs. weekday/weekend split
- **Constraint:** weekday_revenue + weekend_revenue ≈ total_revenue
- **Tolerance:** Exactly equal (no tolerance; derived field)
- **How enforced:** After generating weekend_revenue, compute weekday_revenue = total_revenue − weekend_revenue

### 6. Bank debt service vs. accounting annual service
- **Constraint:** Sum of 12 monthly_bank.debt_service_outflows ≈ accounting.debt_service_estimated
- **Tolerance:** Within ±5% (allow for rounding)
- **How enforced:** Set monthly_bank.debt_service_outflows = accounting.debt_service_estimated / 12 (exact); reconciliation is automatic

### 7. Restaurant profile consistency
- **Constraint:** annual_revenue_estimate (restaurants.csv) should match annual_revenue (accounting.csv)
- **How enforced:** Both derived from same source; copy value directly

### Validation function outputs
After generation, the script will emit:
- **Reconciliation report:** For each restaurant, show:
  - Annual revenue (accounting) vs. sum of monthly POS revenue
  - Annual debt service vs. sum of monthly bank debt service
  - Payment method totals (cash + card vs. total)
  - Deviation percentages and pass/fail status
- **Summary statistics:** Across all 80 restaurants:
  - Mean and stddev of prime cost ratios
  - Mean and stddev of rent-to-revenue ratios
  - Distribution of revenue bands
  - Count of restaurants with zero debt
  - Count of restaurants by city
  - Count by cuisine type

---

## 10. Three Target Demo Profiles

The script will hardcode three special restaurants designed to approximate A, C, and D scores when the scoring engine runs:

### Profile 1: Strong / Target A-grade (`restaurant_id=1`, "Bonne Table", Amsterdam)

**Identity:**
- City: Amsterdam
- Seats: 55
- Opening hours/day: 11.5
- Cuisine: French
- Registration: 2016 (9 years active; mature)
- Requested loan: €100,000
- Loan purpose: "Term loan"

**Operations (strong characteristics):**
- annual_revenue: €450,000 (Band 1, upper end)
- annual_revenue_estimate: €450,000
- food_cost: €126,000 (28% — efficient)
- labour_cost: €135,000 (30% — efficient)
- prime_cost_ratio: 0.58 (good, <0.60)
- rent_annual: €32,000 (7.1% — excellent)
- existing_debt: €45,000 (10% of revenue — minimal)
- debt_service_estimated: €9,900 (0.22 × 45k)
- ebitda_margin: 13–15% (healthy)

**Monthly patterns (12 months, 2025):**
- Revenue stable and consistent; low CV (~0.08)
- Seasonal variation moderate (+10% summer, −5% Jan)
- Monthly revenue baseline: €450,000 / 12 ≈ €37,500/month (with seasonal variation)
- Cash inflows: avg ~€37,500/month; outflows ~€25,000/month (67% ratio; reflects strong cash retention)
- Cash/card split: 20% cash, 80% card (modern)
- Delivery share: 8% (low; mostly dine-in)
- Weekend share: 42% (balanced week/weekend)
- Covers: derived as total_revenue / average_check; should be ~310–420 monthly covers (realistic for 55-seat restaurant with 1.5–2 turns/day weekday, 2.5–3 turns weekend)
- Average check: approximately €110–€125 (food + beverage average)

**Expected score:** 85–95 (A-grade)

### Profile 2: Medium-risk / Target C-grade (`restaurant_id=41`, "Trattoria Pietro", Rotterdam)

**Identity:**
- City: Rotterdam
- Seats: 78
- Opening hours/day: 11
- Cuisine: Italian
- Registration: 2023 (2 years active; young)
- Requested loan: €150,000
- Loan purpose: "Working capital"

**Operations (medium-risk characteristics):**
- annual_revenue: €825,000 (Band 2, mid-range)
- annual_revenue_estimate: €825,000
- food_cost: €264,000 (32% — borderline)
- labour_cost: €280,000 (34% — borderline)
- prime_cost_ratio: 0.66 (caution, 0.65–0.70)
- rent_annual: €96,000 (11.6% — caution zone)
- existing_debt: €330,000 (40% of revenue — moderate)
- debt_service_estimated: €72,600 (0.22 × 330k)
- ebitda_margin: 8–10% (adequate)

**Monthly patterns (12 months, 2025):**
- Revenue moderate volatility; CV ~0.12
- Seasonal variation moderate (+8% Q4, −8% Q1)
- Monthly revenue baseline: €825,000 / 12 ≈ €68,750/month (with seasonal variation)
- Cash inflows: avg ~€68,750/month; outflows ~€51,500/month (75% ratio; reflects moderate cash retention)
- Cash/card split: 28% cash, 72% card (mixed)
- Delivery share: 28% (moderate; multi-channel)
- Weekend share: 52% (slight weekend bias)
- Covers: derived as total_revenue / average_check; should be ~600–850 monthly covers (realistic for 78-seat restaurant with 1.5–2 turns/day weekday, 2.5–3 turns weekend)
- Average check: approximately €75–€95 (mid-range restaurant)

**Expected score:** 55–70 (C-grade)

### Profile 3: High-risk / Target D-grade (`restaurant_id=15`, "Levant Express", Utrecht)

**Identity:**
- City: Utrecht
- Seats: 40
- Opening hours/day: 11
- Cuisine: Turkish
- Registration: 2025-01-10 (0 years — very new; opened January 2025)
- Requested loan: €80,000
- Loan purpose: "Equipment"

**Operations (high-risk characteristics):**
- annual_revenue: €320,000 (Band 1, lower end)
- annual_revenue_estimate: €320,000
- food_cost: €115,000 (36% — high)
- labour_cost: €128,000 (40% — high)
- prime_cost_ratio: 0.76 (warning, 0.70–0.80)
- rent_annual: €44,800 (14% — high pressure; just below danger zone threshold of 0.15)
- existing_debt: €200,000 (62.5% of revenue — high leverage)
- debt_service_estimated: €44,000 (0.22 × 200k)
- target_ebitda_margin: 0.03 (3% — very tight; generates ~€9,600 EBITDA)

**Monthly patterns (12 months, 2025):**
- Revenue high volatility; CV ~0.18 (unstable; typical for new restaurant)
- Seasonal variation high (+15% summer, −15% Jan)
- Monthly revenue baseline: €320,000 / 12 ≈ €26,700/month (with seasonal variation)
- Cash inflows: avg ~€26,700/month; outflows ~€22,700/month (85% ratio — thin margins)
- Cash/card split: 35% cash, 65% card (traditional)
- Delivery share: 38% (high; concentration risk flag >35%)
- Weekend share: 65% (high weekend dependency; concentration risk flag >60%)
- Covers: derived as total_revenue / average_check; should be ~250–350 monthly covers (realistic for 40-seat restaurant with stretched capacity and 1.5–2 turns/day)
- Average check: approximately €75–€90 (casual quick-service)
- Ending balance sometimes drops to €3k–€5k (stress; new restaurant with thin working capital buffer)

**Expected score:** 40–54 (D-grade)

**Note on ID placement:** restaurant_id = 15 places this restaurant in Band 1 (ID range 1–20), same as the strong profile. This is intentional: both profiles operate in the same revenue band (€0–500k) but represent opposite risk profiles within that peer group. The strong profile demonstrates successful operations; the high-risk profile shows an undercapitalised, newly opened restaurant struggling with high leverage and cost pressure.

---

## 11. Value Ranges and Realistic Data

The script will use these ranges to ensure generated data is realistic:

### Operating metrics
| Metric | Min | Typical | Max | Notes |
|--------|-----|---------|-----|-------|
| Average check (€) | €35 | €60–€120 | €180 | Casual: €40–€60; premium: €100–€150 |
| Seats | 20 | 60–100 | 200 | Neighbourhood: 20–60; established: 80–150; premium: 120–200 |
| Opening hours/day | 9.5 | 11 | 14 | Typically 10–12 hours |
| Covers/month | 150 | 600–1200 | 3500 | Depends on seats and turnover |

### Financial ratios
| Metric | Min | Target | Warning | Danger | Notes |
|--------|-----|--------|---------|--------|-------|
| Prime cost ratio | 0.52 | ≤0.63 | 0.65–0.70 | >0.78 | (food + labour) / revenue |
| Rent-to-revenue | 0.06 | ≤0.08 | 0.10–0.15 | >0.15 | Fixed occupancy pressure |
| EBITDA margin | 2% | 8–12% | 5–8% | <2% | Operational profitability |
| Debt-to-revenue | 0% | 25–40% | 40–60% | >80% | Leverage |
| Cash/card split | 10% cash | 20–30% cash | 35% cash | 45% cash | Payment method preference |
| Delivery share | 0% | 8–20% | 25–35% | 40%+ | Concentration risk (>35% flag) |
| Weekend share | 35% | 40–50% | 52–60% | 65%+ | Seasonality risk (>60% flag) |
| Outflows as % inflows | 60% | 70–75% | 80–85% | 90%+ | Cash margin health |

### Monthly and annual patterns
- **Seasonality:** Q4 +10–20%, Q1 −5–10%, summer −5–10%
- **Monthly noise:** ±2–5% random variation around seasonal pattern
- **Ending balance:** €3k–€100k (restaurants never drop below €2k in generated data)
- **Debt service:** Fixed across 12 months (monthly = annual / 12)

---

## 12. Validation Functions

The script will include internal validation logic to ensure data quality:

### Function 1: `validate_restaurant_profile(restaurant_row)`
- Check: restaurant_id is unique
- Check: city is in list of valid Dutch cities
- Check: loan_purpose is one of four fixed values
- Check: registration_date is on or before reference date 2025-12-31 (allows newly opened restaurants in 2025)
- Check: seats, opening_hours_per_day are in realistic ranges
- Check: annual_revenue_estimate is assigned to correct revenue band
- Output: Pass/fail with reason

### Function 2: `validate_monthly_bank(monthly_bank_rows)`
- Check: 12 rows per restaurant (no gaps or duplicates)
- Check: period values are consecutive months in 2025
- Check: total_inflows > 0
- Check: total_outflows > 0 and < total_inflows (healthy)
- Check: cash_deposits + card_deposits ≈ total_inflows (within ±2%)
- Check: ending_balance > 0 (never insolvent)
- Check: debt_service_outflows is constant across 12 months
- Output: Per-restaurant report

### Function 3: `validate_monthly_pos(monthly_pos_rows)`
- Check: 12 rows per restaurant
- Check: period values are consecutive months in 2025
- Check: total_revenue > 0
- Check: covers > 0
- Check: card_sales + cash_sales ≈ total_revenue (within ±1%)
- Check: dine_in_sales + delivery_platform_sales ≈ total_revenue (within ±1%)
- Check: weekend_revenue + weekday_revenue ≈ total_revenue
- Check: delivery_platform_sales / total_revenue ≤ 0.50 (no nonsense data)
- Check: average_check (total_revenue / covers) is in realistic range (€30–€180)
- Output: Per-restaurant report

### Function 4: `validate_accounting(accounting_rows)`
- Check: 1 row per restaurant
- Check: year = 2025
- Check: annual_revenue > 0
- Check: food_cost, labour_cost, rent_annual > 0
- Check: food_cost / annual_revenue in range 0.20–0.40
- Check: labour_cost / annual_revenue in range 0.25–0.45
- Check: rent_annual / annual_revenue in range 0.06–0.18
- Check: ebitda > 0 (mostly; allow rare exceptions for high-risk profile)
- Check: ebitda_margin (ebitda / annual_revenue) is in expected range for restaurant (typically 0.02–0.18)
- Check: net_profit > 0 or close to 0 (rarely negative in MVP)
- Check: existing_debt ≥ 0
- Check: debt_service_estimated = 0 if existing_debt = 0; else > 0
- Output: Per-restaurant report

### Function 5: `validate_reconciliation(restaurants, monthly_bank, monthly_pos, accounting)`
- Check: annual_revenue (accounting) ≈ sum of 12 monthly_pos.total_revenue (within ±3%)
- Check: debt_service_estimated (accounting) ≈ sum of 12 monthly_bank.debt_service_outflows (within ±5%)
- Check: annual_revenue_estimate (restaurants) = annual_revenue (accounting)
- Check: annual accounting cash outflows (food + labour + rent + debt service, using implied other_operating_costs) roughly align with sum of 12 monthly_bank.total_outflows (soft consistency; allow ±10% for monthly variation)
- Output: Per-restaurant report showing deviations; overall summary

### Function 6: `validate_demo_profiles(restaurants, accounting, monthly_bank, monthly_pos)`
- Check: restaurant_id=1 has demo_profile="strong" and looks A-like
- Check: restaurant_id=41 has demo_profile="medium" and looks C-like
- Check: restaurant_id=15 has demo_profile="high_risk" and looks D-like
- Check: Exactly 3 restaurants marked with demo_profile (not null)
- Output: Pass/fail with details on each demo profile's characteristics

### Function 7: `validate_lenders(lenders_rows)`
- Check: 5–10 rows
- Check: lender_id is unique
- Check: min_loan_amount < max_loan_amount
- Check: preferred_loan_purposes contains only fixed vocabulary
- Output: Pass/fail

### Validation output
- Run all validation functions at end of generation
- Print **validation report** to console and (optionally) to `data/validation_report.txt`
- Format: Summary of passes, any warnings, and critical failures (script exits with error if critical failures)

---

## 13. Explicitly Out of Scope

The following will **NOT** be implemented in the synthetic data generation script:

- **No multi-year data:** Only 2025 data; no historical time series or trends
- **No real KvK API integration:** All kvk_number values are synthetic
- **No real lender offers:** Lender profiles are static reference data; no real terms or pricing
- **No owner/identity details:** No founder names, personal contact info, or identity verification flags
- **No transaction-level detail:** Only monthly aggregates; no daily or per-transaction records
- **No branch/location detail:** Each restaurant_id represents one legal entity
- **No performance history:** These are first-time loan requests; no historical repayment data
- **No real bank/POS system exports:** All data is synthesised from first principles
- **No computed scores or grades:** The script generates raw inputs only; scoring runs at load time in the app
- **No data-completeness flags in CSV:** data_available columns are not stored; computed at load time based on presence of rows
- **No predictive model:** Synthetic data is deterministic and rule-based; no machine learning
- **No production-grade security or encryption:** CSVs are plain text; no access controls in the MVP

---

## 14. Implementation Strategy and File Organization

### Script file structure
```
scripts/
├── generate_synthetic_data.py       (main script; ~500–700 lines)
├── __init__.py                      (empty; marks as package)
└── (optional) data_generator.py    (helper functions; extracted if needed for readability)
```

### Script sections
1. **Imports and config** (lines 1–30)
   - `import pandas, random, datetime, csv, os, math`
   - Define constants: `SEED=42`, `DATA_REFERENCE_DATE=2025-12-31`, cities list, cuisine types, revenue bands, demo profile IDs, etc.

2. **Utility functions** (lines 30–150)
   - `set_seed(seed)` — Initialize random state
   - `generate_kvk_number()` — Synthetic 8-digit string
   - `generate_restaurant_name()` — Realistic names
   - `generate_date(start, end)` — Random date in range
   - `clamp(value, min, max)` — Enforce ranges
   - Helper functions for seasonal patterns, noise, etc.

3. **Restaurant generation** (lines 150–250)
   - `generate_restaurants_csv(n=80)` — Create 80 rows; iterate through bands and cities; mark demo profiles
   - Output: DataFrame → `restaurants.csv`

4. **Annual accounting generation** (lines 250–400)
   - `generate_accounting_csv(restaurants_df)` — 1 row per restaurant
   - Logic: food/labour/rent ratios per profile, ebitda, debt and debt service
   - **Important:** Must run before monthly_bank generation because monthly_bank uses `accounting.debt_service_estimated`
   - Output: DataFrame → `accounting.csv`

5. **Monthly POS data generation** (lines 400–550)
   - `generate_monthly_pos_csv(restaurants_df)` — 12 rows per restaurant
   - Logic: revenue anchor and seasonal variation, covers derivation, payment splits, delivery/dine-in, weekend/weekday
   - Output: DataFrame → `monthly_pos.csv`

6. **Monthly bank data generation** (lines 550–700)
   - `generate_monthly_bank_csv(restaurants_df, accounting_df)` — 12 rows per restaurant
   - Logic: inflows anchor, outflows ratio, cash/card split, debt service from accounting.debt_service_estimated, ending balance tracking
   - **Important:** Depends on accounting_df to retrieve debt_service_estimated
   - Output: DataFrame → `monthly_bank.csv`

7. **Lender reference generation** (lines 700–750)
   - `generate_lenders_csv()` — 5–10 rows
   - Static lender profiles with min/max ranges and purpose focus
   - Output: DataFrame → `lenders.csv`

8. **Validation and reconciliation** (lines 750–900)
   - Call all validation functions (see Section 12)
   - Emit validation report
   - Return exit code 0 if all pass; 1 if critical failures

9. **Main and CLI** (lines 900–950)
   - `if __name__ == "__main__":`
   - Optional `--seed` argument to override default seed
   - Optional `--output-dir` to specify output location (default: `data/`)
   - Call generation functions in sequence
   - Save CSVs to `data/` directory
   - Print summary statistics and validation report to console

### Example CLI usage
```bash
# Generate with default seed (42)
python scripts/generate_synthetic_data.py

# Generate with custom seed
python scripts/generate_synthetic_data.py --seed 123

# Generate to custom directory
python scripts/generate_synthetic_data.py --output-dir /tmp/forkfund_data
```

---

## 15. Expected Output

Upon successful execution, the script will produce:

### CSV files
- `data/restaurants.csv` — 80 rows
- `data/monthly_bank.csv` — 960 rows
- `data/monthly_pos.csv` — 960 rows
- `data/accounting.csv` — 80 rows
- `data/lenders.csv` — 5–10 rows

### Console output
```
[INFO] ForkFund Synthetic Data Generator
[INFO] Seed: 42
[INFO] Generating 80 restaurants...
[INFO]   Band 1 (€0–500k): 20 restaurants
[INFO]   Band 2 (€500k–1M): 25 restaurants
[INFO]   Band 3 (€1M–1.5M): 20 restaurants
[INFO]   Band 4 (€1.5M+): 15 restaurants
[INFO] Generating annual accounting data (80 rows)...
[INFO] Generating monthly POS data (12 months × 80 = 960 rows)...
[INFO] Generating monthly bank data (12 months × 80 = 960 rows)...
[INFO] Generating lender reference data (8 rows)...
[INFO] Running validation...
[PASS] Restaurant profile validation: 80/80 passed
[PASS] Monthly bank validation: 80/80 passed
[PASS] Monthly POS validation: 80/80 passed
[PASS] Accounting validation: 80/80 passed
[PASS] Reconciliation validation: 80/80 passed
[PASS] Demo profile validation: 3/3 passed
[PASS] Lender validation: 8/8 passed
[INFO] Summary statistics:
  - Mean prime cost ratio: 0.664
  - Mean rent-to-revenue: 0.105
  - Restaurants with zero debt: 18 (22%)
  - Cities: 10 (Amsterdam: 18, Rotterdam: 12, ...)
  - Cuisines: 9 (Italian: 15, French: 8, ...)
[INFO] Output files:
  - data/restaurants.csv (80 rows)
  - data/monthly_bank.csv (960 rows)
  - data/monthly_pos.csv (960 rows)
  - data/accounting.csv (80 rows)
  - data/lenders.csv (8 rows)
[INFO] Generation complete. Ready for data loader.
```

### Optional validation report file
- `data/validation_report.txt` — Detailed per-restaurant validation results (optional; can be printed to console instead)

---

## Approval Checklist

Use this checklist to verify that the plan is ready before code implementation begins:

### Strategy and scope
- [ ] **Revenue band distribution locked:** 80 restaurants across €0–500k (20), €500k–1M (25), €1M–1.5M (20), €1.5M+ (15)?
- [ ] **City distribution defined:** 8–10 Dutch cities with realistic proportions (Amsterdam, Rotterdam, Utrecht, The Hague, Eindhoven, Groningen, Breda, Maastricht, Arnhem, etc.)?
- [ ] **Fixed seed strategy clear:** Seed=42 for reproducibility; user-overridable via CLI argument?
- [ ] **Demo profiles defined:** Restaurant_id 1 (strong/A), 41 (medium/C), 15 (high-risk/D); both 1 and 15 in Band 1 representing different risk profiles?
- [ ] **Out-of-scope list clear:** No multi-year data, no real APIs, no scores/grades in CSV, no identity verification, etc.?

### Data files and structure
- [ ] **Five CSV files specified:** restaurants.csv (80 rows), monthly_bank.csv (960 rows), monthly_pos.csv (960 rows), accounting.csv (80 rows), lenders.csv (5–10 rows)?
- [ ] **Output directory structure clear:** `data/` folder with five CSV files?
- [ ] **Column mappings documented:** All columns in each file listed with data types and examples?
- [ ] **Raw vs. computed fields clear:** CSV stores raw inputs only; derived fields computed at load time (average_check, prime_cost_ratio, revenue_cv, RevPASH, etc.)?

### Data coherence
- [ ] **Annual-to-monthly reconciliation:** accounting.annual_revenue ≈ sum of 12 monthly_pos.total_revenue (within ±3%)?
- [ ] **Bank inflows vs. payment split:** cash_deposits + card_deposits ≈ total_inflows (within ±2%)?
- [ ] **POS revenue vs. payment split:** card_sales + cash_sales ≈ total_revenue (within ±1%)?
- [ ] **POS revenue vs. channel split:** dine_in_sales + delivery_platform_sales ≈ total_revenue (within ±1%)?
- [ ] **POS revenue vs. temporal split:** weekday_revenue + weekend_revenue ≈ total_revenue?
- [ ] **Debt service reconciliation:** sum of 12 monthly_bank.debt_service_outflows ≈ accounting.debt_service_estimated (within ±5%)?

### Financial metrics and ranges
- [ ] **Average check realistic:** €40–€150 depending on concept?
- [ ] **Seats realistic:** 20–200?
- [ ] **Opening hours realistic:** 9.5–14 hours/day?
- [ ] **Prime cost distribution:** ~40% good (≤0.63), 35% caution (0.63–0.70), 20% warning (0.70–0.78), 5% danger (>0.78)?
- [ ] **Rent-to-revenue distribution:** ~30% good (≤0.08), 45% typical (0.08–0.12), 20% high (0.12–0.15), 5% very high (>0.15)?
- [ ] **EBITDA margins realistic:** 2–18% (strong: 12–15%, medium: 7–10%, high-risk: 2–5%)?
- [ ] **Cash/card split realistic:** 10–45% cash depending on profile?
- [ ] **Delivery share realistic:** 0–40% (>35% triggers risk flag)?
- [ ] **Weekend share realistic:** 35–70% (>60% triggers risk flag)?
- [ ] **Outflows as % of inflows:** 60–85% depending on profile?

### Demo profiles
- [ ] **Strong profile (ID=1, A-like) defined:**
  - Prime cost ≤0.60?
  - Rent-to-revenue ≤0.08?
  - Revenue stable (low CV)?
  - Cash flow >30% margin?
  - Debt <15% of revenue?
  - Low seasonality/delivery risk?
- [ ] **Medium-risk profile (ID=41, C-like) defined:**
  - Prime cost 0.65–0.70?
  - Rent-to-revenue 0.10–0.12?
  - Revenue moderate volatility?
  - Cash flow 20–30% margin?
  - Debt 30–50% of revenue?
  - Moderate seasonality/delivery risk?
- [ ] **High-risk profile (ID=15, D-like) defined:**
  - Prime cost 0.70–0.78?
  - Rent-to-revenue around 0.14 (high pressure, below danger threshold)?
  - Revenue high volatility?
  - Cash flow <15% margin?
  - Debt 50–80% of revenue?
  - High seasonality/delivery/weekend risk (>60%)?
  - Very new (opened January 2025; 0 years of operating history)?

### Validation logic
- [ ] **Data reference date fixed:** Reference date = 2025-12-31 for reproducible years-active calculations?
- [ ] **Validation functions specified:** 7 validation functions (restaurant profile, monthly bank, monthly POS, accounting, reconciliation, demo profiles, lenders)?
- [ ] **Validation output defined:** Pass/fail per restaurant; summary statistics; critical failure exits with error code 1?
- [ ] **Reconciliation tolerance defined:** ±3% for annual revenue, ±5% for debt service, ±2% for payment splits, ±1% for POS splits, ±10% for accounting-to-bank outflows consistency?
- [ ] **Covers and average check:** Treated as derived, not freely chosen; consistency validated after generation?

### Implementation readiness
- [ ] **Dependencies confirmed:** Only pandas + Python standard library (random, datetime, csv, os, math); no numpy, no new packages?
- [ ] **Script structure outlined:** 9 sections (imports, utilities, restaurants, monthly_bank, monthly_pos, accounting, lenders, validation, main)?
- [ ] **CLI arguments specified:** `--seed` (override default), `--output-dir` (override `data/` default)?
- [ ] **Expected output described:** CSV files + console summary + optional validation report?
- [ ] **No code written yet:** Plan only; awaiting approval before implementation?

### Sign-off
- [ ] All checklist items verified
- [ ] Plan is ready for code implementation

---

**Next step:** Once this plan is approved (all checklist items checked), implementation can proceed to write `scripts/generate_synthetic_data.py`.
