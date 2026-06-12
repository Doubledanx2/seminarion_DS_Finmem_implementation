"""Stage-9 orchestrator: executes the Stage-8 overnight queue unattended.

Idempotent + resumable: each step has a done-predicate checked on every invocation;
partially-run train/test steps resume from their every-step checkpoints via
run.py sim-checkpoint. Lockfile prevents double instances (watchdog-safe).
Failures log full tracebacks and the queue continues with the next item.

Usage:
  python run_overnight.py                # the real thing
  python run_overnight.py --dry-run      # walk queue, no LLM spend, green/red report
  python run_overnight.py --morning-report
"""
import os
import sys
import json
import time
import pickle
import datetime
import threading
import traceback
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)
os.environ["PYTHONUTF8"] = "1"

PY = sys.executable
TICKERS = ["TSLA", "NFLX", "AMZN", "MSFT", "COIN"]
LOCK = os.path.join(ROOT, "overnight.lock")
LOG = os.path.join(ROOT, "overnight.log")
EV = os.path.join("data", "04_model_output_log")
DRY = "--dry-run" in sys.argv
CURRENT_STEP = {"name": "starting"}


def log(msg):
    line = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ---------------- lockfile ----------------
def pid_alive(pid):
    try:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                             capture_output=True, text=True).stdout
        return str(pid) in out
    except Exception:
        return False


def acquire_lock():
    if os.path.exists(LOCK):
        try:
            old = int(open(LOCK).read().strip())
        except ValueError:
            old = -1
        if old > 0 and pid_alive(old):
            log(f"another instance alive (pid {old}) — exiting (watchdog no-op)")
            sys.exit(0)
        log(f"stale lock (pid {old}) — taking over")
    with open(LOCK, "w") as f:
        f.write(str(os.getpid()))


def release_lock():
    try:
        os.remove(LOCK)
    except OSError:
        pass


# ---------------- heartbeat ----------------
def heartbeat():
    while True:
        time.sleep(180)
        log(f"HEARTBEAT step={CURRENT_STEP['name']}")


# ---------------- helpers ----------------
def window_dates(ticker):
    with open(os.path.join("data", "03_model_input", f"{ticker.lower()}.pkl"), "rb") as f:
        keys = sorted(pickle.load(f).keys())
    tr_s = next(k for k in keys if k >= datetime.date(2025, 7, 1))
    tr_e = max(k for k in keys if k <= datetime.date(2025, 12, 31))
    te_s = next(k for k in keys if k >= datetime.date(2026, 1, 2))
    te_e = max(k for k in keys if k <= datetime.date(2026, 6, 1))
    return tr_s, tr_e, te_s, te_e


def run_child(args, event_log):
    if DRY:
        log(f"DRY would run: run.py sim {' '.join(args[:8])} ...")
        return 0
    env = dict(os.environ, MEMORY_EVENT_LOG=event_log)
    with open(LOG, "a", encoding="utf-8") as lf:
        return subprocess.run([PY, "run.py", *args], env=env, stdout=lf,
                              stderr=subprocess.STDOUT).returncode


def sim_or_resume(mode, ticker, tag, cfg, tap=None):
    """Fresh `sim` or `sim-checkpoint` resume depending on checkpoint presence."""
    ck_root = "06_train_checkpoint" if mode == "train" else "08_test_checkpoint"
    rp_root = "05_train_model_output" if mode == "train" else "07_test_model_output"
    ckp = os.path.join("data", ck_root, tag)
    rp = os.path.join("data", rp_root, tag)
    os.makedirs(ckp, exist_ok=True)
    os.makedirs(rp, exist_ok=True)
    ev_log = f"{EV}/memory_events_{tag}_{mode}.jsonl"
    tr_s, tr_e, te_s, te_e = window_dates(ticker)
    st, et = (tr_s, tr_e) if mode == "train" else (te_s, te_e)
    if os.path.exists(os.path.join(ckp, "env", "env.pkl")):
        log(f"{tag} {mode}: RESUMING from checkpoint")
        return run_child(["sim-checkpoint", "-ckp", ckp, "-rp", rp, "-cp", cfg, "-rm", mode], ev_log)
    args = ["sim", "-mdp", f"data/03_model_input/{ticker.lower()}.pkl",
            "-st", str(st), "-et", str(et), "-rm", mode, "-cp", cfg,
            "-ckp", ckp, "-rp", rp]
    if tap:
        args += ["-tap", tap]
    return run_child(args, ev_log)


def artifact(mode, tag):
    root = "05_train_model_output" if mode == "train" else "07_test_model_output"
    return os.path.join("data", root, tag, "agent_1", "state_dict.pkl")


def script(name, *extra):
    if DRY and name in ("11_portfolio_layer_run.py",):
        log(f"DRY would run: {name}")
        return 0
    with open(LOG, "a", encoding="utf-8") as lf:
        return subprocess.run([PY, os.path.join("data-pipeline", name), *extra],
                              stdout=lf, stderr=subprocess.STDOUT).returncode


# ---------------- steps ----------------
def preflight():
    import toml
    problems = []
    for t in TICKERS:
        cfg = toml.load(os.path.join("config", f"{t.lower()}_finmem_ours_config.toml"))
        g = cfg["general"]
        for k, v in [("persona_switch_window", 3), ("observation_window", 7),
                     ("unit_position", True), ("disable_downward_jumps", True),
                     ("pure_age_recency", True), ("extended_reflection_train", True),
                     ("top_k", 5)]:
            if g.get(k) != v:
                problems.append(f"{t}: {k}={g.get(k)} != {v}")
        if cfg["chat"].get("paid_cap_usd") != 3.00:
            problems.append(f"{t}: paid_cap_usd != 3.00")
    seeds = json.load(open("data/02_intermediate/filing_seeds.json", encoding="utf-8"))
    ks = {s["symbol"] for s in seeds if s["type"] == "10-K"}
    if ks != set(TICKERS):
        problems.append(f"10-K seeds missing for {set(TICKERS) - ks}")
    # persona self-verification (regenerates configs deterministically + asserts)
    if script("10_finmem_ours_setup.py") != 0:
        problems.append("persona self-verification FAILED")
    r = subprocess.run([PY, os.path.join("tests", "test_leakage.py")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        problems.append("leakage suite T1-T4 FAILED")
    if problems:
        raise RuntimeError("preflight: " + "; ".join(problems))
    log("preflight OK (configs, seeds, persona self-verify, leakage T1-T4)")


STEPS = [("preflight", lambda: False, preflight)]
for _t in TICKERS:
    STEPS.append((f"{_t}_train", lambda t=_t: os.path.exists(artifact("train", f"{t}_ours")),
                  lambda t=_t: sim_or_resume("train", t, f"{t}_ours",
                                             f"config/{t.lower()}_finmem_ours_config.toml")))
    STEPS.append((f"{_t}_test", lambda t=_t: os.path.exists(artifact("test", f"{t}_ours")),
                  lambda t=_t: sim_or_resume("test", t, f"{t}_ours",
                                             f"config/{t.lower()}_finmem_ours_config.toml",
                                             tap=f"data/05_train_model_output/{t}_ours")))
STEPS += [
    ("TSLA_nomem_test",
     lambda: os.path.exists(artifact("test", "TSLA_ours_nomem")),
     lambda: sim_or_resume("test", "TSLA", "TSLA_ours_nomem",
                           "config/tsla_finmem_ours_nomem_config.toml",
                           tap="data/05_train_model_output/TSLA_ours")),
    ("portfolio_layer",
     lambda: os.path.exists("data/09_results/portfolio_layer_result.json"),
     lambda: script("11_portfolio_layer_run.py")),
    ("final_report", lambda: False, lambda: script("12_final_report.py")),
    ("error_pack", lambda: False, lambda: script("13_error_pack.py")),
]


def morning_report():
    done = {n: d() for n, d, _ in STEPS if n not in ("preflight", "final_report", "error_pack")}
    missing = [n for n, ok in done.items() if not ok]
    meter = {}
    mp = os.path.join(EV, "openai_meter.json")
    if os.path.exists(mp):
        meter = json.load(open(mp))
    paid = (meter.get("paid_in", 0) / 1e6 * 0.40 + meter.get("paid_out", 0) / 1e6 * 1.60)
    lines = [
        f"## Overnight run — morning summary ({datetime.datetime.now():%Y-%m-%d %H:%M})",
        f"- Grid: {sum(done.values())}/{len(done)} run-steps complete"
        + (f"; REMAINING: {', '.join(missing)}" if missing else " — FULL GRID DONE"),
        f"- RESULTS_FINMEM_OURS.md: {'present' if os.path.exists('RESULTS_FINMEM_OURS.md') else 'MISSING'}",
        f"- Chat spend: paid ~ ${paid:.2f} of $3.00 cap ({meter.get('calls', 0)} lifetime calls)",
        f"- Log tail: see overnight.log",
    ]
    text = "\n".join(lines)
    log(text)
    # prepend into STATUS.md under the header
    status = open("STATUS.md", encoding="utf-8").read()
    marker = "## Overnight run — morning summary"
    if marker in status:
        head, _, rest = status.partition(marker)
        rest = rest.partition("\n## ")[2]
        status = head + text + ("\n## " + rest if rest else "")
    else:
        first = status.find("\n## ")
        status = status[:first] + "\n" + text + "\n" + status[first:]
    open("STATUS.md", "w", encoding="utf-8").write(status)
    return missing


def main():
    if "--morning-report" in sys.argv:
        morning_report()
        return
    acquire_lock()
    threading.Thread(target=heartbeat, daemon=True).start()
    log(f"=== orchestrator start (pid {os.getpid()}{', DRY-RUN' if DRY else ''}) ===")
    results = {}
    try:
        for name, done, action in STEPS:
            CURRENT_STEP["name"] = name
            try:
                if done():
                    log(f"[SKIP] {name} (already complete)")
                    results[name] = "done-prior"
                    continue
                log(f"[RUN ] {name}")
                rc = action()
                ok = (rc in (0, None)) and (done() or name in
                                            ("preflight", "final_report", "error_pack")
                                            or DRY)
                results[name] = "ok" if ok else f"FAILED rc={rc}"
                log(f"[{'OK  ' if ok else 'FAIL'}] {name}")
            except Exception:
                results[name] = "EXCEPTION"
                log(f"[FAIL] {name}\n{traceback.format_exc()}")
        morning_report()
    finally:
        release_lock()
    log("=== orchestrator end: " + json.dumps(results) + " ===")
    if DRY:
        print("\nDRY-RUN REPORT:")
        for n, r in results.items():
            print(f"  [{'GREEN' if r in ('ok', 'done-prior') else 'RED'}] {n}: {r}")


if __name__ == "__main__":
    main()
