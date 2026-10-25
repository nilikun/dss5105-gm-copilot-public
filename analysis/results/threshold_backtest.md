# Threshold backtest

Baseline window: 20 trailing working days; robust sigma = 1.4826 x MAD; clean period = before 2026-03-25; 400 injections per cell, seed 0.

## 1. Weekday effect (clean period)

| stage    |   Kruskal-Wallis p |   mean |   sd |    CV |
|:---------|-------------------:|-------:|-----:|------:|
| ASSEMBLY |              0.734 |    775 |   66 | 0.085 |
| KNITTING |              0.535 |    895 |   80 | 0.089 |
| PACKING  |              0.72  |    658 |   60 | 0.091 |
| WASHING  |              0.873 |    703 |   61 | 0.087 |

## 2. False alerts on clean data, and the real ASSEMBLY drop

| rule                                         |   false alerts / week | real drop first flagged   |
|:---------------------------------------------|----------------------:|:--------------------------|
| same-weekday median, -15%                    |                  1.59 | 2026-03-25                |
| same-weekday median, -20%                    |                  0.73 | 2026-03-25                |
| trailing median, -15%                        |                  0.86 | 2026-03-25                |
| modified z < -3.5 (Iglewicz-Hoaglin)         |                  0    | 2026-03-25                |
| Shewhart mean/sd 3 sigma                     |                  0    | 2026-03-25                |
| robust z < -1.5                              |                  1.35 | 2026-03-25                |
| robust z < -1.75 (briefing tier)             |                  0.37 | 2026-03-25                |
| robust z < -2                                |                  0.37 | 2026-03-25                |
| robust z < -3                                |                  0    | 2026-03-25                |
| 2 of 3 days robust z < -2 (Western Electric) |                  0    | 2026-03-26                |
| interrupt tier: z < -3 OR 2-of-3 z < -2      |                  0    | 2026-03-25                |

## 3. Recall on injected 3-day drops

| rule                                         | recall -10% (within 3 days)   | recall -15% (within 3 days)   | recall -20% (within 3 days)   | recall -30% (within 3 days)   |
|:---------------------------------------------|:------------------------------|:------------------------------|:------------------------------|:------------------------------|
| same-weekday median, -15%                    | 59%                           | 83%                           | 99%                           | 100%                          |
| same-weekday median, -20%                    | 40%                           | 59%                           | 87%                           | 99%                           |
| trailing median, -15%                        | 63%                           | 78%                           | 100%                          | 100%                          |
| modified z < -3.5 (Iglewicz-Hoaglin)         | 2%                            | 9%                            | 9%                            | 40%                           |
| Shewhart mean/sd 3 sigma                     | 2%                            | 16%                           | 29%                           | 87%                           |
| robust z < -1.5                              | 56%                           | 78%                           | 92%                           | 100%                          |
| robust z < -1.75 (briefing tier)             | 38%                           | 66%                           | 88%                           | 100%                          |
| robust z < -2                                | 22%                           | 53%                           | 72%                           | 98%                           |
| robust z < -3                                | 8%                            | 11%                           | 20%                           | 58%                           |
| 2 of 3 days robust z < -2 (Western Electric) | 5%                            | 16%                           | 38%                           | 87%                           |
| interrupt tier: z < -3 OR 2-of-3 z < -2      | 12%                           | 19%                           | 40%                           | 90%                           |
