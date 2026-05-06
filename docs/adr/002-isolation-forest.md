# ADR-002 — Isolation Forest as Anomaly Detection Baseline

**Status:** Accepted  
**Date:** 2026-05-06  
**Deciders:** Data Science Team

---

## Context

The ML pipeline must detect teams at elevated burnout risk before the risk materializes as attrition or medical leave. The problem structure is:

- **No labeled ground truth.** Organizations rarely tag historical periods as "this team was burning out." The dataset is inherently unlabeled.
- **Class imbalance.** Even in distressed organizations, at-risk teams are a minority.
- **Low-dimensional features.** The AFS composite feature plus its four components (calendar density, after-hours index, context-switch count, sprint health inverse) give ~5 numeric signals.
- **Interpretability matters.** HR stakeholders need to understand *why* a team is flagged, not just *that* it is flagged.

Candidates evaluated:
1. **Rule-based thresholds** (e.g., AFS > 70 → Red Zone)
2. **Isolation Forest** (unsupervised anomaly detection)
3. **One-Class SVM**
4. **Autoencoder**
5. **LSTM sequence model**

---

## Decision

Use **Isolation Forest** as the primary anomaly detector for point-in-time risk scoring, **complemented by an LSTM** for trend-based (sequence) anomaly detection. The ensemble output is the final Resilience Zone classifier.

---

## Rationale

**Why Isolation Forest over rule-based thresholds:**
Rules require manually setting thresholds that generalize poorly across organizations of different sizes and cultures. Isolation Forest learns the normal distribution from data and scores deviations from it — thresholds become data-driven.

**Why Isolation Forest over One-Class SVM:**
- Linear complexity O(n) vs. O(n²) for kernel SVM.
- No kernel selection required; fewer hyperparameters to tune.
- Works well with the low-dimensional feature space (~5 signals).

**Why Isolation Forest over Autoencoder:**
- Autoencoders require more data to learn meaningful reconstructions.
- Isolation Forest is more interpretable: anomaly score is derived from path lengths in random trees, which can be linked back to individual features.
- Significantly faster to train and serve.

**Why add LSTM at all:**
Isolation Forest scores each day independently. A team might show individually unremarkable scores that represent a clear deteriorating *trend* over 14 days — a pattern Isolation Forest cannot detect. The LSTM operates on rolling 14-day windows to capture temporal deterioration signals.

---

## Consequences

**Positive:**
- No labeled data required — unsupervised setup fits the available data.
- Isolation Forest trains in seconds on typical feature table sizes.
- Inference is fast enough for real-time scoring (p99 < 200ms target).
- Scikit-learn implementation is production-stable and well-tested.

**Negative:**
- Isolation Forest contamination parameter (`contamination`) must be calibrated per organization or set conservatively. Too low → many false alarms; too high → missed cases.
- LSTM adds training complexity and requires sufficient historical data (≥90 days recommended).
- Neither model provides causal explanations — SHAP values or feature attributions needed for explainability layer.

**Future work:**
- Calibrate `contamination` per organization via pilot feedback loops.
- Explore SHAP TreeExplainer for feature attribution on IF scores.
- Evaluate replacing IF with LOF or ECOD if recall targets are not met in production.
