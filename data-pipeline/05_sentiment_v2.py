# Adapted from 05-get_sentiment_by_ticker.py (see IMPLEMENTATION_LOG.md).
# Changes vs original:
#   1. Original indexed env_data with keys 'filling_q'/'filling_k' (typo) while
#      04-data_pipeline writes 'filing_q'/'filing_k' -> KeyError. Fixed.
#   2. Tickers/paths parameterized; outputs land at data/03_model_input/<ticker>.pkl
#      (lowercase), the path run.py expects.
#   3. FinBERT runs on GPU when available, batch of one article as in the paper.
#   4. Final pickle structure validated against puppy/environment.py:OneDateRecord
#      (dict[date] -> {price: {sym: float}, filing_k: {sym: str},
#       filing_q: {sym: str}, news: {sym: [str]}}).
#   5. BUG B7 (authors' code): finbert-tone id2label is {0:Neutral, 1:Positive,
#      2:Negative}, but the original read pos=scores[2]/neu=[1]/neg=[0] — i.e. the
#      paper's "positive score" was actually P(Negative). We map by label NAME.

import os
import sys
import pickle
import torch
from tqdm import tqdm
from transformers import BertTokenizer, BertForSequenceClassification

TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
INPUT_DIR = os.path.join("data", "02_intermediate", "env_data.pkl")
OUT_DIR = os.path.join("data", "03_model_input")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
tokenizer = BertTokenizer.from_pretrained("yiyanghkust/finbert-tone")
model = BertForSequenceClassification.from_pretrained("yiyanghkust/finbert-tone").to(DEVICE)
model.eval()


# label-name -> index, robust to any FinBERT variant's ordering (bug B7 fix)
LABEL_IDX = {name.lower(): i for i, name in model.config.id2label.items()}


def sentiment_score(text: str):
    """Returns (neg, neu, pos) by label NAME, not position."""
    inputs = tokenizer(text, return_tensors="pt", max_length=512, truncation=True).to(DEVICE)
    with torch.no_grad():
        outputs = model(**inputs)
    scores = torch.nn.functional.softmax(outputs.logits, dim=-1).tolist()[0]
    return (scores[LABEL_IDX["negative"]], scores[LABEL_IDX["neutral"]], scores[LABEL_IDX["positive"]])


def subset_symbol_dict(env_data: dict, symbol: str) -> dict:
    new_dict = {}
    for d, v in env_data.items():
        price, news = v[0]["price"], v[1]["news"]
        filing_q, filing_k = v[2]["filing_q"], v[3]["filing_k"]
        if symbol not in news:
            continue
        rec = {"price": {}, "filing_k": {}, "filing_q": {}, "news": {}}
        if symbol in price:
            rec["price"][symbol] = price[symbol]
        if symbol in filing_k:
            rec["filing_k"][symbol] = filing_k[symbol]
        if symbol in filing_q:
            rec["filing_q"][symbol] = filing_q[symbol]
        rec["news"][symbol] = news[symbol]
        new_dict[d] = rec
    return new_dict


def assign_finbert_scores(new_dict: dict, symbol: str) -> None:
    for d in tqdm(new_dict, desc=f"FinBERT {symbol}"):
        news_list = new_dict[d]["news"].get(symbol, [])
        scored = []
        for item in news_list:
            neg, neu, pos = sentiment_score(item)
            scored.append(
                f"{item} The positive score for this news is {pos}. "
                f"The neutral score for this news is {neu}. "
                f"The negative score for this news is {neg}."
            )
        new_dict[d]["news"][symbol] = scored


if __name__ == "__main__":
    tickers = sys.argv[1:] or TICKERS
    with open(INPUT_DIR, "rb") as f:
        env_data = pickle.load(f)
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"FinBERT on {DEVICE}")
    for t in tickers:
        sub = subset_symbol_dict(env_data, t)
        assign_finbert_scores(sub, t)
        out = os.path.join(OUT_DIR, f"{t.lower()}.pkl")
        with open(out, "wb") as f:
            pickle.dump(sub, f)
        print(f"[{t}] {len(sub)} dates -> {out}")
