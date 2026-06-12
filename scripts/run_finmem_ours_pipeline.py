"""FinMem-Ours full pipeline runner (Stage 7 steps 1-2). Personas approved by Dan.
Waits for the in-flight TSLA train, then: TSLA test -> {NFLX,AMZN,MSFT,COIN} train+test.
Frozen configs (2975839), memory-event logging ON per run, TokenMeter paces/sleeps
across UTC resets inside each child run. A failed train does not block later tickers
(its test fails fast on the missing -tap path)."""
import os
import sys
import time
import subprocess

os.environ["PYTHONUTF8"] = "1"
EV = os.path.join("data", "04_model_output_log")
PY = sys.executable


def run(args, event_log):
    env = dict(os.environ, MEMORY_EVENT_LOG=event_log)
    r = subprocess.run([PY, "run.py", "sim", *args], env=env)
    return r.returncode


def dirs(*paths):
    for p in paths:
        os.makedirs(p, exist_ok=True)


# 1. wait for the in-flight TSLA-Ours train (max ~40h to survive quota sleeps)
deadline = time.time() + 40 * 3600
target = os.path.join("data", "05_train_model_output", "TSLA_ours", "agent_1", "state_dict.pkl")
while not os.path.exists(target):
    if time.time() > deadline:
        print("TIMEOUT waiting for TSLA_ours train", flush=True)
        sys.exit(1)
    time.sleep(60)
print("TSLA_ours train artifact found - starting TSLA test", flush=True)

dirs("data/08_test_checkpoint/TSLA_ours", "data/07_test_model_output/TSLA_ours")
run(["-mdp", "data/03_model_input/tsla.pkl", "-st", "2026-01-02", "-et", "2026-06-01",
     "-rm", "test", "-cp", "config/tsla_finmem_ours_config.toml",
     "-ckp", "data/08_test_checkpoint/TSLA_ours",
     "-rp", "data/07_test_model_output/TSLA_ours",
     "-tap", "data/05_train_model_output/TSLA_ours"],
    f"{EV}/memory_events_TSLA_ours_test.jsonl")
print("=== TSLA_ours TEST DONE ===", flush=True)

for t in ("NFLX", "AMZN", "MSFT", "COIN"):
    tl = t.lower()
    dirs(f"data/06_train_checkpoint/{t}_ours", f"data/05_train_model_output/{t}_ours",
         f"data/08_test_checkpoint/{t}_ours", f"data/07_test_model_output/{t}_ours")
    run(["-mdp", f"data/03_model_input/{tl}.pkl", "-st", "2025-02-03", "-et", "2025-12-31",
         "-rm", "train", "-cp", f"config/{tl}_finmem_ours_config.toml",
         "-ckp", f"data/06_train_checkpoint/{t}_ours",
         "-rp", f"data/05_train_model_output/{t}_ours"],
        f"{EV}/memory_events_{t}_ours_train.jsonl")
    print(f"=== {t}_ours TRAIN DONE ===", flush=True)
    run(["-mdp", f"data/03_model_input/{tl}.pkl", "-st", "2026-01-02", "-et", "2026-06-01",
         "-rm", "test", "-cp", f"config/{tl}_finmem_ours_config.toml",
         "-ckp", f"data/08_test_checkpoint/{t}_ours",
         "-rp", f"data/07_test_model_output/{t}_ours",
         "-tap", f"data/05_train_model_output/{t}_ours"],
        f"{EV}/memory_events_{t}_ours_test.jsonl")
    print(f"=== {t}_ours TEST DONE ===", flush=True)

print("FINMEM-OURS PIPELINE COMPLETE (5 tickers train+test)", flush=True)
