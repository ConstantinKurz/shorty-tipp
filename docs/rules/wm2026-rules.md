# Shortytipp Tipp Game Rules

## Source

These rules are derived from the original document `WM2026 onlineRegeln.pdf`.

This file contains only the game rules relevant for scoring, ranking, jokers, winner prediction, payouts and rule clarifications.

It intentionally excludes online process, UI, login, profile and navigation descriptions.

---

## 1. Match Prediction Scoring

Participants predict the exact result of a match.

Base points are awarded according to how closely the prediction matches the actual result.

### 1.1 Exact Result

A prediction receives **6 points** if the predicted result is completely correct.

Examples:

- Prediction `2:1`, result `2:1` -> 6 points
- Prediction `3:3`, result `3:3` -> 6 points

### 1.2 Correct Tendency and Correct Goal Difference

A prediction receives **5 points** if:

- the tendency is correct, and
- the goal difference is correct, and
- the exact result is not correct.

Tendency means:

- home win
- draw
- away win

Goal difference means:

```text
home_goals - away_goals
```

Examples:

- Prediction `3:2`, result `1:0` -> 5 points
- Prediction `4:4`, result `2:2` -> 5 points
- Prediction `0:1`, result `6:7` -> 5 points

### 1.3 Correct Tendency and Correct Goals for One Team

A prediction receives **4 points** if:

- the tendency is correct, and
- the predicted goals for at least one team are correct, and
- the exact result is not correct, and
- the goal difference is not correct.

Examples:

- Prediction `3:2`, result `3:0` -> 4 points
- Prediction `1:2`, result `1:8` -> 4 points

### 1.4 Correct Tendency Only

A prediction receives **3 points** if:

- the tendency is correct, and
- no higher scoring category applies.

Examples:

- Prediction `3:2`, result `7:0` -> 3 points
- Prediction `4:2`, result `2:1` -> 3 points

### 1.5 Correct Goals for One Team Only

A prediction receives **1 point** if:

- the tendency is not correct, and
- the predicted goals for at least one team are correct.

Examples:

- Prediction `3:2`, result `0:2` -> 1 point
- Prediction `1:4`, result `1:0` -> 1 point
- Prediction `1:4`, result `7:4` -> 1 point

### 1.6 No Points

A prediction receives **0 points** if none of the scoring conditions apply.

---

## 2. Scoring Precedence

Only one scoring category applies per prediction.

The categories must be evaluated in this order:

1. exact result -> 6 points
2. correct tendency and correct goal difference -> 5 points
3. correct tendency and correct goals for one team -> 4 points
4. correct tendency only -> 3 points
5. correct goals for one team only -> 1 point
6. no match -> 0 points

Points from different categories are not added together.

---

## 3. Relevant Match Result

The relevant result is the played result.

For knockout matches, the relevant result includes extra time if extra time is played.

Penalty shootout results do not count.

Therefore, users may also predict a draw in knockout matches.

If a match is decided administratively, for example after abandonment or by an official decision, the match is removed from scoring.

If a match is removed from scoring, it is removed completely, including retroactively if necessary.

---

## 4. Round Multipliers

The base points from match predictions are multiplied depending on the tournament round.

| Round | Multiplier |
|---|---:|
| Group stage | x1 |
| Round of 32 | x2 |
| Round of 16 | x2 |
| Quarter-final | x3 |
| Semi-final | x3 |
| Third-place match | x3 |
| Final | x3 |

Examples:

- Exact result in group stage: `6 x 1 = 6`
- Exact result in round of 32: `6 x 2 = 12`
- Exact result in round of 16: `6 x 2 = 12`
- Exact result from quarter-final onward: `6 x 3 = 18`

---

## 5. Group Stage Prediction Limit

The group stage contains 72 matches.

Each participant may predict only **36 group-stage matches** of their choice.

The participant chooses which 36 group-stage matches to predict.

Group-stage matches beyond this limit do not count as valid predictions.

---

## 6. Joker Rules

Participants can set jokers on selected predictions.

A joker doubles the points of that prediction.

The joker is applied after the round multiplier.

Formula:

```text
final_points = base_points * round_multiplier * joker_multiplier
```

Where:

```text
joker_multiplier = 2 if joker is active
joker_multiplier = 1 otherwise
```

No jokers are available in the group stage.

If a participant forgets to set a joker, this cannot be corrected retroactively after the relevant deadline.

---

## 7. Joker Distribution

The PDF states that participants can set jokers in the following rounds:

| Round / Round Group | Number of Jokers |
|---|---:|
| Round of 32 | 3 |
| Round of 16 | 3 |
| Quarter-final | 2 |
| Semi-final and Final and third-place match combined | 2 |

### Clarification Required

The PDF also states that participants can set **8 jokers in total**.

However, the listed distribution adds up to:

```text
3 + 3 + 2 + 1 + 1 = 10
```

This discrepancy must be clarified before the joker logic is finalized.

Until clarified, joker limits should be configurable and should not be hardcoded as either 8 or 10.

---

## 8. World Cup Winner Prediction

Before the first match, each participant may predict the World Cup winner.

If the prediction is correct, bonus points are awarded.

The amount of points is configured per team as `Team.champion_points` and set by the admin.

The World Cup 2026 configuration derives these values from the betting-odds categories of the PDF:

| Original category | Meaning | `champion_points` |
|---|---|---:|
| A | teams ranked 1-8 by betting odds | 20 |
| B | teams ranked 9 or lower by betting odds | 30 |

The categories themselves no longer exist in the application. A team carries its bonus value
directly, so any distribution of points across teams is expressible, and the A/B scheme above is
one such distribution.

The betting-odds source named in the PDF is `sportwettentest.net`.

The admin can change a team's `champion_points` at any time. Changing it after the final has been
played requires running the "Recalculate scores" admin action.

The final relevant categorization is updated on 2026-06-10 and communicated separately.

Teams with equal odds receive the same `champion_points`.

A team left at `champion_points = 0` awards no bonus.

---

## 9. Ranking

The participant with the highest total score wins.

The total score consists of:

- match prediction points
- round multiplier effects
- joker effects
- World Cup winner prediction points, if applicable

---

## 10. Tie-Breaking

If two or more participants have the same total score, the participant with the higher number of exact predictions ranks higher.

An exact prediction means a prediction that received the full 6 base points before multipliers and joker effects.

If participants have:

- the same total score, and
- the same number of exact predictions,
- the same number of already used jokers,

then the rank is shared.

Example:

```text
Rank 1: User A, 100 points, 8 exact predictions, 5 jokers
Rank 2: User B, 95 points, 7 exact predictions, 5 jokers
Rank 2: User C, 95 points, 7 exact predictions, 5 jokers
Rank 3: User D, 90 points, 6 exact predictions, 4 jokers
Rank 4: User E, 90 points, 6 exact predictions, 5 jokers
```

---

## 11. Maximum Score Calculation from the PDF

The PDF provides the following maximum-score calculation:

| Section | Calculation | Points |
|---|---:|---:|
| Group stage | 36 matches x 6 points | 216 |
| Round of 32 | 16 matches x 12 points + 3 jokers x 12 points | 228 |
| Round of 16 | 8 matches x 12 points + 3 jokers x 12 points | 132 |
| Quarter-final | 4 matches x 18 points + 2 jokers x 18 points | 108 |
| Semi-final onward | 4 matches x 18 points + 2 jokers x 18 points | 108 |
| World Cup winner prediction | 20 points | 20 |
| Total |  | 802 |

Notes:

- This calculation assumes all match predictions are exact.
- This calculation assumes a 20-point World Cup winner prediction.
- A correct category B World Cup winner prediction can award 30 points.
- Therefore, the theoretical maximum may be higher if the correct World Cup winner is a category B team.
- The maximum-score calculation also reflects the joker discrepancy described above.

---

## 12. Payout Rules

The entry amount is **20 EUR**.

The full amount is paid out to participants according to placement.

### 12.1 Up to 20 Participants

| Placement | Share |
|---|---:|
| 1st place | 50% |
| 2nd place | 30% |
| 3rd place | 20% |

### 12.2 From 21 Participants

| Placement | Share |
|---|---:|
| 1st place | 45% |
| 2nd place | 25% |
| 3rd to 5th place | 10% each |

### 12.3 From 41 Participants

| Placement | Share |
|---|---:|
| 1st place | 40% |
| 2nd place | 25% |
| 3rd place | 15% |
| 4th to 7th place | 5% each |

### Clarification Required

If ranks are shared, the payout distribution for shared ranks must be clarified.

---

## 13. Legal Rule

Legal recourse is excluded.

---

## 14. Tournament Cancellation

If the entire tournament is cancelled for political, terrorist or other reasons, the entry amount is returned.

This rule describes the game agreement but does not define automated scoring behavior.

---

## 15. Open Clarifications

The following points must be clarified before final implementation:

1. **Joker total**
   - The PDF states 8 jokers total.
   - The detailed joker distribution adds up to 10.

2. **Removed matches and jokers**
   - If a removed match had a joker, it must be clarified whether the joker becomes available again.

3. **Winner prediction maximum** — resolved
   - The PDF maximum-score example uses 20 points for the World Cup winner prediction.
   - A category-B winner prediction awards 30 points, so the documented maximum of 802 assumes a
     category-A champion. The maximum is 812 when the champion is worth 30 points.
   - Since champion points are configured per team (section 8), the maximum score depends on the
     configuration and is not a fixed number.

4. **Shared-rank payout**
   - The payout rules do not specify how shared ranks affect payout distribution.
