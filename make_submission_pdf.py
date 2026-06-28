"""Generate IMPLEMENTATION_DEVELOPMENT.pdf — the detailed development report for the
seminar submission. reportlab Platypus; embeds key figures + the canonical results.
Table cells are wrapped in Paragraphs so HTML entities render and text wraps.
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
BODY = ParagraphStyle("Body", parent=ss["BodyText"], fontSize=9.7, leading=14, alignment=TA_LEFT, spaceAfter=5)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8, leading=10.5, textColor=colors.HexColor("#555"))
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=8, leading=10, spaceAfter=0)
CELLH = ParagraphStyle("CellH", parent=CELL, textColor=colors.white, fontName="Helvetica-Bold")
story = []


def P(t, s=BODY): story.append(Paragraph(t, s))
def H(t): story.append(Paragraph(t, H1))
def h(t): story.append(Paragraph(t, H2))
def sp(x=0.2): story.append(Spacer(1, x * cm))


def tbl(data, widths, fontsize=8):
    wrapped = []
    for i, row in enumerate(data):
        st = CELLH if i == 0 else ParagraphStyle("c", parent=CELL, fontSize=fontsize, leading=fontsize + 2)
        wrapped.append([Paragraph(str(c), st) for c in row])
    t = Table(wrapped, colWidths=[w * cm for w in widths], repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCC")),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5FA")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    story.append(t)


def fig(name, w=15.5, cap=""):
    p = os.path.join(FIG, name)
    if os.path.exists(p):
        from PIL import Image as PImage
        iw, ih = PImage.open(p).size
        story.append(Image(p, width=w * cm, height=w * ih / iw * cm))
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
  "entire experiment on a <b>leakage-free 2026 test window</b> (2026-01-02 to 2026-06-01) that "
  "postdates every model's knowledge cutoff &mdash; the fix for the paper's central flaw, where "
  "its 2022&ndash;23 test window sat inside the backbone LLM's training data. We built the full "
  "data pipeline (Alpaca news, SEC filings, Gemini summarisation, FinBERT sentiment), assembled a "
  "corrected and extended configuration we call <b>FinMem-Ours</b>, and benchmarked it against "
  "three baselines under one audited accounting convention.")
P("<b>Headline result.</b> On out-of-sample data the layered-memory + persona apparatus did not "
  "add value &mdash; it was beaten by simpler baselines:")
tbl([["Strategy", "Mean cum. return (0 bps)", "Mean Sharpe"],
     ["No-memory ablation", "+1.7%", "+0.38"],
     ["LC-Trader (plain long-context)", "−2.9%", "+0.16"],
     ["Buy &amp; Hold", "−4.1%", "+0.11"],
     ["FinMem-Ours (full apparatus)", "−5.3%", "−0.15"]],
    [6.2, 5.5, 3.5], fontsize=9.5)
sp(0.15)
P("Both stripped-down baselines &mdash; removing memory (the ablation) and a plain long-context "
  "model fed the same news (LC-Trader) &mdash; outperformed the complete system, which even "
  "trailed passive Buy &amp; Hold. This is the core of our critical assessment.", SMALL)

# ---------------- 2. objective ----------------
H("2. Objective &amp; experimental design")
P("The paper's reported out-performance may reflect the backbone LLM <i>remembering</i> "
  "2022&ndash;23 prices rather than predicting them. Our design therefore forces every generative "
  "component to have a knowledge cutoff before the data window: decision model <b>gpt-4.1-mini</b> "
  "(cutoff Jun-2024) and summariser <b>Gemini 3.1 Flash-Lite</b> (Jan-2025); train "
  "2025-07-01 to 2025-12-31, test 2026-01-02 to 2026-06-01.")
P("<b>Tickers:</b> TSLA, NFLX, AMZN, MSFT, COIN (the paper's five). Hyper-parameters were "
  "<b>frozen at the paper's published values before any test run</b> (the git commit hash is "
  "recorded) so that nothing was tuned on the test data, and the comparisons were declared in "
  "advance: FinMem-Ours vs Buy&amp;Hold, vs the no-memory ablation, vs LC-Trader, and vs the "
  "original as-shipped artefact.")

# ---------------- 3. pipeline ----------------
H("3. What we built &mdash; the data pipeline")
P("&bull; <b>News:</b> downloaded 18,311 articles across the 5 tickers from the Alpaca historical "
  "news API (full monthly coverage; single-source Benzinga feed, disclosed as a limitation).<br/>"
  "&bull; <b>Filings:</b> pulled the 10-K/10-Q MD&amp;A sections from SEC EDGAR / sec-api.io, "
  "dated by publication date.<br/>"
  "&bull; <b>Summarisation:</b> condensed all news and filings with Gemini 3.1 Flash-Lite, each "
  "item summarised independently from its own text only.<br/>"
  "&bull; <b>Sentiment:</b> scored every news item with FinBERT, locally on an RTX 3090.<br/>"
  "&bull; <b>Prices:</b> yfinance adjusted close. The pipeline outputs one model-input file per "
  "ticker, which we validated by stepping it through the paper's market-environment day by day.")

# ---------------- 4. finmem-ours ----------------
H("4. What we built &mdash; the FinMem-Ours system")
P("FinMem-Ours is the paper's architecture made to actually match the paper's description, frozen "
  "at a single git commit. The concrete things we implemented or corrected:")
P("&bull; <b>Self-adaptive persona</b> &mdash; the agent switches between a risk-seeking and a "
  "risk-averse stance based on its recent 3-day return (the paper describes this; the shipped code "
  "only ever used the static risk-seeking line).<br/>"
  "&bull; <b>Deep-memory retention</b> &mdash; we changed the memory mechanics so the deep layer "
  "actually keeps information over time (as shipped it discarded everything within a few days and "
  "never retained a single SEC filing).<br/>"
  "&bull; <b>Extended reflection</b> &mdash; a daily self-review of the last week's decisions, "
  "written into long-term memory (described in the paper, absent from the code).<br/>"
  "&bull; <b>Filing seeding</b> &mdash; the latest annual and quarterly report are loaded into "
  "memory on day one, with their true filing dates.<br/>"
  "&bull; <b>Long-only positions</b> &mdash; we hold at most one share and never short (the "
  "shipped portfolio allowed costless short-selling); local ada-002 embeddings; a 7-day "
  "return signal. Smaller corrections to the research code (sentiment labels, crashes on empty "
  "news days, a Python-3.12 port) are catalogued in the repository log.")

# ---------------- 5. baselines ----------------
H("5. Baselines we ran")
P("Every strategy is scored the same way (next section). We compared FinMem-Ours against:")
P("&bull; <b>Buy &amp; Hold</b> &mdash; stay fully invested.<br/>"
  "&bull; <b>No-memory ablation</b> &mdash; the identical model and prompt, but memory retrieval "
  "returns nothing, so the agent decides from the current day's information alone.<br/>"
  "&bull; <b>LC-Trader</b> &mdash; a plain long-context model fed the same news stream each day "
  "(no persona, no memory, no retrieval, no sentiment) that simply decides buy / sell / hold. "
  "This isolates the question: in a modern long-context world, does FinMem's machinery beat just "
  "giving a plain model the same news? We used prompt-caching to keep its cost low ($2.47 total).")

# ---------------- 6. measurement ----------------
H("6. How we measured performance")
P("All strategies use one accounting convention: <b>long-only unit positions, simple daily "
  "returns compounded over the full price series including the final test day</b>, reported with "
  "and without 10 bps transaction costs. Mid-project an independent recomputation disagreed with "
  "our first numbers; we traced it to two mistakes in our own reporting code &mdash; a dropped "
  "final trading day and an accidental short position whenever the agent said 'sell' &mdash; fixed "
  "both, and added an automatic check that the Buy &amp; Hold return equals the raw end-to-end "
  "price change (the run fails otherwise). Every number in this report uses the corrected "
  "convention; significance is assessed with the Wilcoxon signed-rank test and a bootstrap CI.")

# ---------------- 7. results ----------------
story.append(PageBreak())
H("7. Results (test window 2026 H1)")
df = pd.read_csv("data/09_results/metrics_canonical.csv")
order = {"FinMem-Ours": 0, "No-memory": 1, "LC-Trader": 2, "BuyHold": 3, "As-shipped": 4}
mm = "−"
def pct(x): return f"+{x*100:.1f}%" if x >= 0 else f"{mm}{abs(x)*100:.1f}%"
def num(x): return f"+{x:.2f}" if x >= 0 else f"{mm}{abs(x):.2f}"
rows = [["Ticker", "Strategy", "CR 0bps", "CR 10bps", "Sharpe", "Sortino", "MaxDD", "Turn", "%Long"]]
for t in ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]:
    sub = df[df.ticker == t].sort_values("strategy", key=lambda s: s.map(order))
    for _, r in sub.iterrows():
        rows.append([t, r["strategy"], pct(r["cr_0"]), pct(r["cr_10"]), num(r["sharpe_0"]),
                     num(r["sortino_0"]), f"{mm}{abs(r['mdd_0'])*100:.0f}%", str(int(r["turnover"])),
                     f"{r['pct_days_long']*100:.0f}%"])
tbl(rows, [1.3, 2.6, 1.7, 1.8, 1.5, 1.6, 1.5, 1.1, 1.4], fontsize=7.6)
sp(0.15)
P("Pooled Wilcoxon (daily): FinMem-Ours vs Buy&amp;Hold p=0.69 (not significant); FinMem-Ours vs "
  "No-memory p=0.075 (memory hurt). CR = cumulative return; MaxDD = maximum drawdown; Turn = "
  "number of position changes; %Long = share of days invested.", SMALL)
sp(0.3)
fig("bars_cum_return.png", 15.5, "Fig 1. Cumulative return by ticker, all four strategies (0 bps).")
fig("finmem_ours_all_tickers_vs_bh.png", 15.5, "Fig 2. FinMem-Ours (solid) vs Buy &amp; Hold (dashed) per ticker.")
story.append(PageBreak())
fig("equity_TSLA.png", 13.5, "Fig 3. TSLA equity curves &mdash; FinMem-Ours is the lowest line.")
fig("citation_share.png", 13.5, "Fig 4. Memory-layer citation share &mdash; the agent does draw on its deep / reflection memory.")
fig("vectordb_TSLA.png", 11.5, "Fig 5. End-state memory vectors (ada-002, PCA), coloured by layer.")

# ---------------- 8. findings ----------------
story.append(PageBreak())
H("8. Key findings")
P("<b>F1 &mdash; Pure momentum following.</b> The as-shipped agent agreed with 3-day price "
  "momentum on 100% of its trading decisions; our corrected version lowered this to 74%, but "
  "performance did not improve.")
P("<b>F2 &mdash; The deep memory does not retain.</b> Replaying the agent's own per-day memory "
  "logs, every item that entered the deep layer was expelled within three days, and not one SEC "
  "filing was ever retained &mdash; so the architecture's headline 'long-term memory' claim is "
  "not realised by the shipped settings. Our retention change fixes this (the deep layer ends with "
  "over a thousand items, and the agent even cites its own past reflections).")
P("<b>F3 &mdash; Memory subtracted value.</b> The no-memory ablation beat the full FinMem-Ours on "
  "the mean (+1.7% vs &minus;5.3%) and on 3 of 5 tickers.")
P("<b>F4 &mdash; A plain long-context model is a stronger baseline.</b> LC-Trader was almost "
  "entirely passive (held on roughly 97% of days), tracked the market, and beat FinMem-Ours on the "
  "mean (&minus;2.9% vs &minus;5.3%). Its cost, however, grows with the trading horizon as the "
  "context lengthens &mdash; an overhead the fixed-size memory design avoids.")

# ---------------- 9. reproducibility ----------------
H("9. Reproducibility")
P("Every result is regenerable from saved decision logs with no further model spend. The "
  "repository contains the data pipeline, the train/test runner, the LC-Trader baseline, the "
  "audited metrics module, the figure scripts, and leakage / behaviour test suites. A token-cost "
  "meter with hard caps and checkpoint-resume across daily quota resets is built in &mdash; the "
  "overnight run even survived a mid-run PC crash with no lost work.")

# ---------------- appendix ----------------
H("Appendix &mdash; the original code vs what the paper describes")
P("A by-product of the reproduction: where the published code differs from the paper's text.", SMALL)
tbl([["Aspect", "Paper / README describes", "What the shipped code actually does"],
     ["Risk persona", "Self-adaptive (seeking / averse)", "Static one-sided line only"],
     ["Deep memory", "Retains information over the long run", "Discards within ~3 days; no filings kept"],
     ["Extended reflection", "Daily multi-day self-review", "Not implemented"],
     ["Positions", "Long-only narrative", "'Sell' opens a costless short"],
     ["Filings", "Inform decisions", "Pre-window reports are never loaded"]],
    [3.2, 5.6, 6.7])

doc = SimpleDocTemplate("IMPLEMENTATION_DEVELOPMENT.pdf", pagesize=A4,
                        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                        title="FinMem Implementation Development Report",
                        author="Dan Shoshan & Nimrod Sagi")
doc.build(story)
print("wrote IMPLEMENTATION_DEVELOPMENT.pdf")
