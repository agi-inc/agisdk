#!/usr/bin/env python3
"""
Upload v1 Final Diffs with Model Responses

This script uploads pairs of env_state and model_response files to the leaderboard API.

Usage:
    python upload_v1_pairs.py --input-dir <dir> --run-id <run_id>

Input Format:
    Directory containing pairs of files:
    - {task_id}_env_state.json: Contains the final_state (env_state)
    - {task_id}_model_response.json: Contains the retrieved_answer (model response text)

    Example:
    finaldiffs/
      dashdish-1_env_state.json
      dashdish-1_model_response.json
      omnizon-3_env_state.json
      omnizon-3_model_response.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print(f"Error: Missing 'requests' library. Please install it:")
    print(f"  pip install requests")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Total v1 tasks for score calculation
TOTAL_V1_TASKS = 112

# Leaderboard API base URL
LEADERBOARD_API_BASE = "https://www.realevals.ai/api"


def load_json_file(file_path: Path, allow_empty: bool = False) -> Optional[any]:
    """Load JSON from file, handling double-encoded strings and empty files."""
    try:
        with open(file_path) as f:
            content = f.read().strip()

        # If empty or "No response", return None (allowed for jmespath tasks)
        if not content or content == "" or content == "\"No response\"":
            if allow_empty:
                return None
            else:
                logger.warning(f"Empty or no response in {file_path}")
                return None

        # Try to parse as JSON
        data = json.loads(content)

        # If it's a string, try to parse again (double-encoded)
        if isinstance(data, str):
            data = json.loads(data)

        return data
    except json.JSONDecodeError as e:
        if allow_empty:
            logger.warning(f"Invalid JSON in {file_path}, using empty response")
            return None
        logger.error(f"Invalid JSON in {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        return None


def submit_task_pair(
    task_id: str,
    env_state: dict,
    model_response: any,
    run_id: str,
    api_base: str = None,
) -> dict:
    """
    Submit a task pair (env_state + model_response) to the leaderboard API.

    Returns:
        dict with keys: success (bool), score (float), details (str), submitted (bool)
    """
    if api_base is None:
        api_base = LEADERBOARD_API_BASE
    api_url = f"{api_base}/runs/{run_id}"

    # Convert model_response to string if it's not already
    if isinstance(model_response, list):
        # If it's a list, convert to comma-separated string
        retrieved_answer = ", ".join(str(x) for x in model_response)
    elif isinstance(model_response, dict):
        # If it's a dict, convert to JSON string
        retrieved_answer = json.dumps(model_response)
    else:
        retrieved_answer = str(model_response)

    payload = {
        "run_id": run_id,
        "task_id": task_id,
        "final_state": env_state,
        "retrieved_answer": retrieved_answer,
    }

    try:
        logger.info(f"Submitting {task_id} to leaderboard API...")
        response = requests.post(api_url, json=payload, timeout=60)

        if response.status_code == 200 or response.status_code == 201:
            result = response.json()

            # Parse evaluation results
            evals_passed = result.get("evals_passed", [])
            evals_failed = result.get("evals_failed", [])
            total_evals = len(evals_passed) + len(evals_failed)

            # Calculate score (1.0 if all passed, 0.0 if any failed)
            score = 1.0 if (len(evals_failed) == 0 and total_evals > 0) else 0.0

            details = f"Passed: {len(evals_passed)}/{total_evals} evals"
            if evals_failed:
                details += f" | Failed: {', '.join(evals_failed)}"

            return {
                "success": score > 0,
                "score": score,
                "details": details,
                "submitted": True,
                "evals_passed": evals_passed,
                "evals_failed": evals_failed,
                "response": result,
            }
        elif response.status_code == 409:
            return {
                "success": None,
                "score": 0.0,
                "details": "Already submitted (duplicate)",
                "submitted": False,
            }
        else:
            error_text = response.text
            try:
                error_json = response.json()
                error_text = error_json.get("error", error_text)
            except:
                pass

            return {
                "success": False,
                "score": 0.0,
                "details": f"API error: HTTP {response.status_code} - {error_text}",
                "submitted": False,
            }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "score": 0.0,
            "details": "API request timed out",
            "submitted": False,
        }
    except Exception as e:
        return {
            "success": False,
            "score": 0.0,
            "details": f"API error: {e}",
            "submitted": False,
        }


def find_task_pairs(input_dir: Path) -> list[tuple[str, Path, Path]]:
    """
    Find all task pairs in the input directory.

    Returns:
        List of tuples: (task_id, env_state_path, model_response_path)
    """
    env_state_files = list(input_dir.glob("*_env_state.json"))

    pairs = []
    for env_state_file in env_state_files:
        # Extract task_id from filename
        task_id = env_state_file.stem.replace("_env_state", "")

        # Find corresponding model_response file
        model_response_file = input_dir / f"{task_id}_model_response.json"

        if not model_response_file.exists():
            logger.warning(f"Missing model_response file for {task_id}, skipping")
            continue

        pairs.append((task_id, env_state_file, model_response_file))

    return sorted(pairs, key=lambda x: x[0])


def upload_task_pairs(input_dir: Path, run_id: str, api_base: str = None) -> list[dict]:
    """Upload all task pairs from a directory."""
    pairs = find_task_pairs(input_dir)

    if not pairs:
        logger.warning(f"No task pairs found in {input_dir}")
        return []

    logger.info(f"Found {len(pairs)} task pairs to upload")

    results = []
    for task_id, env_state_path, model_response_path in pairs:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {task_id}")
        logger.info(f"{'='*60}")

        # Load env_state
        env_state = load_json_file(env_state_path)
        if not env_state:
            results.append({
                "task_id": task_id,
                "error": "Failed to load env_state",
            })
            continue

        # Load model_response (allow empty for jmespath-only tasks)
        model_response = load_json_file(model_response_path, allow_empty=True)
        if model_response is None:
            # Use "No response" for tasks without text answers (jmespath tasks)
            model_response = "No response"

        # Submit to API
        api_result = submit_task_pair(task_id, env_state, model_response, run_id, api_base)

        result = {
            "task_id": task_id,
            "api": api_result,
        }
        results.append(result)

        logger.info(
            f"Result: {'PASS' if api_result['success'] else 'FAIL' if api_result['success'] is False else 'SKIP'} "
            f"(score: {api_result['score']}) "
            f"[Submitted: {api_result.get('submitted', False)}]"
        )
        logger.info(f"Details: {api_result['details']}")

    return results


def calculate_aggregate_score(results: list[dict]) -> dict:
    """
    Calculate aggregate statistics.

    Score = (tasks_passed / TOTAL_V1_TASKS) * 100
    """
    total_attempted = len([r for r in results if "api" in r])
    total_passed = len([r for r in results if r.get("api", {}).get("success", False)])
    total_score = sum(r.get("api", {}).get("score", 0.0) for r in results)
    total_skipped = len([r for r in results if r.get("api", {}).get("success") is None])

    # Calculate percentage based on total v1 tasks (112)
    percentage = (total_passed / TOTAL_V1_TASKS) * 100

    aggregate = {
        "total_v1_tasks": TOTAL_V1_TASKS,
        "tasks_attempted": total_attempted,
        "tasks_passed": total_passed,
        "tasks_failed": total_attempted - total_passed - total_skipped,
        "tasks_skipped": total_skipped,
        "total_score": total_score,
        "percentage": round(percentage, 2),
    }

    return aggregate


def main():
    parser = argparse.ArgumentParser(
        description="Upload v1 task pairs (env_state + model_response) to leaderboard"
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing task pair files",
    )

    parser.add_argument(
        "--run-id",
        required=True,
        help="Run ID for leaderboard submission",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file for detailed results",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose logging"
    )

    parser.add_argument(
        "--api-base",
        type=str,
        default="https://www.realevals.ai/api",
        help="Leaderboard API base URL (default: https://www.realevals.ai/api)",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Perform upload
    logger.info(f"Starting v1 task pair upload")
    logger.info(f"Run ID: {args.run_id}")
    logger.info(f"Leaderboard API: {args.api_base}")

    results = upload_task_pairs(args.input_dir, args.run_id, args.api_base)

    # Calculate aggregate score
    aggregate = calculate_aggregate_score(results)

    # Print summary
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    print(f"Run ID: {args.run_id}")
    print(f"Tasks Attempted: {aggregate['tasks_attempted']}")
    print(f"Tasks Passed: {aggregate['tasks_passed']}")
    print(f"Tasks Failed: {aggregate['tasks_failed']}")
    print(f"Tasks Skipped (duplicates): {aggregate['tasks_skipped']}")
    print(f"Total Score: {aggregate['total_score']}")
    print(f"\nAggregate Score: {aggregate['percentage']}%")
    print(f"  ({aggregate['tasks_passed']} / {aggregate['total_v1_tasks']} total v1 tasks)")
    print("=" * 60)

    # Save detailed results if requested
    if args.output:
        output_data = {"aggregate": aggregate, "results": results}

        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)

        logger.info(f"Detailed results saved to: {args.output}")

    # Exit with appropriate code
    sys.exit(0 if aggregate["tasks_failed"] == 0 else 1)


if __name__ == "__main__":
    main()
