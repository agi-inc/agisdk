import argparse
import asyncio
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from browser_use import Agent

from agisdk.REAL.browsergym.webclones.evaluate import WebCloneEvaluator
from agisdk.REAL.browsergym.webclones.task_config import DEFAULT_VERSION, TaskConfig

# Global browser storage per thread
worker_browsers = {}


async def run_task(task: dict, run_id: str, llm_model) -> dict:
    """____________________________________________ Core Logic ____________________________________________"""

    t0 = time.time()
    tid, goal, base = task["id"], task["goal"], task["website"]["url"]
    cfg = f"{base}/config?run_id={run_id}&task_id={tid}&removePopup=true"

    result = {
        "id": tid,
        "task_id": tid,
        "start_time": datetime.now().isoformat(),
        "ok": False,
        "success": False,
        "error": None,
        "response": None,
        "elapsed_time": 0,
        "t": 0,
    }

    # Each task gets its own browser session to avoid conflicts
    try:
        print(f"Starting task: {tid} - {goal[:50]}...")

        # Create detailed task instruction
        detailed_task = f"""
        Complete this web automation task: {goal}

        Current context:
        - You are starting at the configuration page: {cfg}
        - Main website base URL: {base}
        - Task ID: {tid}
        - Run ID: {run_id}

        Steps to follow:
        1. Navigate to the configuration page first to set up the environment
        2. Then navigate to the main website base URL
        3. Complete the required task: {goal}
        4. Extract any relevant information or responses
        5. Navigate to the finish page when complete

        Important: Be thorough and precise in your actions. If you encounter any popups or overlays, handle them appropriately.
        """

        # Get or create browser for this worker thread
        thread_id = threading.get_ident()
        if thread_id not in worker_browsers:
            worker_browsers[thread_id] = Agent(
                task=detailed_task,
                llm=llm_model,
                use_vision=True,
                save_conversation_path=None,
                generate_gif=False,
            )
        else:
            # If browser exists, update it with the new task
            worker_browsers[thread_id].task = detailed_task

        agent = worker_browsers[thread_id]

        # Execute the main task
        start_act_time = time.time()
        print(f"Agent starting execution for task {tid}...")

        # Run the agent
        agent_result = await agent.run()
        act_elapsed = time.time() - start_act_time

        print(f"Task {tid} action completed in {act_elapsed:.2f} seconds")

        # Extract response from agent result
        answer = ""
        for attr in ["response", "message", "content"]:
            if hasattr(agent_result, attr) and getattr(agent_result, attr):
                answer = str(getattr(agent_result, attr))
                break
        else:
            answer = str(agent_result) if agent_result else ""

        result["response"] = answer

        """____________________________________________ Finish & Evaluation ____________________________________________"""

        # Get the current page from browser session to navigate to finish
        if agent.browser and hasattr(agent.browser, "page"):
            page = agent.browser.page

            # Navigate to finish page
            finish_url = f"{base}/finish"
            print(f"Navigating to finish page: {finish_url}")
            await page.goto(finish_url, timeout=30000)

            # Wait for and get the pre element content for evaluation
            try:
                await page.wait_for_selector("pre", timeout=10000)
                pre_element = await page.query_selector("pre")

                if not pre_element:
                    raise ValueError("Pre element not found on finish page")

                env_state = await pre_element.inner_text()
                env_state_json = json.loads(env_state)

                task_version = task.get("version", DEFAULT_VERSION)
                task_config = TaskConfig(tid, task_version)
                evaluator = WebCloneEvaluator(task_config=task_config)
                reward, done, message, info = evaluator.evaluate(
                    env_state=env_state_json, model_response=result["response"]
                )
                print(f"Evaluation result: {message}, Reward: {reward}")

                result.update(
                    {
                        "reward": reward,
                        "done": done,
                        "eval_message": message,
                        "eval_info": info,
                    }
                )

            except (ImportError, json.JSONDecodeError, ValueError) as e:
                print(f"Evaluation error: {e}")
                result["error"] = str(e)
            except Exception as e:
                print(f"Unexpected evaluation error: {e}")
                result["error"] = f"Evaluation error: {str(e)}"

        result["ok"] = True
        result["success"] = True

    except Exception as exc:
        result["error"] = str(exc)
        print(f"Error on task {tid}: {exc}")
        import traceback

        traceback.print_exc()

    elapsed = time.time() - t0
    result.update({"elapsed_time": elapsed, "t": elapsed, "end_time": datetime.now().isoformat()})

    print(f"Completed task {tid} in {elapsed:.2f} seconds. Success: {result['success']}")
    return result


def run_task_sync(task: dict, run_id: str, llm_model) -> dict:
    return asyncio.run(run_task(task, run_id, llm_model))


def main() -> None:
    # _______________________Setup_____________________
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"BrowserUse_{ts}"
    api_key = ""

    # Use your existing run_id or generate a new one
    run_id = "b0c2f93d0c461eed5b99b51ed6e934baa600ba0907185edd93c949ab20f34d21"

    p = argparse.ArgumentParser("Browser-Use benchmark")
    p.add_argument("--api-key", default=api_key)
    p.add_argument("--run-name", default=run_name)
    p.add_argument("--workers", type=int, default=1)  # Working only with 1 worker for now.
    p.add_argument(
        "--filter", default="all"
    )  # Default to just one task, use --filter all to run all tasks
    p.add_argument("--no-headless", action="store_false")  # store_false means no browser mode.
    p.add_argument("--run-id", default=run_id)

    # New arguments for browser-use specific configuration
    p.add_argument(
        "--model-type",
        choices=["openai", "claude", "gemini", "deepseek"],
        default="openai",
        help="LLM model type to use",
    )
    p.add_argument("--max-retries", type=int, default=1, help="Number of retries for failed tasks")
    p.add_argument("--timeout", type=int, default=300, help="Timeout per task in seconds")

    args = p.parse_args()

    # Setup LLM model
    print(f"Setting up {args.model_type} model...")
    try:
        from langchain_openai import ChatOpenAI

        llm_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        print(f"✓ {args.model_type} model configured successfully")
    except Exception as e:
        print(f"✗ Error setting up {args.model_type} model: {e}")
        return

    # Load and filter tasks
    try:
        from agisdk.REAL.tasks import all_tasks as tasks

        # Select tasks based on filter
        if args.filter == "all":
            selected = tasks
        else:
            selected = [t for t in tasks if t["id"] == args.filter]

        print(f"{len(selected)} tasks selected → {args.workers} workers")

        if not selected:
            print(f"No tasks found matching filter: {args.filter}")
            return

    except Exception as e:
        print(f"Error loading tasks: {e}")
        return

    # Prepare for execution
    results = []
    start_time = time.time()
    headless = not args.no_headless

    print("\nStarting browser-use benchmark:")
    print(f"- Model: {args.model_type}")
    print(f"- Tasks: {len(selected)}")
    print(f"- Workers: {args.workers}")
    print(f"- Headless: {headless}")
    print(f"- Run ID: {run_id}")
    print("-" * 50)

    # Execute tasks with progress tracking
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        # Submit all tasks
        future_to_task = {
            pool.submit(run_task_sync, task, run_id, llm_model): task for task in selected
        }

        completed_count = 0
        successful_count = 0

        # Process completed tasks
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result(timeout=args.timeout)
                results.append(result)

                completed_count += 1
                if result.get("success", False):
                    successful_count += 1
                    print(f"✓ Task {task['id']}: Success ({result.get('elapsed_time', 0):.1f}s)")
                else:
                    error_msg = result.get("error", "Unknown error")
                    print(f"✗ Task {task['id']}: Failed - {error_msg}")

                # Print progress every few tasks
                if completed_count % max(1, len(selected) // 10) == 0:
                    print(
                        f"Progress: {completed_count}/{len(selected)} completed, {successful_count} successful"
                    )

            except Exception as e:
                print(f"✗ Task {task['id']}: Exception - {str(e)}")
                # Create error result
                error_result = {
                    "id": task["id"],
                    "task_id": task["id"],
                    "start_time": datetime.now().isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "ok": False,
                    "success": False,
                    "error": str(e),
                    "response": None,
                    "elapsed_time": 0,
                    "t": 0,
                }
                results.append(error_result)
                completed_count += 1

    # Calculate summary statistics
    total_time = time.time() - start_time
    successful_tasks = [r for r in results if r.get("ok", False)]
    success_rate = len(successful_tasks) / len(results) if results else 0
    avg_time = sum(r.get("elapsed_time", 0) for r in results) / len(results) if results else 0

    # Print detailed results
    print("\n" + "=" * 60)
    print("BROWSER-USE BENCHMARK RESULTS")
    print("=" * 60)
    print(f"✓ {len(successful_tasks)}/{len(results)} tasks succeeded ({success_rate:.2%})")
    print(f"Average time per task: {avg_time:.2f} seconds")
    print(f"Total execution time: {total_time:.2f} seconds")

    # Get results from REAL Evals (if available)
    try:
        pass  # Uncomment when you have this function available
    except Exception as e:
        print(f"Could not retrieve REAL Evals results: {e}")

    # Print final summary
    print("\nRun Summary:")
    print(f"Timestamp: {ts}")
    print(f"Run ID: {run_id}")
    print(f"Model: {args.model_type}")
    print(f"Tasks: {len(results)}")
    print(f"Success: {len(successful_tasks)}")
    print(f"Success Rate: {success_rate:.2%}")
    print(f"Avg Time: {avg_time:.2f} seconds")
    print(f"Total Time: {total_time:.2f} seconds")


if __name__ == "__main__":
    main()
