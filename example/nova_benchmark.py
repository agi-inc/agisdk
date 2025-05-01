#!/usr/bin/env python3
# Benchmark script for running all tasks headlessly and in parallel using NovaAct

from nova_act import NovaAct
from agisdk.REAL.tasks import all_tasks as tasks
import urllib.parse
import concurrent.futures
import time
import argparse
import os
import json
from datetime import datetime


def run_task_with_timeout(task, run_id, headless=True, timeout=300):
    """Run a single task with NovaAct and return the results, with timeout handling."""
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_task_impl, task, run_id, headless)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            task_id = task["id"]
            print(f"Task {task_id} timed out after {timeout} seconds")
            return {
                "task_id": task_id,
                "start_time": datetime.now().isoformat(),
                "end_time": datetime.now().isoformat(),
                "success": False,
                "error": f"Task timed out after {timeout} seconds",
                "response": None,
                "elapsed_time": timeout
            }

def run_task_impl(task, run_id, headless=True):
    """Implementation of running a single task with NovaAct."""
    start_time = time.time()
    task_id = task["id"]
    goal = task["goal"]
    url = task["website"]["url"]
    config_url = url + f"/config?run_id={run_id}&task_id={task_id}"
    
    result = {
        "task_id": task_id,
        "start_time": datetime.now().isoformat(),
        "success": False,
        "error": None,
        "response": None,
        "elapsed_time": 0
    }
    
    try:
        print(f"Starting task: {task_id} - {goal[:50]}...")
        with NovaAct(starting_page=config_url, headless=headless) as nova:
            nova.go_to_url(url)
            start_act_time = time.time()
            nova_result = nova.act(goal)
            act_elapsed = time.time() - start_act_time
            
            print(f"Task {task_id} action completed in {act_elapsed:.2f} seconds")
            response = nova_result.response if nova_result.response is not None else "No response"
            
            # Submit the response
            encoded_response = urllib.parse.quote(response)
            nova.go_to_url(url + "/submit?retrieved_answer=" + encoded_response)
            
            result["success"] = True
            result["response"] = response
    except Exception as e:
        result["error"] = str(e)
        print(f"Error on task {task_id}: {e}")
    
    elapsed = time.time() - start_time
    result["elapsed_time"] = elapsed
    result["end_time"] = datetime.now().isoformat()
    
    print(f"Completed task {task_id} in {elapsed:.2f} seconds. Success: {result['success']}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Run NovaAct benchmarks on all tasks in parallel")
    parser.add_argument("--run-id", type=str, required=True, help="Run ID from realevals.xyz")
    parser.add_argument("--max-workers", type=int, default=4, help="Maximum number of parallel workers")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds for each task")
    parser.add_argument("--output-dir", type=str, default="./results", help="Directory to save results")
    parser.add_argument("--filter", type=str, default=None, help="Filter tasks by substring in task ID")
    parser.add_argument("--no-headless", action="store_true", help="Run with browser visible (not headless)")
    
    args = parser.parse_args()
    
    # Filter tasks if specified
    filtered_tasks = tasks
    if args.filter:
        filtered_tasks = [task for task in tasks if args.filter in task["id"]]
    
    print(f"Running {len(filtered_tasks)} tasks with {args.max_workers} parallel workers")
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Generate a timestamp for the results file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(args.output_dir, f"nova_benchmark_{timestamp}.json")
    
    # Run tasks in parallel
    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_task = {executor.submit(run_task_with_timeout, task, args.run_id, not args.no_headless, args.timeout): task for task in filtered_tasks}
        
        for future in concurrent.futures.as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                all_results.append(result)
                
                # Save intermediate results
                with open(results_file, 'w') as f:
                    json.dump(all_results, f, indent=2)
            except Exception as e:
                print(f"Task {task['id']} generated an exception: {e}")
    
    # Calculate summary statistics
    successful_tasks = [r for r in all_results if r["success"]]
    success_rate = len(successful_tasks) / len(filtered_tasks) if filtered_tasks else 0
    avg_time = sum(r["elapsed_time"] for r in all_results) / len(all_results) if all_results else 0
    
    summary = {
        "timestamp": timestamp,
        "run_id": args.run_id,
        "total_tasks": len(filtered_tasks),
        "successful_tasks": len(successful_tasks),
        "success_rate": success_rate,
        "average_time": avg_time,
        "results": all_results
    }
    
    # Save final results with summary
    with open(results_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nBenchmark complete!")
    print(f"Success rate: {success_rate:.2%} ({len(successful_tasks)}/{len(filtered_tasks)})")
    print(f"Average time per task: {avg_time:.2f} seconds")
    print(f"Results saved to: {results_file}")


if __name__ == "__main__":
    main()
