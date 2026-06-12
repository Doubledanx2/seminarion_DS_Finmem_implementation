"""Estimate OpenAI token cost for the news-summarization step (gate before any spend).

Reads data/01_raw/alpaca_news_<TICKER>.parquet, reconstructs the text we would send
(headline + summary + HTML-stripped content, as 03-summary.py sends the article body),
and estimates tokens as chars/4 (OpenAI rule of thumb) plus prompt overhead.
"""
import os
import re
import sys
import polars as pl

OUT_TOKENS_PER_ARTICLE = 200   # summary budget used by the paper's prompt
PROMPT_OVERHEAD_TOKENS = 30    # system msg + instruction wrapper
TAG_RE = re.compile(r"<[^>]+>")

# $/1M tokens (June 2026 list prices, OpenAI API; Batch API = 50% off)
# NOTE: only the gpt-4.1 family has a knowledge cutoff (2024-06) that predates our
# whole 2025-26 window; gpt-5.4/5.5 cutoffs (2025-08 / 2025-12) overlap it.
PRICES = {
    "gpt-4.1": (2.00, 8.00),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-5.4": (2.50, 15.00),
    "gpt-5.5": (5.00, 30.00),
}


def estimate(path: str) -> tuple[int, int, int]:
    df = pl.read_parquet(path)
    text = (
        df.with_columns(
            (
                pl.col("title").fill_null("") + "\n"
                + pl.col("summary").fill_null("") + "\n"
                + pl.col("content").fill_null("").map_elements(
                    lambda s: TAG_RE.sub(" ", s), return_dtype=pl.Utf8
                )
            ).str.len_chars().alias("chars")
        )
    )
    n = df.height
    in_tokens = int(text["chars"].sum() / 4) + n * PROMPT_OVERHEAD_TOKENS
    out_tokens = n * OUT_TOKENS_PER_ARTICLE
    return n, in_tokens, out_tokens


if __name__ == "__main__":
    raw_dir = os.path.join("data", "01_raw")
    files = sys.argv[1:] or [
        os.path.join(raw_dir, f) for f in sorted(os.listdir(raw_dir))
        if f.startswith("alpaca_news_") and f.endswith(".parquet")
    ]
    tot_n = tot_in = tot_out = 0
    for f in files:
        n, ti, to = estimate(f)
        tot_n, tot_in, tot_out = tot_n + n, tot_in + ti, tot_out + to
        print(f"{os.path.basename(f)}: {n} articles, ~{ti / 1e6:.2f}M in / ~{to / 1e6:.2f}M out tokens")
    print(f"\nTOTAL: {tot_n} articles, ~{tot_in / 1e6:.2f}M input + ~{tot_out / 1e6:.2f}M output tokens")
    for model, (p_in, p_out) in PRICES.items():
        cost = tot_in / 1e6 * p_in + tot_out / 1e6 * p_out
        print(f"  {model:12s}: ${cost:,.2f}")
