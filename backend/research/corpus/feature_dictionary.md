---
artifact_type: feature_dictionary
title: Feature dictionary
model_version: XGBoost-v3
---

# Feature dictionary

The model reads 24 numbers per stock per day. This is what each one is and how it
is worked out.

One thing applies to every feature below. After it is calculated, it is turned
into a score that says "how unusual is this compared to every other stock in the
universe on the same day", then capped at plus or minus 5 so a single freak value
cannot dominate. That means the model is always making a relative comparison, not
an absolute one. A stock with a raw 3% gain on a day when everything gained 3% is
unremarkable, and the feature reflects that.

Source: `ml/features/build.py`.

## ret_5 — 5-day momentum

Percentage price change over the last 5 trading days.

`close / close_5_days_ago - 1`

Reads recent short-term direction. Short windows like this are noisy on their own,
which is why the model also gets 20, 60 and 120-day versions.

## ret_20 — 20-day momentum

Percentage price change over roughly the last month of trading.

`close / close_20_days_ago - 1`

The workhorse momentum window. Long enough to filter out day-to-day noise, short
enough to still be current.

## ret_60 — 60-day momentum

Percentage price change over roughly the last three months.

`close / close_60_days_ago - 1`

## ret_120 — 120-day momentum

Percentage price change over roughly the last six months.

`close / close_120_days_ago - 1`

The slowest momentum feature. It captures a longer trend that shorter windows miss,
and it tends to be steadier because a single bad week barely moves it.

## sma20_dist — Distance from 20-day moving average

How far the price sits above or below its own 20-day average.

`close / average_close_over_20_days - 1`

Positive means trading above the recent average. Large positive values can mean
either strength or that the price has run too far too fast.

## sma50_dist — Distance from 50-day moving average

Same idea as above over a 50-day average.

`close / average_close_over_50_days - 1`

## sma200_dist — Distance from 200-day moving average

Same idea over a 200-day average, which is the window most people mean when they
talk about a stock's long-term trend line.

`close / average_close_over_200_days - 1`

## rsi_14 — RSI (14)

The Relative Strength Index over 14 days. It compares the size of recent gains to
the size of recent losses and turns that into a number from 0 to 100.

Rises on days the stock gained, falls on days it lost. Traditionally, readings
above 70 are called overbought and below 30 oversold, though the model is not told
those thresholds and works them out for itself if they matter.

## vol_20 — 20-day volatility

How much the daily price bounces around, measured over 20 days and scaled up to an
annual figure so it reads like the volatility numbers quoted elsewhere.

`standard_deviation_of_daily_returns_over_20_days x sqrt(252)`

252 is roughly the number of trading days in a year.

## vol_60 — 60-day volatility

The same measure over 60 days. Comparing it against vol_20 shows whether a stock
has recently got calmer or choppier than it usually is.

## vol_of_vol — Volatility of volatility

How much the 20-day volatility figure has itself been moving around, over the last
20 days.

Picks up unstable conditions: not just a jumpy stock, but one whose jumpiness keeps
changing. That often marks a market in transition.

## atr_pct — ATR as a percentage of price

Average True Range over 14 days, divided by the current price.

True Range is the biggest of: today's high minus today's low, the gap from
yesterday's close up to today's high, or the gap from yesterday's close down to
today's low. Averaging it over 14 days gives a typical daily trading range.

Dividing by price makes it comparable across stocks, so a 500 dollar stock and a 20
dollar stock can be measured on the same scale.

## bb_pctb — Bollinger %b

Where the price sits inside its Bollinger Bands, as a 0-to-1 position.

The bands are drawn two standard deviations either side of the 20-day average.
0 means the price is sitting on the lower band, 1 means the upper band, 0.5 means
right on the average. Values outside 0 to 1 mean the price has pushed past a band.

## macd_hist — MACD histogram

The MACD histogram, divided by price to keep it comparable across stocks.

MACD is the gap between a fast (12-day) and slow (26-day) exponential average of
price. The histogram is the gap between MACD and its own 9-day average. In plain
terms it measures whether upward momentum is currently building or fading.

## volume_z — Volume z-score

How unusual today's trading volume is against the last 20 days.

`(today_volume - average_volume_20d) / standard_deviation_of_volume_20d`

A value of 2 means today's volume is two standard deviations above normal. Volume
spikes often accompany news, so this is the closest thing the model has to a news
detector.

## dollar_vol_z — Dollar-volume z-score

The same idea as volume_z, but for money traded rather than share count, and
measured over 60 days.

Shares traded multiplied by price, log-scaled, then compared to its own 60-day
norm. Using money rather than shares stops a cheap stock looking more active than
it is.

## obv_slope — On-balance-volume slope

Whether volume has been arriving on up days or down days over the last 20 days.

On-balance volume adds the day's volume when the stock rose and subtracts it when
it fell, accumulating over time. This feature measures how much that running total
has changed over 20 days, scaled by typical volume.

Rising means buying pressure, falling means selling pressure.

## dist_52w_high — Distance from 52-week high

How far below its highest price of the past year the stock is trading.

`close / highest_close_in_252_days - 1`

0 means it is at a one-year high. -0.30 means it is 30% below it.

## dist_52w_low — Distance from 52-week low

How far above its lowest price of the past year the stock is trading.

`close / lowest_close_in_252_days - 1`

## ret_skew_20 — Return skew (20 days)

Whether the last 20 days of returns were lopsided.

Positive skew means a few large up days among many small ones. Negative skew means
a few large down days. It describes the shape of recent moves rather than their
direction.

## ret_kurt_20 — Return kurtosis (20 days)

Whether the last 20 days contained extreme moves relative to a normal spread.

High values mean the stock has been mostly quiet with occasional violent days,
which is a different risk profile from something that moves steadily.

## gap — Overnight gap

How far the opening price jumped from the previous close.

`today_open / yesterday_close - 1`

Overnight gaps usually mean something happened while the market was shut, such as
an earnings release.

## intraday_range — Intraday range

How wide today's trading range was, relative to price.

`(today_high - today_low) / close`

Wide ranges signal disagreement between buyers and sellers within the day.

## rel_strength_20 — Relative strength (20 days)

Starts as the same 20-day price change as ret_20. The comparison against the rest
of the universe comes from the cross-sectional scoring step applied to every
feature, which is what turns it into a relative strength measure.

Because it shares a starting point with ret_20, the two features are correlated.
Attribution values are therefore split between them, and neither should be read in
isolation.
