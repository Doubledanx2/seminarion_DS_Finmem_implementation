"""Generate IMPLEMENTATION_DEVELOPMENT.pdf — the detailed development report for the
seminar submission. reportlab Platypus; embeds key figures + the canonical results.
"""
import os
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak)

FIG = "data/09_results/figures"
NAVY = colors.HexColor("#16215B")
ACC = colors.HexColor("#0072B2")
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], textColor=NAVY, fontSize=15, spaceBefore=14, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], textColor=ACC, fontSize=12, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("Body", parent=ss["BodyText"], fontSize=9.5, leading=13.5, alignment=TA_LEFT, spaceAfter=5)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8, leading=10.5, textColor=colors.HexColor("#555"))
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=7.6, leading=9.5, spaceAfter=0)
story = []


def P(t, s=BODY): story.append(Paragraph(t, s))
def H(t): story.append(Paragraph(t, H1))
def h(t): story.append(Paragraph(t, H2))
def sp(x=0.2): story.append(Spacer(1, x * cm))


def tbl(data, widths, header=True, fontsize=7.8):
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1 if header else 0)
    style = [("FONTSIZE", (0, 0), (-1, -1), fontsize), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCC")),
             ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
             ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    story.append(t)


def fig(name, w=15.5, cap=""):
    p = os.path.join(FIG, name)
    if os.path.exists(p):
        from PIL import Image as PImage
        iw, ih = PImage.open(p).size
        h_ = w * ih / iw
        story.append(Image(p, width=w * cm, height=h_ * cm))
        if cap:
            story.append(Paragraph(cap, SMALL))
        sp(0.25)


# ---------------- title ----------------
story.append(Spacer(1, 3 * cm))
P("Reproducing FinMem on a Leakage-Free Window", ParagraphStyle("T", parent=H1, fontSize=22, alignment=TA_CENTER, textColor=NAVY))
sp(0.3)
P("Implementation Development Report", ParagraphStyle("Ts", parent=H2, fontSize=14, alignment=TA_CENTER, textColor=ACC))
sp(1.0)
P("MBA Data-Science Seminar &mdash; reproduction &amp; critical assessment of<br/>"
  "Yu et al., <i>FinMem: A Performance-Enhanced LLM Trading Agent with Layered Memory "
  "and Character Design</i> (arXiv:2311.13743)",
  ParagraphStyle("c", parent=BODY, alignment=TA_CENTER, fontSize=10.5))
sp(1.2)
P("Dan Shoshan &amp; Nimrod Sagi", ParagraphStyle("a", parent=BODY, alignment=TA_CENTER, fontSize=11))
P("Code: github.com/Doubledanx2/seminarion_DS_Finmem_implementation",
  ParagraphStyle("u", parent=SMALL, alignment=TA_CENTER))
story.append(PageBreak())

# ---------------- 1. executive summary ----------------
H("1. Executive summary")
P("We reproduced the FinMem LLM trading agent on the authors' own codebase and re-ran the "
  "entire experiment on a <b>leakage-free 2026 test window</b> (2026-01-02 &rarr; 2026-06-01) "
  "that postdates every model's knowledge cutoff &mdash; the fix for the paper's central flaw, "
  "where its 2022&ndash;23 test window sat inside the backbone LLM's training data. We built the "
  "full data pipeline (Alpaca news, SEC filings, Gemini summarisation, FinBERT sentiment), "
  "fixed numerous bugs in the research code, assembled a corrected and extended configuration "
  "we call <b>FinMem-Ours</b>, and benchmarked it against three baselines under one audited, "
  "canonical accounting convention.")
P("<b>Headline result.</b> On out-of-sample data the elaborate layered-memory + persona "
  "apparatus did not add value &mdash; it was beaten by simpler baselines:")
tbl([["Strategy", "Mean cum. return (0 bps)", "Mean Sharpe"],
     ["No-memory ablation", "+1.7%", "+0.38"],
     ["LC-Trader (plain long-context)", "&minus;2.9%", "+0.16"],
     ["Buy &amp; Hold", "&minus;4.1%", "+0.11"],
     ["FinMem-Ours (full apparatus)", "&minus;5.3%", "&minus;0.15"]],
    [6.2, 5.5, 3.5], fontsize=9)
sp(0.15)
P("Both stripped-down baselines &mdash; removing memory (the ablation) and a plain long-context "
  "model fed the same news (LC-Trader) &mdash; outperformed the complete system, which even "
  "trailed passive Buy &amp; Hold. This is the cleanest statement of our critical assessment.", SMALL)

# ---------------- 2. objective ----------------
H("2. Objective &amp; experimental design")
P("<b>Leakage thesis (Backtesting Sin #2).</b> The paper's reported out-performance may reflect "
  "the GPT-4-Turbo backbone <i>remembering</i> 2022&ndash;23 prices rather than predicting them. "
  "Our design forces every generative component to have a knowledge cutoff before the data "
  "window: decision model <b>gpt-4.1-mini</b> (cutoff Jun-2024), summariser <b>Gemini 3.1 "
  "Flash-Lite</b> (Jan-2025); train 2025-07-01&rarr;12-31, test 2026-01-02&rarr;06-01.")
P("<b>Tickers:</b> TSLA, NFLX, AMZN, MSFT, COIN (the paper's five). <b>Hyper-parameters frozen</b> "
  "at the paper's published values before any test run (git-hash recorded) to avoid data-snooping "
  "(Sin #4). Comparisons pre-declared: FinMem-Ours vs Buy&amp;Hold, vs no-memory, vs LC-Trader, "
  "vs the as-shipped artefact.")

# ---------------- 3. pipeline ----------------
H("3. Data pipeline")
P("<b>News:</b> Alpaca historical news API, 18,311 articles across the 5 tickers (full monthly "
  "coverage; single-source Benzinga feed &mdash; disclosed limitation). <b>Filings:</b> SEC 10-K/"
  "10-Q MD&amp;A via sec-api.io (31 credits) keyed by <i>filedAt</i> (publication date), never "
  "period-of-report. <b>Summarisation:</b> all news + filings condensed by Gemini 3.1 Flash-Lite "
  "with strict per-article isolation (no cross-article or background context). <b>Sentiment:</b> "
  "FinBERT (yiyanghkust/finbert-tone) locally on an RTX 3090. <b>Prices:</b> yfinance adjusted "
  "close. Output: one per-ticker model-input pickle stepped through the paper's MarketEnvironment.")

# ---------------- 4. implementation challenges ----------------
H("4. Implementation challenges (selected bugs in the research code)")
tbl([["ID", "Issue found in the shipped code", "Resolution"],
     ["B7", "FinBERT label order is {0:Neutral,1:Positive,2:Negative} but the code read "
            "pos=score[2] &mdash; the paper fed P(Negative) as the 'positive' sentiment", "Map labels by name"],
     ["B8", "The self-adaptive risk persona is NOT implemented &mdash; only a static one-sided "
            "'risk-seeking' line ships; the two-sided rule is commented out", "Config-flagged paper_rule (3-day CR sign)"],
     ["B14", "Empty-news days push an empty list to FAISS &rarr; crash (news != {} is always "
             "True for a list)", "Truthiness gate"],
     ["B16", "trading_reflection swallowed exceptions, returning {} silently &mdash; days vanished "
             "from the failure metric", "Log traceback + explicit hold fallback"],
     ["B20", "Our OWN metrics used raw decisions as the position (hold=flat, sell=SHORT) and "
             "dropped the final test day &mdash; inflated every cell", "Canonical accounting (see &sect;6)"],
     ["pin", "Pre-1.0 OpenAI API, hard-coded Linux paths, guardrails-ai pinned to Python&lt;3.11, "
             "ada-002 'Adj Close' removed by yfinance", "Modernised wrappers, v2 scripts"]],
    [1.1, 9.4, 5.0])
sp(0.1)
P("Every issue is catalogued with IDs B1&ndash;B20 / D1&ndash;D35 in IMPLEMENTATION_LOG.md "
  "(in the code zip).", SMALL)

# ---------------- 5. architecture ----------------
H("5. FinMem-Ours &mdash; the corrected &amp; extended configuration")
P("FinMem-Ours is the paper's architecture plus our fixes, frozen at one git hash. Key elements:")
P("&bull; <b>Self-adaptive persona</b> (paper_rule): risk-seeking/averse by the sign of the 3-day "
  "cumulative return (paper &sect;3.1), reconstructing the commented-out rule.<br/>"
  "&bull; <b>Deep-memory retention fix:</b> the as-shipped deep layer is a 3-day revolving door "
  "(entry bar == exit bar + decay &rarr; nothing persists, no filing ever retained). We disable "
  "downward jumps and use pure age-based recency, so the deep layer actually retains knowledge.<br/>"
  "&bull; <b>Extended reflection</b> (paper-described but never shipped): a daily M-day self-review "
  "synthesised into deep memory.<br/>"
  "&bull; <b>Filing seeding:</b> the most recent 10-K/10-Q as of day-1 are ingested with true "
  "filedAt dates (fixes a boundary gap where pre-window filings were never seen).<br/>"
  "&bull; <b>Long-only unit positions {0,+1}</b> (the shipped portfolio allowed costless shorting "
  "&mdash; Sin #7); ada-002 embeddings; observation = 7-day cumulative return.")

# ---------------- 6. backtest integrity + audit ----------------
H("6. Backtest integrity &amp; the metrics self-audit")
P("We treated the 'Seven Sins of Quantitative Investing' as a test-suite. Beyond the leakage fix "
  "(Sin #2) and frozen hyper-parameters (Sin #4), the most important episode was a "
  "<b>self-audit (Sin #5)</b>: an independent recompute disagreed with our committed numbers. We "
  "found two bugs in our own reporting &mdash; (1) the return series dropped the final test day "
  "(a &minus;4.57% TSLA day), and (2) it treated raw decisions as the position, implicitly "
  "shorting on every 'sell'. Both inflated results (e.g. NFLX no-memory read +57% vs the true "
  "+19.8%). We adopted ONE canonical convention &mdash; <b>carry-forward unit long-only positions, "
  "simple compounded returns, full price series including the terminal day</b> &mdash; with a "
  "regression assertion (B&amp;H must equal P[last]/P[first]&minus;1) that fails the run otherwise. "
  "Every figure below uses it. Catching our own unaudited-backtest bug is itself a result.")

# ---------------- 7. results ----------------
story.append(PageBreak())
H("7. Results (canonical convention, test 2026 H1)")
df = pd.read_csv("data/09_results/metrics_canonical.csv")
order = {"FinMem-Ours": 0, "No-memory": 1, "LC-Trader": 2, "BuyHold": 3, "As-shipped": 4}
rows = [["Ticker", "Strategy", "CR 0bps", "CR 10bps", "Sharpe", "Sortino", "MaxDD", "Turn", "%Long"]]
for t in ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]:
    sub = df[df.ticker == t].sort_values("strategy", key=lambda s: s.map(order))
    for _, r in sub.iterrows():
        rows.append([t, r["strategy"], f"{r['cr_0']*100:+.1f}%", f"{r['cr_10']*100:+.1f}%",
                     f"{r['sharpe_0']:.2f}", f"{r['sortino_0']:.2f}", f"{r['mdd_0']*100:.0f}%",
                     str(int(r["turnover"])), f"{r['pct_days_long']*100:.0f}%"])
tbl(rows, [1.3, 2.6, 1.7, 1.8, 1.5, 1.6, 1.5, 1.2, 1.4], fontsize=7.2)
sp(0.15)
P("Pooled Wilcoxon (daily): FinMem-Ours vs Buy&amp;Hold p=0.69 (n.s.); FinMem-Ours vs No-memory "
  "p=0.075 (memory hurt, median &minus;28 bps/day). Costs reported at 0 and 10 bps; a 0&ndash;50 "
  "bps break-even sweep is in the code.", SMALL)
sp(0.3)
fig("bars_cum_return.png", 15.5, "Fig 1. Cumulative return by ticker, all four strategies (0 bps).")
fig("finmem_ours_all_tickers_vs_bh.png", 15.5, "Fig 2. FinMem-Ours (solid) vs Buy &amp; Hold (dashed) per ticker.")
story.append(PageBreak())
fig("equity_TSLA.png", 13.5, "Fig 3. TSLA equity curves &mdash; FinMem-Ours is the lowest line.")
fig("citation_share.png", 13.5, "Fig 4. Memory-layer citation share &mdash; the agent does use its deep/reflection memory.")
fig("vectordb_TSLA.png", 11.5, "Fig 5. End-state memory vectors (ada-002, PCA), coloured by layer.")

# ---------------- 8. findings ----------------
story.append(PageBreak())
H("8. Key findings")
P("<b>F1 &mdash; Pure momentum following.</b> The as-shipped agent agreed with 3-day price momentum "
  "on 100% of its trading decisions; our changes moved this to 74%, but performance did not improve.")
P("<b>F2 &mdash; Deep memory is a revolving door.</b> Offline replay of the authors' own per-day "
  "memory dumps: 176 items entered the deep layer, every one expelled within 3 days, and zero SEC "
  "filings were ever retained &mdash; the entry threshold equals the exit threshold while importance "
  "only decays. The architecture's headline retention claim is not realised by the shipped parameters.")
P("<b>F3 &mdash; Memory subtracted value.</b> The no-memory ablation (same backbone, same prompt, "
  "empty retrieval) beat the full FinMem-Ours on the mean (+1.7% vs &minus;5.3%) and on 3/5 tickers.")
P("<b>F4 &mdash; A plain long-context model is a stronger baseline.</b> LC-Trader &mdash; no persona, "
  "memory, retrieval, embeddings or sentiment, just the same news streamed into gpt-4.1-mini &mdash; "
  "was almost entirely passive (&asymp;97% days long), tracked the market, and beat FinMem-Ours on the "
  "mean (&minus;2.9% vs &minus;5.3%). Prompt-caching cut its cost 71% ($2.47 for 515 calls), though "
  "cost scales quadratically with horizon &mdash; a structural overhead the fixed-size memory avoids.")

# ---------------- 9. reproducibility ----------------
H("9. Reproducibility")
P("All artefacts are checkpointed and every result is regenerable from saved decisions with $0 "
  "spend. Pipeline: <font face='Courier'>data-pipeline/01..05</font> (data), "
  "<font face='Courier'>run.py</font> (train/test), <font face='Courier'>lc_trader.py</font> "
  "(baseline), <font face='Courier'>16_canonical_metrics.py</font> (audited metrics), "
  "<font face='Courier'>17/20/21/22_*.py</font> (figures), "
  "<font face='Courier'>tests/</font> (leakage + behaviour suites). Money gates, a token/cost meter "
  "with hard caps, and checkpoint-resume across quota resets are built in; the overnight grid even "
  "survived a mid-run PC crash with zero data loss.")

# ---------------- appendix ----------------
H("Appendix &mdash; GitHub code vs paper: discrepancies")
tbl([["Aspect", "Paper / README implies", "Shipped code actually does"],
     ["Sentiment", "FinBERT labels used correctly", "Reads P(Negative) as 'positive' (B7)"],
     ["Persona", "Self-adaptive risk persona", "Static one-sided line only (B8)"],
     ["Deep memory", "Retains info beyond human limits", "3-day revolving door, no filings (F2)"],
     ["Decay", "Q_shallow = 14 (sensitivity-justified)", "Ships Q_shallow = 3 (D20)"],
     ["Shorting", "Long-only narrative", "'Sell' opens a costless short (Sin #7)"],
     ["Seeding", "Filings inform decisions", "Pre-window filings never ingested"],
     ["Metrics (ours)", "&mdash;", "Raw-decision position + dropped last day (B20)"]],
    [3.0, 6.0, 6.5])

doc = SimpleDocTemplate("IMPLEMENTATION_DEVELOPMENT.pdf", pagesize=A4,
                        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                        title="FinMem Implementation Development Report",
                        author="Dan Shoshan & Nimrod Sagi")
doc.build(story)
print("wrote IMPLEMENTATION_DEVELOPMENT.pdf")
