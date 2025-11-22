# REAL Hackathon – Submission Guide

Welcome to the REAL Hackathon – a competition focused on building browser agents that are both **accurate** and **fast** on real-world benchmark environments. This document explains what you’re optimizing for, how to submit, and what we’ll do with your code once it lands in our hands.

---

## What You’re Optimizing For
- **Accuracy**: Agents must complete as many benchmark tasks as possible. We score these tasks automatically via the evaluator.
- **Speed**: Each task’s runtime (from the evaluator’s `time_taken`) matters just as much as accuracy. Using only the largest models (GPT‑5, Claude 4.5, etc.) may give you great accuracy but poor latency, which hurts your score.
- **Balance**: You need a blend of smart reasoning and fast execution. Lower-latency models with a well-crafted agent often outperform bigger-but-slower setups.

---

## Required Workflow
1. **Clone & Setup**
   - Follow the instructions in `README.md` (`uv sync`, set API keys, etc.).

2. **Run the Example Agent**
   - Execute `uv run ./scripts/bench.py` to see the reference `QwenAgent` in action.
   - The Qwen agent is *only* an example; do **not** submit it as-is. Use it to understand the shape of a complete agent implementation.

3. **Build Your Own Agent**
   - Copy the structure under `src/agi_agents/qwen/` and drop your custom agent in `src/agi_agents/<your_agent>/`.
   - Implement the `BaseAgent` interface (see Qwen for reference).

4. **Wire It Up**
   - Update `scripts/bench.py` to import and instantiate your agent (instead of `QwenAgent`).
   - Ensure that running `uv run ./scripts/bench.py` executes **your** agent across the benchmark.

5. **Validate Locally**
   - The repository ships with 16 public tasks under `benchmarks/hackathon/`.
   - Run the full benchmark and verify the output includes both the accuracy (pass/fail counts) and the evaluator’s `time_taken`.

---

## What Happens After You Submit
- We’ll pull your repo, install dependencies, and run `uv run ./scripts/bench.py` exactly as you’ve set it up.
- We will **swap the benchmark tasks** with a hidden held-out set; your agent must be robust enough to handle unseen scenarios.
- We’ll record both the pass/fail stats and total benchmark time from the evaluator outputs to compute your final score.

---

## Final Checklist
- [ ] `uv run ./scripts/bench.py` finishes without manual edits.
- [ ] The script instantiates **your** agent by default.
- [ ] All dependencies (API keys, env vars) are clearly documented in `README.md`.
- [ ] You’ve confirmed accuracy and time on the provided 16 tasks.

Good luck, and may the fastest-smartest agent win!
