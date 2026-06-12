"""Smoke test for the local-GPU model stack (no API keys needed):
1. bge-large-en-v1.5 embeddings on CUDA via puppy.embedding.LocalSentenceTransformerEmb
2. FAISS IndexIDMap roundtrip at the bge dimension (1024) as memorydb.py builds it
3. FinBERT (yiyanghkust/finbert-tone) sentiment on CUDA as 05_sentiment_v2.py uses it
"""
import os
import sys
import importlib.util

import numpy as np
import faiss
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(f"torch {torch.__version__} | CUDA available: {torch.cuda.is_available()}"
      + (f" ({torch.cuda.get_device_name(0)})" if torch.cuda.is_available() else ""))

# 1. local embeddings (import module directly; puppy/__init__ pulls heavier deps)
spec = importlib.util.spec_from_file_location("pemb", os.path.join(ROOT, "puppy", "embedding.py"))
pemb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pemb)

emb_func = pemb.make_embedding_function(
    backend="local", embedding_model="BAAI/bge-large-en-v1.5", chunk_size=5000, verbose=False
)
dim = emb_func.get_embedding_dimension()
print(f"bge-large dim = {dim} on {emb_func.device}")
assert dim == 1024

texts = [
    "Tesla deliveries beat expectations in Q1 2026.",
    "Tesla misses delivery estimates; shares fall.",
    "Netflix announces password sharing crackdown results.",
]
emb = emb_func(texts)
assert emb.shape == (3, dim) and emb.dtype == np.float32
print(f"embeddings ok: shape {emb.shape}")

# 2. FAISS roundtrip exactly as memorydb.py (normalize_L2 + IndexIDMap2/FlatIP)
faiss.normalize_L2(emb)
index = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))
index.add_with_ids(emb, np.array([10, 11, 12]))
q = emb_func(["Did Tesla beat delivery numbers?"])
faiss.normalize_L2(q)
dists, ids = index.search(q, 3)
print(f"faiss search ok: ids={ids[0].tolist()} sims={np.round(dists[0], 3).tolist()}")
assert ids[0][0] in (10, 11), "TSLA-delivery doc should rank first"

# 3. FinBERT on CUDA
from transformers import BertTokenizer, BertForSequenceClassification

device = "cuda" if torch.cuda.is_available() else "cpu"
tok = BertTokenizer.from_pretrained("yiyanghkust/finbert-tone")
fb = BertForSequenceClassification.from_pretrained("yiyanghkust/finbert-tone").to(device)
fb.eval()
label_idx = {name.lower(): i for i, name in fb.config.id2label.items()}
print(f"finbert-tone id2label: {fb.config.id2label} (bug B7: original code assumed neg/neu/pos order)")
inputs = tok("Tesla deliveries beat expectations and margins improved.",
             return_tensors="pt", max_length=512, truncation=True).to(device)
with torch.no_grad():
    scores = torch.nn.functional.softmax(fb(**inputs).logits, dim=-1).tolist()[0]
neg, neu, pos = scores[label_idx["negative"]], scores[label_idx["neutral"]], scores[label_idx["positive"]]
print(f"FinBERT ok on {device}: neg/neu/pos = {round(neg, 3)}/{round(neu, 3)}/{round(pos, 3)}")
assert pos > 0.5, "clearly positive sentence should score positive"

print("\nLOCAL MODEL STACK OK")
