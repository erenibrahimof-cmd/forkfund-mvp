# ForkFund MVP Prompt

Build a working MVP for ForkFund, a B2B Restaurant Credit Passport and lender dashboard for Dutch restaurant financing.

ForkFund helps restaurants become finance-ready by turning fragmented restaurant data into a standardised, explainable Credit Passport. It helps professional lenders screen restaurant borrowers faster by showing verified business information, mock financial data, restaurant-specific operating metrics, a rules-based score, and written risk drivers.

## Source of truth

The authoritative specification is `docs/mvp_design.md`.

This prompt is a summary for project context. If this prompt and `docs/mvp_design.md` ever conflict, follow `docs/mvp_design.md`, especially for:

* scoring dimensions
* scoring weights
* formulas
* grade bands
* data fields
* MVP boundaries
* implementation order

## Core MVP flow

The MVP should implement the full multi-party flow:

Restaurant owner → enters business details → connects/selects mock financial data → receives Restaurant Credit Passport → lender views dashboard → lender filters and opens the Passport.

## Core features

1. Restaurant onboarding/input

   * Simulated KvK lookup
   * Manual loan request
   * Restaurant details such as city, business age, seats, opening hours, cuisine type, requested loan amount, and loan purpose

2. Mock financial data connection

   * Simulated bank / PSD2 data
   * Simulated POS data
   * Simulated accounting data
   * Each connected source contributes to the data-completeness score
   * The Passport should still generate if one source is missing, but with lower data confidence

3. Rules-based scoring engine

   * Deterministic and explainable
   * No predictive AI credit model
   * 0–100 composite score
   * A–E grade
   * Low / medium / high risk band
   * Sub-scores and written drivers explaining the score

4. Restaurant-specific Credit Passport

   * Business identity
   * Financing request
   * Revenue and cash-flow indicators
   * Restaurant-specific metrics such as prime cost, food-cost ratio, labour-cost ratio, rent-to-revenue, RevPASH, table-turnover proxy, delivery-platform dependency, weekend dependency, and cash/card consistency
   * Data completeness
   * Peer context within a comparable restaurant revenue band

5. Lender dashboard

   * Filterable pool of restaurant profiles
   * Filters for city, grade, loan amount, loan purpose, data completeness, and restaurant-specific risk indicators
   * Ability to open an individual Restaurant Credit Passport

## Scoring model

The score should follow `docs/mvp_design.md` and use nine dimensions:

1. Data completeness and verification
2. Revenue stability
3. Cash-flow strength
4. Debt burden and repayment capacity
5. Prime cost efficiency
6. Rent / occupancy pressure
7. POS demand quality
8. Seasonality and concentration risk
9. Business maturity

The model should remain rules-based and transparent. It should not estimate default probability and should not claim to be a trained credit-risk model.

## Shared vocabulary

Loan purposes must use this fixed vocabulary to avoid empty dashboard matches:

* Term loan
* Working capital
* Equipment
* Renovation

Lender filters should use the same vocabulary.

## Synthetic data scope

Use synthetic data only.

The synthetic data should be realistic enough to demonstrate the product:

* approximately 80 restaurant profiles, so peer percentiles within revenue bands are meaningful
* fixed random seed for reproducibility
* restaurants across multiple Dutch cities
* restaurants across different revenue bands
* a few demo-ready restaurants with clearly different profiles, such as strong, medium-risk, and high-risk examples
* synthetic bank, POS, and accounting fields that support the scoring model

Do not use real restaurant data.

Before creating synthetic data files, first propose the data schema and wait for human approval.

## Application pages

The app should contain:

1. Home / concept overview
2. Restaurant onboarding
3. Credit Passport
4. Lender dashboard
5. Methodology / About

## Technology stack

Use a simple Python-based MVP stack:

* Python
* Streamlit
* Pandas
* Synthetic CSV data

The app should be easy to run locally from the command line.

## Important boundaries

This is an academic MVP. Do not implement:

* real PSD2/open-banking connection
* live KvK API
* live POS/accounting integrations
* real lender offers
* money movement
* owner identity verification
* iDIN or BKR checks
* production-grade security
* predictive default model

The score is pre-underwriting decision support, not a final lending decision.

## Development approach

Build the project step by step.

Do not build the whole app in one uncontrolled step.

Recommended implementation order:

1. Minimal Streamlit app skeleton
2. Synthetic data schema
3. Synthetic data files
4. Data-loading utilities
5. Rules-based scoring engine
6. Restaurant Credit Passport page
7. Lender dashboard
8. Methodology/About page
9. README and final documentation polish

Before writing code for a component, first propose a short plan and wait for human approval.

