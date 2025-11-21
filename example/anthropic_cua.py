#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scrapybara import Scrapybara
from scrapybara.anthropic import Anthropic
from scrapybara.prompts import BROWSER_SYSTEM_PROMPT
from scrapybara.tools import ComputerTool

from agisdk.REAL.browsergym.webclones.evaluate import WebCloneEvaluator
from agisdk.REAL.browsergym.webclones.task_config import DEFAULT_VERSION, TaskConfig
from agisdk.REAL.tasks import all_tasks as tasks


def run_task(task: dict, run_id: str, model: Anthropic, timeout_ms: int = 420000) -> dict:
    t0 = time.time()
    tid = task["id"]
    base = task["website"]["url"]
    goal = task["goal"]
    cfg = f"{base}/config?run_id={run_id}&task_id={tid}&removePopup=true"

    print(f"\n🚀 STARTING TASK: {tid}")
    print(f"   Website: {base}")
    print(f"   Goal: {goal}")
    print(f"   Config URL: {cfg}")
    print(f"   Model: {model.name}")
    print(f"   Run ID: {run_id}")
    print(f"   Started at: {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 60)

    result = {
        "task_id": tid,
        "ok": False,
        "error": None,
        "elapsed": 0,
        "reward": None,
        "message": "",
        "env_state": None,
        "website": base,
        "goal": goal,
        "started_at": datetime.now().isoformat(),
    }

    inst = None
    try:
        print(f"🌐 [{tid}] Starting browser instance...")
        client = Scrapybara()
        inst = client.start_browser()
        print(f"✅ [{tid}] Browser started successfully")

        print(f"🤖 [{tid}] Sending task to Claude...")
        print(
            f"    Prompt: First navigate to {cfg} to configure the task, then complete this goal: {goal}"
        )

        task_timeout = 420  # 7 minutes in seconds
        start_time = time.time()
        resp = client.act(
            model=model,
            tools=[ComputerTool(inst)],
            system=BROWSER_SYSTEM_PROMPT,
            prompt=f"First navigate to {cfg} to configure the task, then complete this goal: {goal}. When the task is complete, immediately navigate to {base}/finish and extract the JSON from the <pre> element on that page. Return only the JSON content from the finish page.",
        )
        if time.time() - start_time > task_timeout:
            raise TimeoutError(f"Task {tid} exceeded 7-minute timeout")

        print(
            f"💬 [{tid}] Claude response: {resp.text[:200]}{'...' if len(resp.text) > 200 else ''}"
        )

        print(f"📊 [{tid}] Parsing final results from response...")

        env_state = None
        try:
            env_state = json.loads(resp.text)
        except (json.JSONDecodeError, TypeError):
            import re

            json_match = re.search(r"\{.*\}", resp.text, re.DOTALL)
            if json_match:
                try:
                    env_state = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        if env_state is None:
            env_state = {
                "error": "Could not extract JSON from response",
                "response": resp.text,
            }

        result["env_state"] = env_state
        print(f"\n=== ENV STATE for {tid} ===")
        print(json.dumps(env_state, indent=2))

        result["response"] = resp.text

        print(f"🏆 [{tid}] Evaluating task performance...")
        task_version = task.get("version", DEFAULT_VERSION)
        evaluator = WebCloneEvaluator(TaskConfig(tid, task_version))
        reward, _, msg, _ = evaluator.evaluate(env_state=env_state, model_response=resp.text or "")
        result.update(ok=True, reward=reward, message=msg)

        success = reward > 0
        result["success"] = success

        elapsed = time.time() - t0
        print(f"✅ [{tid}] TASK COMPLETED!")
        print(f"   Reward: {reward}")
        print(f"   Success: {success}")
        print(f"   Status: {msg}")
        print(f"   Duration: {elapsed:.2f}s")
        print(f"   Completed at: {datetime.now().strftime('%H:%M:%S')}")

        if inst:
            print(f"🔄 [{tid}] Closing browser after successful completion...")
            inst.stop()
            inst = None

    except Exception as e:
        elapsed = time.time() - t0
        result["error"] = str(e)
        print(f"❌ [{tid}] TASK FAILED!")
        print(f"   Error: {e}")
        print(f"   Duration: {elapsed:.2f}s")
        print(f"   Failed at: {datetime.now().strftime('%H:%M:%S')}")

    finally:
        result["elapsed"] = time.time() - t0
        result["elapsed_time"] = result["elapsed"]
        result["finished_at"] = datetime.now().isoformat()
        result["start_time"] = result["started_at"]
        result["end_time"] = result["finished_at"]
        if inst:
            print(f"🔄 [{tid}] Stopping browser instance...")
            inst.stop()
        print("=" * 60)

    return result


def get_results_folder() -> Path:
    return Path("anthropic_cua_results")


def load_existing_results() -> dict[str, Any]:
    results_folder = get_results_folder()
    existing_tasks = {}

    if results_folder.exists():
        for task_file in results_folder.glob("task_*.json"):
            try:
                with open(task_file) as f:
                    task_data = json.load(f)
                    task_id = task_data.get("task_id")
                    if task_id:
                        existing_tasks[task_id] = task_data
            except (OSError, json.JSONDecodeError) as e:
                print(f"⚠️ Could not load task file {task_file}: {e}")

    return {"tasks": existing_tasks}


def save_task_result(task_result: dict[str, Any], run_name: str) -> None:
    results_folder = get_results_folder()
    results_folder.mkdir(exist_ok=True)

    task_id = task_result.get("task_id", "unknown")
    task_file = results_folder / f"task_{task_id}.json"

    individual_task = {
        "task_id": task_id,
        "run_name": run_name,
        "timestamp": task_result.get("start_time", datetime.now(timezone.utc).isoformat()),
        "model": "Anthropic-CUA",
        "success": task_result.get("success", False),
        "reward": task_result.get("reward", 0),
        "elapsed_time": task_result.get("elapsed_time", 0),
        "env_state": task_result.get("env_state", {}),
        "model_response": task_result.get("response", ""),
        "eval_message": task_result.get("message", ""),
        "error": task_result.get("error"),
        "start_time": task_result.get("start_time"),
        "end_time": task_result.get("end_time"),
        "website": task_result.get("website", ""),
        "goal": task_result.get("goal", ""),
    }

    with open(task_file, "w") as f:
        json.dump(individual_task, f, indent=2)

    print(f"📄 Task {task_id} saved to: {task_file}")


def save_summary_results(all_results: dict[str, Any], run_name: str) -> None:
    results_folder = get_results_folder()
    results_folder.mkdir(exist_ok=True)

    tasks = all_results.get("tasks", {})
    completed_tasks = [t for t in tasks.values() if t.get("success") is not None]
    successful_tasks = [t for t in completed_tasks if t.get("success", False)]

    summary = {
        "run_name": run_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": "Anthropic-CUA",
        "total_tasks": len(completed_tasks),
        "successful_tasks": len(successful_tasks),
        "failed_tasks": len(completed_tasks) - len(successful_tasks),
        "success_rate": len(successful_tasks) / len(completed_tasks) * 100
        if completed_tasks
        else 0,
        "avg_time": sum(t["elapsed_time"] for t in completed_tasks) / len(completed_tasks)
        if completed_tasks
        else 0,
        "total_time": sum(t["elapsed_time"] for t in completed_tasks),
    }

    summary_file = results_folder / "summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"📊 Summary saved to: {summary_file}")


def is_task_completed(task_id: str, existing_results: dict[str, Any]) -> bool:
    tasks = existing_results.get("tasks", {})
    task_result = tasks.get(task_id)
    return task_result is not None and task_result.get("success", False)


def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    default_name = f"Anthropic_CUA_{ts}"

    p = argparse.ArgumentParser("Scrapybara-Claude REAL benchmark")
    p.add_argument(
        "--filter",
        default="omnizon-1",
        help="Task id (or prefix) to run, e.g. `omnizon` for all matching, or `all` for all tasks",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Thread pool size (one browser per worker)",
    )
    p.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Disable headless mode for debugging",
    )
    p.add_argument("--eval-api-key", default="", help="REAL-Evals API key (optional)")
    p.add_argument("--run-name", default=default_name)
    p.add_argument("--run-id", default="ce41693c-babe-4192-a932-d45e45804308")
    args = p.parse_args()

    model = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    run_id = args.run_id

    existing_results = load_existing_results()
    print(f"📁 Results folder: {get_results_folder()}")

    completed_count = sum(
        1 for task in existing_results.get("tasks", {}).values() if task.get("success", False)
    )
    if completed_count > 0:
        print(f"✅ Found {completed_count} previously completed tasks that will be skipped")

    if args.filter == "all":
        selected = tasks
        print(f"🌟 Running ALL {len(selected)} tasks with {args.workers} worker(s)")
        print("   This will take a significant amount of time (7 minutes per task)")
        print(f"   Estimated total time: {len(selected) * 7 / args.workers:.1f} minutes")
    else:
        selected = [t for t in tasks if t["id"].startswith(args.filter)]
        print(f"🚀 Running {len(selected)} task(s) with {args.workers} worker(s)")

    tasks_to_run = [t for t in selected if not is_task_completed(t["id"], existing_results)]
    skipped_count = len(selected) - len(tasks_to_run)

    if skipped_count > 0:
        print(f"⏭️  Skipping {skipped_count} already completed tasks")

    print(f"🎯 Running {len(tasks_to_run)} remaining task(s)")
    print("   Each task has a 7-minute timeout")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(run_task, t, run_id, model) for t in tasks_to_run]
        for f in as_completed(futs):
            result = f.result()
            existing_results["tasks"][result["task_id"]] = result
            save_task_result(result, args.run_name)

    all_tasks = existing_results.get("tasks", {})
    completed_tasks = [t for t in all_tasks.values() if t.get("success") is not None]
    successful = [t for t in completed_tasks if t.get("success", False)]
    failed = [t for t in completed_tasks if not t.get("success", False)]
    success_rate = len(successful) / len(completed_tasks) * 100 if completed_tasks else 0
    avg_time = (
        sum(t["elapsed_time"] for t in completed_tasks) / len(completed_tasks)
        if completed_tasks
        else 0
    )

    print("🎉 BENCHMARK RESULTS")
    print(f"Tasks completed successfully: {len(successful)}/{len(completed_tasks)}")
    print(f"Success rate: {success_rate:.2f}%")
    print(f"Average time: {avg_time:.2f} seconds")
    print(f"Total time: {sum(t['elapsed_time'] for t in completed_tasks):.2f} seconds")

    if failed:
        print(f"Failed tasks: {len(failed)}")
        for task in failed:
            print(f"  - {task['task_id']}: {task.get('error', 'Unknown error')}")

    save_summary_results(existing_results, args.run_name)


if __name__ == "__main__":
    main()
