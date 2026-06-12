# DEEP_LAYER_TRACE.md — Is FinMem's deep memory structurally unable to retain knowledge?

**Verdict: CONFIRMED (finding F2). The long-term layer is a revolving door: every item
that ever entered it left within 3 trading days, and SEC filings — the layer's intended
content — mathematically cannot persist there at all.**

Method: offline replay of the authors' own verbose per-day memory dumps in
`TSLA_run.log` (229 train days, 3,781 distinct memories, zero API calls), parsed by
`data-pipeline/09_deep_layer_trace.py`, plus closed-form parameter math. Frozen main-run
artifacts untouched (Sin-4: this is instrumentation/analysis only).

## 1. The parameter math (frozen config = paper values, Q=14/90/365)

| Rule | Value | Consequence |
|---|---|---|
| Entry to LONG (promotion) | importance ≥ 80 | entrants arrive barely above the bar |
| LONG importance decay | ×0.988 / day | from 81.8 → falls below 80 in **2–3 days** |
| Exit from LONG (demotion) | importance < 80 | same threshold as entry ⇒ revolving door |
| 10-K direct ingestion into LONG | importance sampled {80: 80%, 60: 15%, 40: 5%} | 80 → 79.04 after ONE decay ⇒ demoted next step; 60/40 ⇒ demoted immediately. **Max possible residence: 1 day** |
| 10-Q ingestion into MID | {80: 15%, 60: 80%, 40: 5%} | needs ≥ 80 to promote, but 80×0.967 = 77.4 on day one ⇒ **can never reach LONG by decay alone** |
| Access feedback | importance += 5×counter | the only force fighting decay; rewards retrieval frequency, not document type |

There is no parameterization escape inside the paper's published values: any item
entering at the threshold is expelled within days because **the entry and exit bars are
the same number while importance only decays**.

## 2. Empirical replay (TSLA train, 229 days)

- **176 distinct items entered LONG; 175 exited; residence: avg 3.0 days, max 3.**
  (Dumps are post-decay/pre-jump, so "3 appearance-days" = entry day + 2.)
- Long-layer occupancy never exceeded **7** items and was usually 1–4 — out of 3,781
  memories the agent accumulated.
- **Zero SEC filings ever appeared in LONG.** (Train-window TSLA 10-Qs sit in MID and
  decay; the FY2024 10-K was filed 2025-01-30, three days before train start — never
  ingested at all, a window-boundary detail worth one log line on its own.)
- Who DID reach long? Exclusively news items that drew the 5%-probability importance-90
  initialization: 90 → 82.8 after one decay → the **double jump pass** in
  `BrainDB.step` (the `for _ in range(2)` loop) carries them short→mid→long in a
  single evening. Three days later they are demoted again. "Deep memory" in practice =
  a 3-day echo of lucky high-roll news.

## 3. Reconstructed timelines (verbatim from the replay)

**id 8 — the canonical "deep knowledge" item (a news article):**
```
2025-02-03 ingest(short) imp=90.0  (5% high-roll init)
2025-02-03 short  imp=82.80                    → double-jump to LONG same evening
2025-02-04 long   imp=81.81  rec=0.997 (reset)
2025-02-05 long   imp=80.82
2025-02-06 long   imp=79.85   < 80             → demoted after 3 days
2025-02-07..02-20 mid  77.2 → 59.0  < 60       → demoted after 9 more days
2025-02-21..04-02 short 54.3 → 5.26 < 5        → purged. Total life: 41 days
```
Note the recency discontinuity at each demotion: delta is kept but re-scaled by the new
layer's Q (mid rec=0.875=e^(−12/90) → next day short rec=0.395=e^(−13/14)).

**ids 103/105/114/115 — four items, identical trajectory to id 8, digit for digit**
(same init roll, same 3-day long residence, same 41-day life). The dynamics are
deterministic given the init draw; the layer adds no item-specific judgment.

**id 3023 — the "sticky" memory (Dan's recency puzzle):** ingested 2025-10-20 at
importance 50; decayed toward purge; then access feedback (+5×counter, counter reaching
5) repeatedly re-inflated importance (17.5 → 39.8 within four days), cycling it up
through MID and back; the up-jump resets delta/recency. At train-end: rec = 0.257 =
e^(−19/14) — i.e. **delta 19, not item age 51**: recency measures time since the last
*promotion*, not since ingestion. Mystery solved: recency is implicitly
"access-refreshed" via the jump mechanism — frequently-cited items never age, which
compounds the momentum-echo-chamber effect (the agent re-retrieves what it already
cited, F1's likely mechanism).

## 4. Implications (slide-ready)

1. The architecture's headline claim — layered memory that "retains critical
   information beyond human perceptual limits" — is not realized by the shipped
   parameterization: deep memory holds nothing longer than ~3 days and never holds a
   filing.
2. The 10-K/10-Q pipeline cost (extraction + summarization) buys at most a few days of
   MID-layer visibility per quarter.
3. Combined with F1 (100% momentum agreement on TSLA test), the system's effective
   information set ≈ recent news + the prompt's own momentum line.
4. Candidate ablation (post-main, exploratory only): entry/exit hysteresis (e.g., exit
   bar 60 for items that entered at 80) or decay-exempt filings — NOT run; listed as
   future work to respect the freeze.

*Instrumentation note: ingestion log lines carry no layer header (they are emitted
outside the per-layer dump), so naive parsing attributes them to the previous day's
last section; the parser flags `rec=1.0, delta=0` rows as ingests (B17, cosmetic).
For live traces, `MEMORY_EVENT_LOG` (Task 3.1) now records promote/demote/purge/ingest
events explicitly in future runs — off in frozen main runs.*
