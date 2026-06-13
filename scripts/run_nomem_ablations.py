"""Part B: no-memory ablation test runs for NFLX/AMZN/MSFT/COIN.
Loads each ticker's trained FinMem-Ours agent, runs the 2026 test with no_memory=true
(retrieval returns empty; same backbone + prompt). Idempotent: skips finished tags."""
import os
import sys
import pickle
import datetime
import subprocess

os.environ["PYTHONUTF8"] = "1"
PY = sys.executable
EV = os.path.join("data", "04_model_output_log")


def window(ticker):
    keys = sorted(pickle.load(open(f"data/03_model_input/{ticker.lower()}.pkl", "rb")).keys())
    s = next(k for k in keys if k >= datetime.date(2026, 1, 2))
    e = max(k for k in keys if k <= datetime.date(2026, 6, 1))
    return str(s), str(e)


for t in ("NFLX", "AMZN", "MSFT", "COIN"):
    tag = f"{t}_ours_nomem"
    final = f"data/07_test_model_output/{tag}/agent_1/state_dict.pkl"
    if os.path.exists(final):
        print(f"{tag}: already done", flush=True)
        continue
    for d in (f"data/08_test_checkpoint/{tag}", f"data/07_test_model_output/{tag}"):
        os.makedirs(d, exist_ok=True)
    st, et = window(t)
    env = dict(os.environ, MEMORY_EVENT_LOG=f"{EV}/memory_events_{tag}_test.jsonl")
    print(f"=== {tag} test {st}..{et} ===", flush=True)
    rc = subprocess.run([PY, "run.py", "sim",
                         "-mdp", f"data/03_model_input/{t.lower()}.pkl",
                         "-st", st, "-et", et, "-rm", "test",
                         "-cp", f"config/{t.lower()}_finmem_ours_nomem_config.toml",
                         "-ckp", f"data/08_test_checkpoint/{tag}",
                         "-rp", f"data/07_test_model_output/{tag}",
                         "-tap", f"data/05_train_model_output/{t}_ours"], env=env).returncode
    print(f"=== {tag} rc={rc} ===", flush=True)
print("NOMEM ABLATIONS COMPLETE", flush=True)
