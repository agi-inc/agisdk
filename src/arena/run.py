import asyncio
import traceback
import glob
from pathlib import Path
from typing import List, Any, Union, Optional
import os.path as osp

from arena.browser import AgentBrowser
from arena.task import Task
from arena.execution import TaskExecution


class RunHarness:
    def __init__(
        self,
        agent,
        tasks: Union[str, List[str]] = None,
        parallel: int = 10,
        sample_count: int = 1,
        max_steps: int = 60,
        ignore_errors: bool = False,
        # Browser
        headless: bool = True,
        width: int = 1920,
        height: int = 1080,
        wait_until: str = "load",
        timeout: int = 30000,
    ):
        self.agent = agent
        self.ignore_errors = ignore_errors

        if tasks is None:
            raise ValueError("Must specify either 'tasks' or 'resume' parameter")
        parsed_tasks = self._parse_tasks(tasks)

        # Print all detected tasks
        print(f"Detected {len(parsed_tasks)} tasks:")
        for i, task_spec in enumerate(parsed_tasks):
            print(f"  Task {i}: {task_spec}")

        self.parallel = parallel
        self.sample_count = sample_count
        self.max_steps = max_steps
        # Convert to format: (task_index, task_spec, sample_indices)
        self.tasks = [
            (idx, task_spec, list(range(self.sample_count)))
            for idx, task_spec in enumerate(parsed_tasks)
        ]

        self.browser_kwargs = dict(
            headless=headless,
            width=width,
            height=height,
            wait_until=wait_until,
            timeout=timeout,
        )

        self.successful_count = 0
        self.failed_count = 0
        self.total_task_time = 0.0

    def _parse_tasks(
        self, tasks: Union[str, List[str]]
    ) -> List[str]:
        """Parse and expand task specifications into a list of task file paths."""

        if isinstance(tasks, str):
            tasks = [tasks]

        expanded_tasks = []
        for task_spec in tasks:
            # Handle comma-separated lists
            for task in task_spec.split(","):
                task = task.strip()
                if not task:
                    continue

                # Handle glob patterns
                if "*" in task or "?" in task:
                    glob_matches = glob.glob(task, recursive=True)
                    if not glob_matches:
                        raise ValueError(
                            f"No files found matching glob pattern: {task}"
                        )
                    expanded_tasks.extend(sorted(glob_matches))
                else:
                    # Tree-search match for task specification
                    matches = self._find_task_matches(task)
                    if matches:
                        expanded_tasks.extend(matches)
                    else:
                        raise ValueError(f"No tasks found matching: {task}")

        return expanded_tasks

    def _find_task_matches(self, spec: str) -> List[str]:
        """
        Find all task files that match the given specification.
        Returns all matching .json files, sorted.
        """
        benchmarks_dir = Path(
            osp.join(osp.dirname(osp.dirname(osp.dirname(__file__))), "src/benchmarks")
        )
        if not benchmarks_dir.exists():
            return []

        matches = []

        # Search all .json files in benchmarks directory
        for json_file in benchmarks_dir.rglob("*.json"):
            path_str = str(json_file)

            # Match if spec appears anywhere in the path
            if spec in path_str:
                matches.append(path_str)

        return sorted(matches)

    async def _run_single_task(
        self,
        task_spec: str,
        task_idx: int,
        sample_idx: int,
        max_steps: int,
        ignore_errors: bool = False,
    ) -> Any:
        """Run a single task with its own agent and browser"""
        browser = None
        task_execution_id = None
        task = None
        state = None

        try:
            # Create browser with kwargs
            browser = AgentBrowser(**self.browser_kwargs)
            await browser.start()

            # Create Task object from task specification
            task = await Task.from_spec(task_spec, browser)

            # Create TaskExecution
            task_execution = TaskExecution(
                task=task,
                agent=self.agent,
                browser=browser,
                max_steps=self.max_steps,
                task_execution_id=task_execution_id,
                ignore_errors=ignore_errors,
            )

            # Run task and get state and result
            state, result = await task_execution.run()

            # return values
            step_count = state.step

            # Update progress display after task completion
            if result.success:
                self.successful_count += 1
            else:
                self.failed_count += 1
            print(
                f"Task {task_idx} sample {sample_idx} finished with {step_count} steps and success={result.success}"
            )
            self._record_result_time(result)

            print(
                f"Success: {self.successful_count}, Failures: {self.failed_count}"
            )
            return result

        except Exception as e:
            print(traceback.format_exc())
            self.failed_count += 1

            if not task:
                return None

            print(f"Task {task_idx} sample {sample_idx} failed: {e}")

            return None
        finally:
            if browser:
                await browser.stop()

    async def run(self, tasks=None) -> None:
        if not tasks:
            tasks = self.tasks
        total_runs = len(tasks) * self.sample_count
        print(
            f"Running {len(tasks)} tasks x {self.sample_count} samples = {total_runs} total runs with parallelism {self.parallel} with max steps {self.max_steps}"
        )

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.parallel)

        async def run_with_semaphore(task_spec, task_idx: int, sample_idx: int):
            async with semaphore:
                result = await self._run_single_task(
                    task_spec,
                    task_idx,
                    sample_idx,
                    self.max_steps,
                    self.ignore_errors,
                )
                return result

        # Create all task-sample combinations
        all_runs = []
        for task_index, task_spec, sample_indices in tasks:
            for sample_idx in sample_indices:
                all_runs.append((task_spec, task_index, sample_idx))

        # Run all task-sample combinations
        await asyncio.gather(
            *[
                run_with_semaphore(task_spec, task_idx, sample_idx)
                for task_spec, task_idx, sample_idx in all_runs
            ],
            return_exceptions=False,
        )
        print(
            f"Success: {self.successful_count}, Failures: {self.failed_count}, total benchmark time: {self.total_task_time:.2f}s"
        )

    def _record_result_time(self, result: Optional["ExperimentResult"]) -> None:
        if result is None:
            return

        time_taken = getattr(result, "time_taken", None)

        if time_taken is None:
            details = getattr(result, "details", None)
            if isinstance(details, dict):
                time_taken = details.get("time_taken")
            elif isinstance(details, (list, tuple)):
                for item in details:
                    if isinstance(item, dict) and "time_taken" in item:
                        time_taken = item["time_taken"]
                        break

        if isinstance(time_taken, (int, float)):
            self.total_task_time += float(time_taken)
