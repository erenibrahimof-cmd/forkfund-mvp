# ForkFund MVP

ForkFund is a B2B Restaurant Credit Passport and lender dashboard MVP for Dutch restaurant financing.

This repository contains the Assignment 2 technical MVP implementation for RSM FinTech: Business Models and Applications.

## Current status

This project follows a design-first process. The MVP design specification is available in:

`docs/mvp_design.md`

## Planned MVP flow

Restaurant owner → enters details → connects/selects mock financial data → receives Credit Passport → lender views dashboard → lender filters and opens the Passport.

## Planned technology stack

- Python
- Streamlit
- Pandas
- Synthetic restaurant, bank, POS, and accounting data

## Assignment context

The MVP will implement the core ForkFund flow:

1. Restaurant onboarding and simulated KvK lookup
2. Mock bank, POS, and accounting data connection
3. Rules-based Restaurant Credit Passport scoring
4. Credit Passport generation
5. Lender dashboard with filters