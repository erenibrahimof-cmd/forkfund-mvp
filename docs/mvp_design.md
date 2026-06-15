# ForkFund — MVP Design Document
### The Credit Passport for Restaurant Finance

**Eren Ibrahimof Berke (633021) · Sarah Laik (654939)**
RSM FinTech: Business Models and Applications · June 2026

---

**Purpose of this document.** This document is the Step 0 design specification agreed before implementation. It fixes the user flow, the core versus optional feature set, the data fields, the rules-based scoring logic, the application pages, and an explicit statement of what is deliberately not implemented. It is grounded in how Dutch restaurant lending actually works, so that the simulated MVP mirrors a realistic production system.

---

## 1. Grounding: how Dutch restaurant lending actually works

The design mirrors two real lending tiers in the Netherlands, because ForkFund's Credit Passport must be useful to both.

- **Traditional bank loans:** usually larger tickets, lower interest rates, and a more document-heavy process. Lenders often require annual accounts, recent bank statements, investment plans, forecasts, and an overview of existing financing obligations.
- **Alternative and fintech lenders:** usually smaller tickets, faster decisions, and more reliance on recent bank-transaction data and turnover patterns. Hard requirements are often practical: a valid KvK number, a business active for at least 12 months, Dutch business registration, and sufficient recent revenue.

**Design implication.** The primary signal in modern restaurant lending is the recent transaction stream. Bank and POS data show whether a restaurant has stable revenue, sufficient cash inflow, and operational consistency. Accounting data is useful, but in the MVP it is treated as an enhancer rather than a gate. This matches ForkFund's role as a pre-underwriting layer: it standardises credit-relevant restaurant data before the lender performs final checks.

Because hospitality is viewed as higher-risk, lenders may still require collateral, personal guarantees, owner identity checks, iDIN verification, and BKR checks. These steps sit after ForkFund's pre-screening and remain the lender's responsibility. ForkFund therefore does not make the final lending decision; it improves the quality, comparability, and speed of the lender's screening process.

---

## 2. Why ForkFund is restaurant-specific

ForkFund does not narrow its market to restaurants because generic SME lending is impossible. It narrows the market because restaurants have credit-relevant operating signals that generic SME lenders do not standardise well. These include food-cost pressure, labour intensity, prime cost, rent-to-revenue pressure, table utilisation, average check, revenue per available seat hour, delivery-platform dependency, cash/card consistency, and seasonal demand patterns.

This is the core reason why ForkFund can create value as a vertical fintech platform. A generic SME score can assess turnover, cash flow, debt, and business age. A restaurant-specific Credit Passport can additionally explain whether the restaurant's operating model is healthy. For example, two restaurants may have the same revenue, but very different credit risk if one has high prime cost, high rent pressure, weak table utilisation, and heavy dependence on delivery platforms.

**Design implication.** The MVP scoring model combines standard cash-flow lending logic with a restaurant-specific operating-risk layer. This makes the product defensible as restaurant credit infrastructure rather than a generic SME dashboard.

---

## 3. The user flow

The MVP follows a single linear journey across two actors. The restaurant builds a Passport; the lender consumes it.

| Step | Action |
|------|--------|
| 1 | Restaurant enters its details. Identity is auto-filled through a simulated KvK lookup, while the loan request is entered manually. |
| 2 | Restaurant connects financial data sources: bank, POS, and accounting. In the MVP these are simulated by loading mock data per source. |
| 3 | The system standardises the data, runs the rules-based scoring engine, and generates the Restaurant Credit Passport. |
| 4 | The lender opens the dashboard and sees the pool of qualified restaurant profiles. |
| 5 | The lender filters by grade, loan size, purpose, city, and restaurant-specific operating indicators, then opens an individual Passport to review the detail. |

In one line:

> Restaurant owner → enters details → connects/selects mock financial data → receives Credit Passport → lender views dashboard → lender filters and opens the Passport.

---

## 4. Core versus optional features

Core features are the ones that implement the full multi-party flow and should work well in the final demo. Optional features are only added if time allows.

### Core features

| Core feature | Description |
|--------------|-------------|
| Restaurant onboarding/input | Simulated KvK identity lookup plus manual loan request. |
| Mock/sample financial data | Per-source connect steps for bank, POS, and accounting data. |
| Rules-based scoring engine | Deterministic, explainable model defined in Section 6. |
| Credit Passport generation | Score, grade, peer context, written drivers, and financing-readiness explanation. |
| Lender dashboard | Filterable pool of restaurants with openable individual Passports. |

### Optional features

| Optional feature | Description |
|------------------|-------------|
| Charts/visualisations | Revenue trend, sub-score bars, and peer-percentile indicators. |
| Lender express-interest button | A button recording lender interest, without creating a real offer. |
| Monitoring dashboard | Post-funding metric tracking as a future revenue stream. |
| Synthetic-data generator | Scripted, seeded generator for a larger restaurant population. |
| Login simulation | Toggle between restaurant and lender roles. |

---

## 5. Data fields and their source

Every field is tagged with where it would come from in a real production system. **E** marks fields that are essential to scoring or lender filtering. **N** marks useful but non-essential context.

### Bucket A: Identity and registration

*Production source: KvK API. MVP source: simulated lookup auto-fill.*

| Field | E/N | Used for |
|-------|-----|----------|
| KvK number | E | Lookup key and lender verification. |
| Legal name | E | Passport identity. |
| Registration date | E | Business maturity score. |
| City | E | Lender location filter. |
| Legal form | N | Lender context. |
| SBI code | N | Confirms restaurant sector. |

### Bucket B: Financing request

*Production source: manual restaurant input. MVP source: manual restaurant input.*

| Field | E/N | Used for |
|-------|-----|----------|
| Requested loan amount | E | Lender minimum/maximum filter and repayment-capacity context. |
| Loan purpose | E | Lender purpose filter. |
| Seats/capacity | E | Restaurant-specific utilisation metrics. |
| Opening hours | E | RevPASH and operating-capacity context. |
| Cuisine type | N | Passport context and peer grouping. |

The loan-purpose vocabulary is fixed to avoid empty lender matches: **Term loan, Working capital, Equipment, Renovation.**

### Bucket C: Financial and operating data

*Production source: PSD2/open banking, POS, and accounting APIs. MVP source: per-source simulated connect buttons that load mock data.*

| Source | Fields | Feeds |
|--------|--------|-------|
| Bank / PSD2 | Monthly inflows, monthly outflows, ending balance, debt-service outflows, cash deposits. | Cash-flow strength, debt burden, cash/card consistency, data completeness. |
| POS | Monthly revenue, covers, average check, card/cash split, delivery-platform sales, weekend revenue share. | Revenue stability, POS demand quality, seasonality, concentration risk. |
| Accounting | Annual revenue, food cost, labour cost, rent, EBITDA, existing debt, net profit. | Prime cost efficiency, rent pressure, repayment capacity, debt burden. |

Bank and POS data cover 12 monthly observations. Accounting data covers one to two annual years. Connections are independent: if a source is skipped, the Passport still generates but data completeness declines.

### Bucket D: Computed by the system

The system computes the following variables:

- 0–100 composite score
- A–E grade
- Low, medium, or high risk band
- Nine sub-scores
- EBITDA margin
- Food-cost ratio
- Labour-cost ratio
- Prime-cost ratio
- Rent-to-revenue ratio
- Debt-to-revenue ratio
- RevPASH
- Table-turnover proxy
- Delivery-platform dependency
- Weekend/seasonality dependency
- Cash/card consistency flag
- Data-completeness percentage
- Written explanation and key risk drivers
- Peer percentile within the same revenue band

---

## 6. Scoring logic: rules-based and restaurant-specific

Consistent with the business plan, the MVP uses a transparent rules-based model, not a predictive AI credit model. ForkFund does not yet have repayment-performance history, so a deterministic model is more honest and more credible for lenders.

The model is hybrid:

- the **score** is calculated against fixed benchmarks and remains fully explainable;
- the **peer percentile** is shown as context and is not part of the score.

### 6.1 Composite score

The composite score is a weighted average of nine sub-scores. Each sub-score is measured from 0 to 100.

$$\text{Score} = \sum_{i=1}^{9} w_i s_i, \qquad \sum_{i=1}^{9} w_i = 1$$

| Dimension | Weight | Benchmark logic | Rationale |
|-----------|--------|-----------------|-----------|
| Data completeness and verification | 0.10 | Connected sources / total possible sources. | More verified data increases lender confidence. |
| Revenue stability | 0.125 | Based on coefficient of variation of monthly revenue. | Stable turnover supports repayment reliability. |
| Cash-flow strength | 0.15 | Net cash inflow margin compared with a 30% target. | Cash flow is the primary signal for debt service. |
| Debt burden and repayment capacity | 0.15 | Combination of debt-to-revenue and estimated annual debt service coverage. | Existing obligations reduce capacity for new borrowing. |
| Prime cost efficiency | 0.15 | Food cost plus labour cost as a share of revenue. | Prime cost is a central restaurant profitability indicator. |
| Rent / occupancy pressure | 0.10 | Rent-to-revenue ratio compared with a target range. | High fixed occupancy cost increases downside risk. |
| POS demand quality | 0.10 | Covers, average check, table-turnover proxy, and RevPASH. | Shows whether revenue comes from healthy restaurant demand. |
| Seasonality and concentration risk | 0.075 | Weekend revenue share, delivery-platform share, and monthly volatility. | Overdependence on peaks or platforms creates fragility. |
| Business maturity | 0.05 | Years active, capped at 10 years. | Many lenders prefer at least 12 months of operating history. |

The weighting deliberately gives substantial importance to restaurant-specific operating signals. Prime cost, rent pressure, POS demand quality, and seasonality/concentration together account for **42.5%** of the score. This makes the Credit Passport visibly restaurant-specific while still retaining general lender logic around cash flow, debt, maturity, and data completeness.

### 6.2 Sub-score formulas

The MVP uses simple formulas that are transparent and easy to explain in the video.

**1. Data completeness and verification**

$$s_1 = 100 \times \frac{\text{number of connected sources}}{3}$$

The three sources are bank, POS, and accounting data.

**2. Revenue stability**

$$CV_{\text{revenue}} = \frac{\sigma(\text{monthly revenue})}{\mu(\text{monthly revenue})}$$

$$s_2 = \max\left(0,\ \min\left(100,\ 100 \times (1 - CV_{\text{revenue}})\right)\right)$$

A lower coefficient of variation means more stable monthly revenue.

**3. Cash-flow strength**

$$\text{Net cash inflow margin} = \frac{\text{bank inflows} - \text{bank outflows}}{\text{bank inflows}}$$

$$s_3 = \max\left(0,\ \min\left(100,\ 100 \times \frac{\text{net cash inflow margin}}{0.30}\right)\right)$$

The benchmark target is 30%. Values above the target are capped at 100.

**4. Debt burden and repayment capacity**

$$\text{Debt-to-revenue} = \frac{\text{existing debt}}{\text{annual revenue}}$$

$$s_{4a} = 100 \times (1 - \min(\text{debt-to-revenue},\ 1))$$

$$\text{DSCR proxy} = \frac{\text{EBITDA}}{\text{estimated annual debt service}}$$

$$s_{4b} = \max\left(0,\ \min\left(100,\ 100 \times \frac{\text{DSCR proxy}}{1.50}\right)\right)$$

$$s_4 = 0.5\,s_{4a} + 0.5\,s_{4b}$$

If debt service is unavailable, the model uses the debt-to-revenue component and assigns a neutral value of 50 to the missing DSCR component.

**5. Prime cost efficiency**

$$\text{Prime cost ratio} = \frac{\text{food cost} + \text{labour cost}}{\text{annual revenue}}$$

$$s_5 = \begin{cases}
100 & \text{if prime cost ratio} \leq 0.60 \\
75  & \text{if } 0.60 < \text{prime cost ratio} \leq 0.65 \\
50  & \text{if } 0.65 < \text{prime cost ratio} \leq 0.70 \\
25  & \text{if } 0.70 < \text{prime cost ratio} \leq 0.80 \\
0   & \text{if prime cost ratio} > 0.80
\end{cases}$$

This is one of the most important restaurant-specific signals.

**6. Rent / occupancy pressure**

$$\text{Rent-to-revenue ratio} = \frac{\text{annual rent}}{\text{annual revenue}}$$

$$s_6 = \begin{cases}
100 & \text{if rent-to-revenue} \leq 0.08 \\
80  & \text{if } 0.08 < \text{rent-to-revenue} \leq 0.10 \\
60  & \text{if } 0.10 < \text{rent-to-revenue} \leq 0.12 \\
30  & \text{if } 0.12 < \text{rent-to-revenue} \leq 0.15 \\
0   & \text{if rent-to-revenue} > 0.15
\end{cases}$$

High rent pressure is treated as a major fixed-cost risk.

**7. POS demand quality**

The scoring engine uses three independent POS demand indicators with equal weight:

$$s_7 = \tfrac{1}{3}\,s_{\text{avg check}} + \tfrac{1}{3}\,s_{\text{table turnover}} + \tfrac{1}{3}\,s_{\text{RevPASH}}$$

where:

$$\text{RevPASH} = \frac{\text{monthly revenue}}{\text{number of seats} \times \text{opening hours per month}}$$

The original design listed four components including a raw-covers volume metric (covers\_per\_seat\_month × seats). Covers volume is omitted because it is nearly perfectly correlated with the table-turnover proxy within any revenue band — both are derived from the same monthly covers count. Three independent signals (revenue quality per customer, seat utilisation, seat-hour productivity) avoid redundancy while preserving the restaurant-specific character of the dimension.

Each component is scored as the restaurant's population percentile rank (0–100) within the 80-restaurant pre-loaded dataset.

**8. Seasonality and concentration risk**

$$s_8 = 0.4\,s_{\text{seasonality}} + 0.3\,s_{\text{delivery dependency}} + 0.3\,s_{\text{weekend dependency}}$$

The risk flags are:

- high revenue seasonality;
- high delivery-platform share;
- high weekend revenue dependency.

For the MVP, the score is reduced when:

- the coefficient of variation of monthly revenue is high;
- delivery-platform revenue exceeds 35% of total revenue;
- weekend revenue exceeds 60% of total revenue.

The three components use the following step-function thresholds as implemented in `src/scorer.py`:

| Revenue CV | *s*_seasonality |
|---|---|
| ≤ 0.10 | 100 |
| ≤ 0.15 | 75 |
| ≤ 0.20 | 50 |
| ≤ 0.30 | 25 |
| > 0.30 | 0 |

| Delivery share | *s*_delivery |
|---|---|
| ≤ 15% | 100 |
| ≤ 25% | 75 |
| ≤ 35% | 50 |
| ≤ 45% | 25 |
| > 45% | 0 |

| Weekend share | *s*_weekend |
|---|---|
| ≤ 45% | 100 |
| ≤ 55% | 75 |
| ≤ 60% | 50 |
| ≤ 70% | 25 |
| > 70% | 0 |

**9. Business maturity**

$$s_9 = \min\left(100,\ 100 \times \frac{\text{years active}}{10}\right)$$

Restaurants active for less than one year are flagged as below common lender eligibility standards.

### 6.3 Missing data rule

Missing inputs do not break the Passport. If a dimension cannot be fully calculated because a data source is not connected, the missing component receives a neutral score of 50. The lower data-completeness score then reflects the reduced confidence in the assessment. This allows the MVP to demonstrate graceful degradation instead of blocking the user.

### 6.4 Grade and risk bands

| Score | Grade | Risk band | Meaning |
|-------|-------|-----------|---------|
| 85–100 | A | Low risk | Strong restaurant credit profile. |
| 70–84 | B | Low-to-medium risk | Finance-ready with minor weaknesses. |
| 55–69 | C | Medium risk | Possible borrower, but needs lender review. |
| 40–54 | D | High risk | Weak profile or major risk flags. |
| 0–39 | E | Very high risk | Not finance-ready in current form. |

### 6.5 Written explanation

For every dimension, the engine emits a short written driver: positive, neutral, or flagged risk. Example drivers include:

- *Positive: Monthly revenue is stable and supports predictable repayment capacity.*
- *Positive: Prime cost is within the healthy restaurant benchmark range.*
- *Neutral: Accounting data is missing, so repayment capacity is estimated with lower confidence.*
- *Risk flag: Rent-to-revenue is high, creating fixed-cost pressure.*
- *Risk flag: Delivery-platform dependency is high, which may reduce margin and increase concentration risk.*

The score is labelled throughout as **pre-underwriting decision support**, not a final lending decision.

---

## 7. Application pages

| Page | Purpose |
|------|---------|
| Home / concept overview | Introduces the problem, ForkFund's Credit Passport idea, and the demo navigation. |
| Restaurant onboarding | Simulated KvK lookup, manual loan request, and mock data connections for bank, POS, and accounting data. |
| Credit Passport | Generated profile with score, grade, peer context, sub-scores, restaurant-specific operating signals, completeness, and written drivers. |
| Lender dashboard | Filterable pool of qualified restaurants. Lenders can filter by city, loan amount, purpose, grade, data completeness, and restaurant-specific risk indicators. |
| Methodology / About | Explains the scoring model, benchmarks, MVP scope, and what is deliberately not implemented. |

---

## 8. What is deliberately not implemented

The MVP states these boundaries honestly in the Methodology page and in the video. These are not gaps in the concept; they are the documented boundary of an academic MVP.

- **No real PSD2/open-banking connection:** bank data is simulated. In production, this would use a licensed account-information provider.
- **No live KvK API:** identity is a simulated lookup over synthetic records. In production, this would connect to the KvK API.
- **No live POS/accounting integrations:** these are represented through mock data behind a connect step.
- **No real lender offers or money movement:** the marketplace surfaces and filters profiles; it does not originate loans, hold funds, or transmit investor orders.
- **No owner identity, iDIN, or BKR credit check:** these remain the lender's step after pre-screening.
- **No production-grade security or persistence:** the MVP does not include authentication hardening, database persistence, audit logs, or GDPR-grade access controls.
- **No predictive default model:** scoring is rules-based and explainable by design, not a trained AI credit model.

---

## 9. Implementation contract

This design is the contract for the build. Implementation proceeds one component at a time against these decisions. Any major deviation updates this document first.

The implementation order is:

1. Create the public GitHub repository and initial documentation.
2. Add `prompt.md`, `README.md`, and `AGENTS.md`.
3. Build the Streamlit app skeleton.
4. Add synthetic restaurant, bank, POS, and accounting data.
5. Implement the rules-based scoring engine.
6. Implement the Restaurant Credit Passport page.
7. Implement the lender dashboard and filters.
8. Add methodology documentation and final video demo script.
