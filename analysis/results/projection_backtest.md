# Completion projection backtest

Walk-forward over 34 completed orders (each predicted from orders completed before it was placed; first 15 skipped for history). Late orders in sample: 13. Cycle–pieces correlation (all completed): 0.75. Bootstrap n=1000, seed 0.

| model             |   MAE (days) | MAE 95% CI   |   bias (days) | P80 coverage   | MAE 1st half / 2nd half   | late-order recall   | late-order precision   |
|:------------------|-------------:|:-------------|--------------:|:---------------|:--------------------------|:--------------------|:-----------------------|
| A plan (due date) |         6.94 | 5.2–8.8      |          1.71 | 62%            | 6.8 / 7.1                 | 0%                  | 0%                     |
| B global median   |         5.97 | 4.6–7.5      |          0.62 | 74%            | 5.5 / 6.4                 | 85%                 | 50%                    |
| C size band       |         5.31 | 4.1–6.7      |         -1.22 | 65%            | 5.6 / 5.0                 | 77%                 | 56%                    |
| C + load scaling  |         5.97 | 4.5–7.5      |         -2.2  | 59%            | 6.1 / 5.9                 | 69%                 | 50%                    |
| E log-linear size |         4.58 | 3.6–5.6      |          0.12 | 76%            | 4.4 / 4.8                 | 77%                 | 48%                    |

MAE = mean |P50 − actual cycle|. P80 coverage should be ≈ 80%. Late-order recall/precision: P80 projection exceeds the promised lead time, vs actually late.
