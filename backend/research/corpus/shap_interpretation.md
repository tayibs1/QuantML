---
artifact_type: shap_summary
title: How to read the feature attribution
model_version: XGBoost-v3
---

# How to read the feature attribution

Every signal comes with a breakdown of which features pushed the prediction where.
This explains what those numbers are and what they are not.

Source: `ml/inference/shap_summary.py`.

## Where the numbers come from

The model is a large collection of decision trees, so there is no single equation
to point at. Instead the contribution of each feature is worked out by asking how
the prediction would change if that feature's value were unknown, averaged fairly
across every order the features could be considered in. These are SHAP values.

XGBoost calculates them directly, so the numbers come from the model itself rather
than from an approximation fitted around it.

They have a useful property: the starting point plus every feature's contribution
adds up exactly to the model's output for that stock. Nothing is left unexplained.

## Reading a driver

Each driver has a contribution with a sign.

**Supports** means the feature pushed the model towards the label it chose.
**Opposes** means it pushed against, and the label was reached despite it.

Opposing drivers are the more interesting half. A BUY where the three largest
contributions all support it is a clean agreement. A BUY where a large opposing
driver sits just behind the supporting ones is a disagreement the model resolved
narrowly, and it is more fragile.

The size of a contribution is measured in the model's internal scoring units, not
percent and not return. Only relative sizes are meaningful: a driver at 0.12 moved
the prediction twice as much as one at 0.06. The absolute value has no external
interpretation.

The base value is where the model starts before looking at any feature, and it
reflects how common the label is overall rather than anything about this stock.

## What attribution does not tell you

**It is not causation.** It describes how this model reached this output. It does
not say the feature causes the return. The model may have learned a relationship
that is coincidental.

**It is not a correctness check.** A confident prediction with a clean attribution
can still be wrong. Attribution explains the reasoning, not the outcome.

**Correlated features split credit.** When features measure overlapping things, the
attribution divides between them, understating each. The four momentum windows and
rel_strength_20 all overlap, so seeing them share the top of a list means one
underlying bet, not several independent ones.

**It is specific to this stock on this day.** Global feature importance on the
models page is a different measurement, showing which features matter across all
predictions. The two frequently disagree, and both are correct about their own
question.

## Global importance versus per-signal attribution

The models page shows importance scores summed across the whole training set. That
answers "which features does this model rely on in general".

The drivers on a signal card answer "which features moved this one prediction".

A feature can be near-useless overall but decisive for one stock on one day, and
the reverse is also common. Do not use one to check the other.
