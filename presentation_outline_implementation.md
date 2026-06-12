# Implementation Presentation — Outline (30 min)
Dan Shoshan & Nimrod Sagi · FinMem reproduction · per seminar handout structure

> Framing sentence (use verbatim, slide 1): *"In our paper presentation we charged FinMem
> with three crimes. Today we report what happened when we retried it under honest
> conditions — same architecture, same code, fair test dates, real frictions, frozen
> hyperparameters."*

## 1. Objective & setup (5–7 min)

- S1 Title + the one-sentence framing above.
- S2 **What we reproduced vs adapted vs added** (3-column slide):
  faithful = authors' code, 5 tickers, FAISS layered memory, FinBERT, persona prompts,
  train→test protocol; adapted = post-cutoff window (2025-02→2026-06), gpt-4.1-mini
  backbone (GPT-4-Turbo retired Oct-2026), Gemini summarizer, local embeddings,
  validation contract reimplemented (guardrails 0.3.2 incompatible with py3.12);
  added = portfolio layer, no-memory ablation, metrics v2, leakage test suite T1–T4.
- S3 **The three crimes → three fixes** (recap 30 sec each):
  leakage → every model cutoff predates the data window (table of cutoffs);
  zero friction → all metrics ± costs with break-even sweep;
  test-set tuning → freeze commit `f170a92` BEFORE first test run (show the hash).
- S4 Budget slide (crowd-pleaser): entire experiment ≈ **$7–11 + $5 OpenAI deposit**
  (Gemini paid run $6.95, decisions ~$0 via data-sharing pool, local GPU for the rest).

## 2. System & experimental design (8–10 min)

- S5 Architecture diagram (ARCHITECTURE.md fig): data pipeline → 5 agents → portfolio
  layer → evaluation. Mark which boxes are paper / adapted / new.
- S6 **The chronology engine**: date-keyed env, one-way valve, memory decay clock
  (Q=14/90/365), and the T1–T4 leakage test suite. Mention T4 caught a real bug (B10
  duplicate-URL article loss) — tests that catch things are tests that work.
- S7 What "training" means here: no gradients — supervised memory population
  (agent sees next-day move in 2025, writes reflections; test 2026 is blind).
  Honest note: no validation set exists in this design; our defense = zero tuning
  (frozen a priori at paper-published values).
- S8 EDA slide (EDA_REPORT.md table): hostile test window (4/5 tickers negative B&H),
  coverage asymmetry (TSLA 15/day vs NFLX 3/day, 67 zero-news days), volatility spread.
- S9 Pre-declared comparisons & metrics: FinMem vs B&H vs no-memory; mini vs gpt-4.1;
  Sharpe/CR/MDD ± 10bps + 0–50bps break-even; Wilcoxon; bootstrap CI;
  guardrail-failure rate (our new metric).

## 3. The reproduction gap: what the released code actually contains (4–5 min)
*(our strongest original material — "no stones left unturned")*

- S10 **Paper-vs-code discrepancy table**:
  B8 — self-adaptive persona (the paper's flagship profiling feature + its TSLA
  regime-switch case study) is ABSENT from the released code (two-sided rule exists
  only as a comment); B7 — FinBERT sentiment labels scrambled in their pipeline
  (their "positive" = P(negative)); D20 — shallow decay shipped Q=3 vs published Q=14;
  momentum window 3d hardcoded vs M=7 narrative; dual position accounting
  (accumulating shares vs direction-based metrics); frictionless shorting (Crime #4).
- S11 Pipeline bugs we fixed to make it run at all (pagination returning market-wide
  news, month-end date crash, empty bodies, guardrails/py3.12, B9 truncator crash) —
  "the published pipeline cannot reproduce its own inputs without repair."

## 4. Results (8–10 min) — [PLACEHOLDERS until runs complete]

- S12 Headline table: per-ticker Sharpe/CR/MDD — FinMem vs B&H vs no-memory,
  with and without costs. (THE slide. Whatever it says, it's a finding.)
- S13 Paper's claim vs our result (their TSLA 2.67 Sharpe vs ours, side by side, with
  the three-crimes annotation).
- S14 Break-even friction chart: at how many bps does FinMem's edge die?
- S15 Backbone sensitivity: mini vs gpt-4.1 (1-ticker) [vs local Ollama, exploratory].
- S16 Persona ablation: as-shipped vs paper-rule (B8 variant) — does the "flagship
  feature" matter?
- S17 Portfolio layer (our extension): portfolio vs equal-weight B&H.

## 5. Error analysis (with results, ~included in the 10–12 min block)

- S18 Guardrail-failure rate + the hidden Hold bias (validation fallback = Hold —
  same failure mode the paper mocked in FinGPT).
- S19 Reasoning-chain audit: ≥20 random agent-days/ticker, manually checked — do cited
  memory IDs actually support the decision? (storytelling guard, Challenger principle).
- S20 Behavior on sparse tickers / zero-news days; top-5-day return contribution
  (is performance a few lucky days?); per-month regime sensitivity.
- [Live demo: Streamlit replay — scrub one trading day: retrieved memories per layer →
  reasoning → action → equity curve. Canned, zero API risk.]

## 6. Lessons learned & conclusion (3–5 min)

- S21 Lessons: research code ≠ paper (4 discrepancies); reproducibility rots in 2 years
  (guardrails, openai SDK, yfinance, model retirements mid-project); chronology must be
  *tested*, not assumed (T4→B10); free-tier engineering (quota pacing, checkpoint-resume)
  as a first-class design constraint.
- S22 Three takeaways (mirror of the paper-presentation close):
  1) The architecture is reproducible; the *numbers* [are/aren't — fill from results].
  2) Honest backtesting changed the answer by [X] — leakage/friction/tuning each
     quantified.
  3) Trust nothing you haven't audited — including, as we learned, the authors' own
     sentiment labels.

## Q&A ammunition (backup slides)

- Cutoff table for every model; freeze-commit diff; T1–T4 test code; B7/B8 code
  screenshots; cost meter logs; Wilcoxon/bootstrap details; persona texts;
  why no validation set (and why frozen params answer it); survivorship disclosure.
