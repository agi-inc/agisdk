#!/usr/bin/env python3
"""Manual BrowserGym agent wired through the harness.

Edit the CONFIG section below to change what gets executed. By default we run
all v2 omnizon tasks once, with the browser visible and demo highlights on.
"""

from agisdk import REAL
from agisdk.REAL.demo_agent.manual_agent import ManualAgentArgs

CONFIG = {
    # Task selection -------------------------------------------------------
    "task_version": "v2",          # harness will prepend this when sampling
    "task_type": "omnizon",        # run every omnizon-* task in v2
    "task_id": None,                # set to an int for a single task like omnizon-3
    "sample_tasks": 5,              # repeat each task N times
    "tasks": None,                  # optional explicit list of task names (overrides type/id)

    # Environment controls -------------------------------------------------
    "headless": False,
    "max_steps": 25,
    "browser_dimensions": (1280, 720),
    "use_html": False,
    "use_axtree": True,
    "use_screenshot": True,
    "results_dir": "./results/manual_agent",

    # Manual agent tweaks --------------------------------------------------
    "demo_mode": "default",         # "off" disables cursor highlights
    "wait_prompt": "Type your final summary (optional), then press Enter once you have finished the task.",
    "settle_wait_ms": 3000,
    "show_goal_panel": True,
    "completion_message": "Task completed manually.",
}


def main() -> None:
    agent_args = ManualAgentArgs(
        demo_mode=CONFIG["demo_mode"],
        wait_prompt=CONFIG["wait_prompt"],
        settle_wait_ms=CONFIG["settle_wait_ms"],
        show_goal_panel=CONFIG["show_goal_panel"],
        completion_message=CONFIG["completion_message"],
    )

    harness = REAL.harness(
        agentargs=agent_args,
        task_version="v2",
        task_name="omnizon-17",
        headless=CONFIG["headless"],
        max_steps=CONFIG["max_steps"],
        use_html=CONFIG["use_html"],
        use_axtree=CONFIG["use_axtree"],
        use_screenshot=CONFIG["use_screenshot"],
        browser_dimensions=CONFIG["browser_dimensions"],
        results_dir=CONFIG["results_dir"],
        sample_tasks=CONFIG["sample_tasks"],
        force_refresh=True,
    )

    results = harness.run(tasks=CONFIG["tasks"])

    print("\nFinal results:")
    for task_name, record in results.items():
        reward = record.get("cum_reward")
        elapsed = record.get("elapsed_time", 0.0)
        print(f"  {task_name}: reward={reward}, elapsed_time={elapsed:.2f}s")


if __name__ == "__main__":
    main()
