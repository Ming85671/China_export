# China Export Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally runnable Streamlit dashboard for China export commodity shipment analysis.

**Architecture:** Keep database access, pandas analytics, and Streamlit rendering separate. Load only required columns with the fixed China-export SQL scope, then apply interactive filters and aggregations through tested pure functions.

**Tech Stack:** Python, Streamlit, pandas, Plotly, SQLAlchemy, PyMySQL, pytest

---

### Task 1: Analytics Tests and Implementation

**Files:**
- Create: `tests/test_analytics.py`
- Create: `src/analytics.py`
- Create: `src/__init__.py`

- [ ] Write failing tests for normalization, filtering, time aggregation, metrics, and Top 10 behavior.
- [ ] Run `pytest tests/test_analytics.py -v` and confirm failures are caused by missing analytics functions.
- [ ] Implement the minimal pure pandas functions.
- [ ] Run `pytest tests/test_analytics.py -v` and confirm all analytics tests pass.

### Task 2: Database Query Tests and Implementation

**Files:**
- Create: `tests/test_database.py`
- Create: `src/database.py`

- [ ] Write a failing test asserting the query selects required columns from `axs` and applies the fixed country conditions.
- [ ] Run `pytest tests/test_database.py -v` and confirm failure is caused by missing query construction.
- [ ] Implement query construction and SQLAlchemy connection helpers.
- [ ] Run `pytest tests/test_database.py -v` and confirm the query test passes.

### Task 3: Streamlit Dashboard

**Files:**
- Create: `app.py`
- Create: `.streamlit/config.toml`

- [ ] Add sidebar filters and clear filter-context messaging.
- [ ] Add headline metrics that follow the active commodity filter.
- [ ] Add the main trend, Top 10 ranking, Top 10 trend comparison, and inspection-only detail table.
- [ ] Add empty-state and database-error handling.

### Task 4: Deployment Configuration and Documentation

**Files:**
- Create: `.streamlit/secrets.toml.example`
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `README.md`

- [ ] Document local secrets and Streamlit Cloud secrets setup.
- [ ] Exclude real credentials and local Streamlit secrets from version control.
- [ ] Document local run and test commands.

### Task 5: Verification

- [ ] Run `pytest -v`.
- [ ] Run `python -m compileall app.py src tests`.
- [ ] Start Streamlit locally and confirm the app reaches the expected missing-secrets setup state without crashing.
