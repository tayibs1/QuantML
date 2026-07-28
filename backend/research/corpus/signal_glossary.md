---
artifact_type: feature_dictionary
title: Signal glossary
model_version: XGBoost-v3
---

# Signal glossary

What the numbers on a QuantML signal card actually mean.

## BUY, HOLD and AVOID

These are rankings, not instructions.

Every trading day the model sorts the whole universe by its predicted 5-day
return and cuts it into three equal groups. Top third is labelled BUY, bottom
third AVOID, middle third HOLD. That is how the training labels were built, so it
is also how the output should be read.

The important consequence: these labels are always relative to the other stocks
being scored that day. A BUY means "expected to do better than most of this
universe over the next 5 days". It does not mean the stock is expected to go up.
In a falling market the BUY group can lose money and still be doing its job by
losing less than everything else.

Equally, an AVOID is not a prediction that a stock will fall. It means the model
ranks it in the weakest third of the universe right now.

Because the groups are cut into thirds by construction, roughly a third of the
universe carries each label on any given day. A large number of BUY signals is
therefore not a bullish market call.

## Confidence

The model's own estimated probability for the label it picked, as a percentage.

With three possible labels, pure guessing gives about 33%. So confidence should be
read against that floor, not against 0. A 36% confidence reading is barely above
chance. A 75% reading is a genuinely strong opinion by this model's standards.

Confidence describes how sure the model is given the patterns it was trained on.
It says nothing about whether those patterns still hold today. A confident model
can be confidently wrong when conditions change, and the training data cannot warn
it about a situation it never saw.

## Expected 5-day return

A blended estimate, not a forecast for this specific stock.

It is worked out by taking the average historical 5-day return of each of the
three groups, then weighting those averages by the probabilities the model assigned
to each group. So it inherits whatever the past relationship between group and
return happened to be.

Treat it as a relative ranking score expressed in return units. It is not a target
price and it carries no confidence interval.

## Risk level

Low, Moderate, High or Elevated, based only on recent realised volatility.

Each stock's 20-day volatility is ranked against the rest of the universe. The
bottom 40% are Low, up to 70% Moderate, up to 90% High, and the top 10% Elevated.

This is purely a volatility bucket. It does not account for company-specific risk,
event risk such as upcoming earnings, liquidity, or how crowded a position is. A
stock can sit in the Low bucket and still be exposed to a known upcoming event that
the model has no knowledge of.

## Drivers

The features that moved this particular prediction the most, biggest first.

They come from the model's own attribution of its decision, not from a general
ranking of which features matter across all stocks. Two stocks with the same label
can have completely different drivers.

## Model

Which trained model produced the signal. The current champion is XGBoost-v3.
