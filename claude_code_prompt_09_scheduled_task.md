# Prompt for Claude Code — Stage 9: Windows scheduled task for the overnight run

Copy everything below the line into Claude Code. Complements Stage 8 (the overnight
queue): this makes it LAUNCH ITSELF at the quota reset and survive crashes/reboots.

---

## Build the unattended-run infrastructure

1. **Orchestrator script** `run_overnight.py` (repo root): executes the Stage-8 queue
   exactly as specified (pre-flight asserts → TSLA→NFLX→AMZN→MSFT→COIN train+test →
   no-memory TSLA → portfolio layer → RESULTS_FINMEM_OURS.md + CSV + error pack →
   STATUS.md morning summary). Requirements:
   - **Idempotent + resumable**: every invocation checks completed checkpoints and
     continues from the next unfinished step; running it twice must never duplicate
     work or double-spend.
   - **Lockfile guard** (no two instances), heartbeat line to `overnight.log` every
     few minutes, full tracebacks to the log on any failure, then continue with the
     next queue item.
   - Budget guards unchanged: free pool first, paid gpt-4.1-mini overflow hard-capped
     at $3.00, ada-002 ~$1.50, never straddle the boundary silently.

2. **Windows Task Scheduler entries** (use `schtasks` so it's scriptable; log the
   exact commands you register):
   - **Main trigger: 03:10 Israel time** (≈ 00:05 UTC + margin, the pool reset) —
     run `run_overnight.py`.
   - **Watchdog: every 2 hours from 03:30 to 09:30** — re-invoke the orchestrator;
     thanks to idempotency+lockfile this is a free retry if a crash/reboot killed it,
     and a no-op if it's alive or done.
   - **Morning report: 08:30** — regenerate STATUS.md summary + verify
     RESULTS_FINMEM_OURS.md exists; if the grid is incomplete, write exactly what
     remains and why.
   - Tasks run whether or not Dan is logged in ("Run whether user is logged on or
     not" / highest privileges as needed), working directory = repo root, venv python
     full path (no PATH assumptions).

3. **Machine prerequisites — print a one-line checklist for Dan to confirm tonight:**
   power plan set to never sleep (or wake timers enabled for 03:05), laptop lid/AC
   policy if relevant, disk space ≥ 2GB free, `.env` present.

4. **Test the whole chain NOW without spending tokens:** dry-run mode flag
   (`--dry-run`) that walks the queue with mocked LLM calls, exercises lockfile,
   resume logic, and the scheduled-task invocation path (trigger the task manually
   once via `schtasks /run`), then report green/red per item.

5. Register everything, show me the `schtasks /query` output for the three tasks,
   and update STATUS.md ("Overnight automation: ARMED, next fire 03:10").
