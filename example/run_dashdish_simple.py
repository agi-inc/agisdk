#!/usr/bin/env python3
"""
Test multiple webclones tasks with GPT-4o

Usage:
    export OPENAI_API_KEY="your-key"
    python run_dashdish_simple.py
"""

import sys
from pathlib import Path

# Use local source code instead of installed package
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agisdk import REAL

# Define the tasks you want to test (2 random tasks from each category except flyunified and gocalendar)
tasks = [
    "v2.dashdish-3",
    "v2.dashdish-10",
    "v2.gomail-2",
    "v2.gomail-4",
    "v2.marrisuite-3",
    "v2.marrisuite-12",
    "v2.networkin-11",
    "v2.networkin-17",
    "v2.omnizon-4",
    "v2.omnizon-10",
    "v2.opendining-7",
    "v2.opendining-11",
    "v2.staynb-4",
    "v2.staynb-7",
    "v2.topwork-3",
    "v2.topwork-4",
    "v2.udriver-10",
    "v2.udriver-3",
    "v2.zilloft-14",
    "v2.zilloft-3",
]
# Run each task
for task_name in tasks:
    print(f"\n{'=' * 60}")
    print(f"🚀 Running task: {task_name}")
    print(f"{'=' * 60}")

    # Create harness for this task
    harness = REAL.harness(
        model="o3",  # GPT-4o agent
        task_name=task_name,  # Current task
        headless=False,
        use_cache=False,
    )

    # Run and print results
    results = harness.run()

    # Display results
    for task, result in results.items():
        success = result.get("cum_reward", 0) == 1
        print(f"\n{'✅ SUCCESS' if success else '❌ FAILURE'}: {task}")
        print(f"Time: {result.get('elapsed_time', 0):.2f}s")
        print(f"Reward: {result.get('cum_reward', 0)}")
