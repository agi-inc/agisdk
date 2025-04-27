#!/usr/bin/env python3
"""
Core harness for running agents on browsergym tasks.
Provides a clean, simple interface for running both built-in and custom agents.
"""

import os
import glob
import random
import json
import time
import logging
import tempfile
import dataclasses
from typing import List, Dict, Optional, Any, Union, Tuple, Type
from pathlib import Path
from statistics import mean, median, stdev
import multiprocessing as mp
from functools import partial

# Import the necessary browsergym components
from agisdk.REAL.browsergym.experiments import Agent, AbstractAgentArgs, EnvArgs, ExpArgs, get_exp_result
from agisdk.REAL.demo_agent.basic_agent import DemoAgentArgs

# Worker initialization function for multiprocessing
def init_worker():
    global tempfile
    import tempfile

logger = logging.getLogger(__name__)

class harness:
    """
    A simplified harness for running browsergym tasks with various agents.
    
    Example usage with built-in agent:
        harness = REAL.harness(model="gpt-4o", leaderboard=True)
        results = harness.run()
        
    Example usage with custom agent:
        harness = REAL.harness(agentargs=YourAgentArgs(), leaderboard=True)
        results = harness.run()
    """
    
    def __init__(
        self,
        model: str = None,
        agentargs: AbstractAgentArgs = None,
        task_name: str = None,
        task_type: str = None,
        task_id: int = None,
        leaderboard: bool = False,
        run_id: str = None,
        headless: bool = True,
        max_steps: int = 25,
        use_html: bool = False,
        use_axtree: bool = True,
        use_screenshot: bool = True,
        browser_dimensions: tuple = (1280, 720),
        golden_user_data_dir: str = None,
        extensions_dir: str = None,
        viewport: dict = None,
        results_dir: str = "./results",
        parallel: bool = False,
        num_workers: int = 4,
        use_cache: bool = True,
        cache_only: bool = False,
        force_refresh: bool = False,
        sample_tasks: int = 1,
        api_key: str = None,
        run_name: str = None,
        model_id_name: str = None,
    ):
        """
        Initialize the harness with the provided configuration.
        
        Args:
            model: Name of the AI model to use (e.g., "gpt-4o")
            agentargs: Arguments for a custom agent (if not using a built-in model)
            task_name: Specific task name to run (e.g., "webclones.omnizon-1")
            task_type: Task type to run (e.g., "omnizon")
            task_id: Specific task ID within a task type
            leaderboard: Whether to submit results to a leaderboard
            run_id: Identifier for this run (required for leaderboard)
            headless: Whether to run the browser in headless mode
            max_steps: Maximum number of steps per task
            use_html: Whether to include HTML in observations
            use_axtree: Whether to include accessibility tree in observations
            use_screenshot: Whether to include screenshots in observations
            browser_dimensions: Tuple of (width, height) for browser viewport
            golden_user_data_dir: Path to browser user data directory
            extensions_dir: Path to Chrome extensions directory
            viewport: Dictionary with width and height for browser viewport
            results_dir: Directory to store results
            parallel: Whether to run tasks in parallel
            num_workers: Number of parallel workers
            use_cache: Whether to use cached results
            cache_only: Only use cached results, don't run missing tasks
            force_refresh: Force re-running tasks even if cached results exist
        """
        self.results_dir = results_dir
        self.parallel = parallel
        self.num_workers = num_workers
        self.use_cache = use_cache
        self.cache_only = cache_only
        self.force_refresh = force_refresh
        self.leaderboard = leaderboard
        self.run_id = run_id
        self.sample_tasks = sample_tasks
        
        logger.info(f"Harness initialized with model={model or 'custom'}, task={task_name or task_type}, Sampling each task {sample_tasks} times")
        # Initialize agent arguments
        if agentargs is not None:
            self.agent_args = agentargs
        elif model is not None:
            # Set system message handling based on model
            system_message_handling = "combined" if model == "o1-mini" else "separate"
            self.agent_args = DemoAgentArgs(
                model_name=model,
                chat_mode=False,
                demo_mode="default",
                use_html=use_html,
                use_axtree=use_axtree,
                use_screenshot=use_screenshot,
                system_message_handling=system_message_handling
            )
        else:
            raise ValueError("Either model or agentargs must be provided")
        
        # Initialize environment arguments
        if viewport is None:
            viewport = {"width": browser_dimensions[0], "height": browser_dimensions[1]}
            
        self.env_args = {
            "task_seed": None,
            "max_steps": max_steps,
            "headless": headless,
            "golden_user_data_dir": golden_user_data_dir,
            "extensions_dir": extensions_dir,
            "viewport": viewport,
        }
        
        # Try to get run_id from API if api_key and run_name are provided but run_id is not
        if not run_id and api_key and run_name:
            # Use model_id_name if provided, otherwise use model
            api_model_id_name = model_id_name if model_id_name else model
            if api_model_id_name:
                logger.info(f"Getting run ID from API using api_key, model_id_name={api_model_id_name}, and run_name={run_name}")
                try:
                    from agisdk.REAL.browsergym.webclones.base import get_run_id_from_api
                    api_run_id = get_run_id_from_api(api_key, api_model_id_name, run_name)
                    if api_run_id:
                        logger.info(f"Retrieved run ID from API: {api_run_id}")
                        run_id = api_run_id
                        # Enable leaderboard if we got a run_id from the API
                        leaderboard = True
                    else:
                        logger.warning("Failed to get run ID from API")
                except Exception as e:
                    logger.error(f"Error getting run ID from API: {e}")
            else:
                logger.warning("Cannot get run ID from API: model_id_name not provided and model is None")
        
        # Handle run_id and leaderboard submission
        if run_id:
            # self.env_args["task_kwargs"] = {"run_id": run_id}
            
            # Set the RUNID environment variable when leaderboard submission is enabled
            if leaderboard:
                logger.info(f"Setting RUNID environment variable to {run_id} for leaderboard submission")
                os.environ["RUNID"] = run_id
            else:
                # Unset RUNID if leaderboard isn't enabled but it exists in environment
                if "RUNID" in os.environ:
                    logger.info("Unsetting RUNID environment variable (leaderboard disabled)")
                    del os.environ["RUNID"]
        elif leaderboard:
            logger.warning("Leaderboard submission is enabled but run_id is not provided. Please provide a run_id or api_key, model_id_name and run_name.")
        
        # Store task selection parameters
        self.task_name = task_name
        self.task_type = task_type
        self.task_id = task_id
        
        # Create default results directory if it doesn't exist
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
            
        # Log initialization
        logger.info(f"Harness initialized with model={model or 'custom'}, task={task_name or task_type}")
    
    def run(self, tasks: List[str] = None) -> Dict[str, Any]:
        """
        Run the tasks with the configured agent and environment.
        
        Args:
            tasks: Optional list of specific task names to run. If not provided,
                  tasks will be determined based on task_name, task_type, and task_id.
                  
        Returns:
            Dictionary of results indexed by task name
        """
        # Determine which tasks to run if not explicitly provided
        if tasks is None:
            if self.task_name:
                # Run a specific task
                tasks = [self.task_name]
            else:
                # Get tasks based on type and/or ID
                tasks = self._get_tasks(
                    task_type=self.task_type,
                    task_id=self.task_id
                )
                logger.info(f"Running {len(tasks)} tasks")
        
        if not tasks:
            raise ValueError("No tasks found to run")
            
        logger.info(f"Running {len(tasks)} tasks")
        
        # Run the tasks and get results
        results = self._run_tasks(
            tasks=tasks,
            agent_args=self.agent_args,
            env_args_dict=self.env_args,
            results_dir=self.results_dir,
            parallel=self.parallel,
            num_workers=self.num_workers,
            use_cache=self.use_cache,
            cache_only=self.cache_only,
            force_refresh=self.force_refresh
        )
        
        # Format and return results
        self._format_results(results)
        
        return results
    
    def _format_results(self, results: Dict[str, Any]) -> None:
        """Format and print benchmark results."""
        if not results:
            print("No results to display.")
            return
        
        # Calculate aggregate score
        success_count = sum(1 for _, r in results.items() if r.get('cum_reward', 0) == 1)
        success_rate = success_count / len(results) * 100
        
        # Collect timing statistics
        all_times = [r.get('elapsed_time', 0) for _, r in results.items()]
        successful_times = [r.get('elapsed_time', 0) for _, r in results.items() if r.get('cum_reward', 0) == 1]
        
        print("\n===== BENCHMARK RESULTS =====")
        print(f"Tasks completed successfully: {success_count}/{len(results)}")
        print(f"Success rate: {success_rate:.2f}%")
        
        # Print timing statistics
        if all_times:
            print("\nTiming Statistics (All Tasks):")
            print(f"  Average time: {mean(all_times):.2f} seconds")
            print(f"  Median time: {median(all_times):.2f} seconds")
            print(f"  Min time: {min(all_times):.2f} seconds")
            print(f"  Max time: {max(all_times):.2f} seconds")
            if len(all_times) > 1:
                print(f"  Std deviation: {stdev(all_times):.2f} seconds")
        
        if successful_times:
            print("\nTiming Statistics (Successful Tasks Only):")
            print(f"  Average time: {mean(successful_times):.2f} seconds")
            print(f"  Median time: {median(successful_times):.2f} seconds")
            print(f"  Min time: {min(successful_times):.2f} seconds")
            print(f"  Max time: {max(successful_times):.2f} seconds")
            if len(successful_times) > 1:
                print(f"  Std deviation: {stdev(successful_times):.2f} seconds")
        
        # Group results by task type
        task_type_results = {}
        for task_name, record in results.items():
            # Extract task type (e.g., "omnizon" from "webclones.omnizon-1")
            task_full_name = task_name.split('.')[1] if '.' in task_name else task_name
            parts = task_full_name.split('-')
            
            # Find where the numeric part starts
            for i, part in enumerate(parts[1:], 1):
                if part and part[0].isdigit():
                    task_type = '-'.join(parts[:i])
                    break
            else:
                # Fallback if no numeric part is found
                task_type = parts[0]
            
            if task_type not in task_type_results:
                task_type_results[task_type] = {
                    'total': 0,
                    'success': 0,
                    'times': []
                }
            
            task_type_results[task_type]['total'] += 1
            task_type_results[task_type]['times'].append(record.get('elapsed_time', 0))
            if record.get('cum_reward', 0) == 1:
                task_type_results[task_type]['success'] += 1
        
        # Print results by task type
        print("\nResults by task type:")
        for task_type, stats in sorted(task_type_results.items()):
            success_rate = (stats['success'] / stats['total']) * 100
            avg_time = mean(stats['times']) if stats['times'] else 0
            print(f"  {task_type}: {stats['success']}/{stats['total']} ({success_rate:.2f}%) - Avg time: {avg_time:.2f}s")
    
    def _get_tasks(
        self,
        task_type: Optional[str] = None,
        task_id: Optional[int] = None,
        sample_size: Optional[int] = None,
        random_seed: int = 42,
        include_impossible: bool = False
    ) -> List[str]:
        """
        Get tasks based on filtering criteria.
        
        Args:
            task_type: Filter tasks by type (e.g., 'omnizon', 'dashdish')
            task_id: Run a specific task ID for the given task type
            sample_size: Number of tasks to sample (after filtering by task_type)
            random_seed: Seed for random sampling
            include_impossible: Whether to include tasks marked as impossible
            
        Returns:
            List of task names formatted as 'webclones.{task_type}-{task_id}'
        """
        # Use a relative path that works in both editable and installed modes
        tasks_dir = Path(__file__).parent / "browsergym" / "webclones" / "tasks"
        
        # Get all JSON files in the main tasks directory (excluding the alt subdirectory)
        json_files = [f for f in glob.glob(f"{tasks_dir}/*.json") if "/alt/" not in f]
        
        filtered_tasks = []
        for f in json_files:
            # If including all tasks, add all files
            if include_impossible:
                filtered_tasks.append(f)
                continue
                
            # Otherwise filter out impossible tasks
            with open(f, 'r') as file:
                try:
                    task_data = json.load(file)
                    # Only include tasks where "possible" is not explicitly set to false
                    if task_data.get('possible', True):
                        filtered_tasks.append(f)
                except json.JSONDecodeError:
                    # Skip files with invalid JSON
                    continue
        
        # Extract task names without extension
        task_names = [os.path.basename(f).replace('.json', '') for f in filtered_tasks]
        
        # Filter by task type if specified
        if task_type:
            task_names = [t for t in task_names if t.startswith(f"{task_type}-") or 
                          (('-' in t) and t.split('-')[:-1] == task_type.split('-'))]
        
        # Filter by specific task ID if specified
        if task_type and task_id is not None:
            specific_task = f"{task_type}-{task_id}"
            if specific_task in task_names:
                return [f"webclones.{specific_task}" for _ in range(self.sample_tasks)]
            else:
                raise ValueError(f"Task {specific_task} not found")
        
        # Sample tasks if requested
        if sample_size is not None and sample_size > 0:
            if sample_size >= len(task_names):
                # If sample size is larger than available tasks, use all tasks
                pass
            else:
                random.seed(random_seed)
                task_names = random.sample(task_names, sample_size)
        
        # Format task names for browsergym
        return [f"webclones.{name}" for name in sorted(task_names) for _ in range(self.sample_tasks)]
    
    def _run_tasks(
        self,
        tasks: List[str],
        agent_args: AbstractAgentArgs,
        env_args_dict: Dict[str, Any],
        results_dir: str = "./results",
        parallel: bool = False,
        num_workers: int = 5,
        continue_previous: bool = False,
        use_cache: bool = True,
        cache_only: bool = False,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Run tasks with the provided agent and environment configuration.
        
        Args:
            tasks: List of task names to run
            agent_args: Arguments for the agent
            env_args_dict: Dictionary of arguments for the environment
            results_dir: Directory to store results
            parallel: Whether to run tasks in parallel
            num_workers: Number of workers to use for parallel execution
            continue_previous: Whether to try to continue from previous runs
            use_cache: Whether to use and update the cache
            cache_only: Whether to only use cached results without running missing tasks
            force_refresh: Whether to force re-running tasks even if cached results exist
            
        Returns:
            Dictionary of results indexed by task name
        """
        # Generate a unique run ID for this batch (but potentially override with cached run_id for leaderboard)
        import uuid
        from datetime import datetime
        
        # Initialize with a new UUID
        run_uuid = str(uuid.uuid4())
        run_timestamp = datetime.now().isoformat()
        
        
        '''
            Identify and Use Cached Run IDs:
            - When running leaderboard submissions with caching enabled, the system now checks if there are cached leaderboard results
            - If found, it extracts and uses the same run_id from the cached results
            - This ensures that subsequent leaderboard submissions using cached results maintain the same run_id
            
            Prioritization of Run IDs:
            - Explicitly provided run_id (via harness initialization) takes highest priority
            - Cached leaderboard run_id takes second priority
            - New auto-generated run_id is used as a last resort

        '''
        # Check if there's a consistent run_id we should use from the cache for leaderboard submissions
        cached_run_id = None
        if self.leaderboard and use_cache and not force_refresh:
            # Try to find a cached leaderboard result to extract its run_id
            for task_name in tasks[:1]:  # Just check one task to determine the run_id
                cached_result = self._find_cached_result(task_name, agent_args, env_args_dict, results_dir)
                if cached_result and cached_result.get("leaderboard", False):
                    cached_run_id = cached_result.get("run_uuid")
                    if cached_run_id:
                        print(f"Using cached leaderboard run_id: {cached_run_id}")
                        run_uuid = cached_run_id
                        break
        
        print(f"Running multiple tasks with ID: {run_uuid}")
        
        # If this is a leaderboard run, set the RUNID environment variable
        if self.leaderboard:
            if hasattr(self, "run_id") and self.run_id:
                # If harness was initialized with a specific run_id, use that instead
                run_uuid = self.run_id
                print(f"Using explicitly provided run_id: {run_uuid}")
            logger.info(f"Setting RUNID environment variable to {run_uuid} for leaderboard submission")
            os.environ["RUNID"] = run_uuid
        
        # Store run metadata for tracking
        run_metadata = {
            "run_uuid": run_uuid,
            "run_timestamp": run_timestamp,
            "agent_type": agent_args.agent_name if hasattr(agent_args, "agent_name") else type(agent_args).__name__,
            "model_name": getattr(agent_args, "model_name", "unknown"),
            "total_tasks": len(tasks),
            "leaderboard": self.leaderboard if hasattr(self, "leaderboard") else False
        }
        
        print(f"Starting run with ID: {run_uuid}")
        
        # Initialize results dictionary
        results = {}
        
        # Determine which tasks need to be run
        tasks_to_run = []
        
        if use_cache and not force_refresh:
            for task_name in tasks:
                # Try to find a cached result
                cached_result = self._find_cached_result(task_name, agent_args, env_args_dict, results_dir)
                
                if cached_result:
                    # Use cached result
                    print(f"Using cached result for {task_name} from {cached_result.get('exp_dir', 'unknown')}")
                    results[task_name] = cached_result
                elif not cache_only:
                    # Need to run this task
                    tasks_to_run.append(task_name)
                else:
                    print(f"No cached result for {task_name} (skipping in cache-only mode)")
        else:
            # Force refresh or no cache - run all tasks
            if not cache_only:
                tasks_to_run = tasks
        
        # Run tasks if needed
        if tasks_to_run:
            print(f"Running {len(tasks_to_run)} tasks...")
            
            if parallel:
                # Create a partial function with the fixed arguments
                run_task_partial = partial(
                    self._run_single_task,
                    agent_args=agent_args,
                    env_args_dict=env_args_dict,
                    results_dir=results_dir,
                    continue_previous=continue_previous,
                    use_cache=use_cache,
                    run_uuid=run_uuid
                )
                
                # Run tasks in parallel using multiprocessing
                with mp.Pool(processes=num_workers, initializer=init_worker) as pool:
                    new_results = dict(pool.map(run_task_partial, tasks_to_run))
                    
                    # Merge with cached results
                    results.update(new_results)
            else:
                # Run tasks sequentially
                for task_name in tasks_to_run:
                    task_name, exp_record = self._run_single_task(
                        task_name=task_name,
                        agent_args=agent_args,
                        env_args_dict=env_args_dict,
                        results_dir=results_dir,
                        continue_previous=continue_previous,
                        use_cache=use_cache,
                        run_uuid=run_uuid
                    )
                    results[task_name] = exp_record
        
        # Gather statistics for this run using the run_uuid
        cache_hits = len(tasks) - len(tasks_to_run)
        
        # Find all experiments with this run_uuid to count errors
        exps_with_errors = 0
        total_exps = 0
        
        for exp_dir in self._find_experiment_dirs(results_dir):
            # Extract experiment info
            info = self._get_experiment_info(exp_dir)
            
            # If we can't extract info, skip this directory
            if info is None:
                continue
                
            # Count only experiments from this run
            if info.get("run_uuid") == run_uuid:
                total_exps += 1
                
                # Check for errors
                if info.get("err_msg") is not None or info.get("stack_trace") is not None:
                    exps_with_errors += 1
        
        # Print statistics
        print("\nRun Statistics:")
        print(f"  Run UUID: {run_uuid}")
        print(f"  Total tasks: {len(tasks)}")
        print(f"  From cache: {cache_hits}")
        print(f"  Newly executed: {len(tasks_to_run)}")
        print(f"  Tasks with errors: {exps_with_errors} of {total_exps} ({exps_with_errors/total_exps*100 if total_exps > 0 else 0:.1f}%)")
        
        return results
    
    def _run_single_task(
        self,
        task_name: str,
        agent_args: AbstractAgentArgs,
        env_args_dict: Dict[str, Any],
        results_dir: str,
        continue_previous: bool = False,
        use_cache: bool = True,
        run_uuid: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Run a single task with the provided agent and environment configuration.
        
        Args:
            task_name: Name of the task to run
            agent_args: Arguments for the agent
            env_args_dict: Dictionary of arguments for the environment
            results_dir: Directory to store results
            continue_previous: Whether to try to continue from a previous run
            use_cache: Whether to update the cache with results
            run_uuid: Optional UUID for tracking this run batch
            
        Returns:
            Tuple of (task_name, results_dict)
        """
        print(f"Running task: {task_name}")
        
        # Set task name in env args
        env_args_dict["task_name"] = task_name
        
        # Create EnvArgs from dictionary
        env_args = EnvArgs(**env_args_dict)
        
        # Set up experiment
        exp_args = ExpArgs(
            env_args=env_args,
            agent_args=agent_args
        )
        
        # Start timing
        start_time = time.time()
        
        # Run experiment
        exp_args.prepare(results_dir)
        
        # Add essential metadata to summary_info.json before running the experiment
        # This ensures the cache has what it needs even if there's a crash
        summary_info_path = Path(exp_args.exp_dir) / "summary_info.json"
        
        # Extract metadata for cache key
        agent_type = agent_args.agent_name if hasattr(agent_args, "agent_name") else type(agent_args).__name__
        model_name = getattr(agent_args, "model_name", "unknown")
        max_steps = env_args.max_steps
        
        # Check if this is a leaderboard run
        is_leaderboard = self.leaderboard if hasattr(self, "leaderboard") else False
        leaderboard_suffix = "_leaderboard" if is_leaderboard else ""
        
        # Create initial summary info with metadata
        initial_summary = {
            "task_name": task_name,
            "agent_type": agent_type,
            "model_name": model_name,
            "max_steps": max_steps,
            "leaderboard": is_leaderboard,  # Store leaderboard flag in metadata
            "cache_key": f"{task_name}_{agent_type}_{model_name}_{max_steps}{leaderboard_suffix}",
            "experiment_status": "started",
            "run_uuid": run_uuid,  # Add the run UUID for tracking
        }
        
        # Write initial summary info
        with open(summary_info_path, "w") as f:
            json.dump(initial_summary, f, indent=4)
        
        # Run the experiment
        exp_args.run()
        
        # End timing
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Get results
        exp_result = get_exp_result(exp_args.exp_dir)
        exp_record = exp_result.get_exp_record()
        
        # Add timing information to the record
        exp_record['elapsed_time'] = elapsed_time
        
        # Add experiment directory to the record
        exp_record['exp_dir'] = str(exp_args.exp_dir)
        
        # Print current task result
        print(f"Task: {task_name}")
        print(f"  Reward: {exp_record.get('cum_reward', 0)}")
        success = exp_record.get('cum_reward', 0) == 1
        print(f"  Success: {success}")
        print(f"  Time: {elapsed_time:.2f} seconds")
        
        return task_name, exp_record
    
    def _find_cached_result(
        self, 
        task_name: str, 
        agent_args: AbstractAgentArgs, 
        env_args_dict: Dict[str, Any],
        results_dir: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find a cached result for the given task and agent configuration.
        
        Args:
            task_name: Name of the task
            agent_args: Arguments for the agent
            env_args_dict: Dictionary of arguments for the environment
            results_dir: Directory containing experiment results
            
        Returns:
            The cached result or None if not found or if the result contains errors
        """
        # Create cache key
        cache_key = self._create_cache_key(task_name, agent_args, env_args_dict)
        
        # Find all experiment directories
        exp_dirs = self._find_experiment_dirs(results_dir)
        
        # Filter by cache key
        matching_exps = []
        
        for exp_dir in exp_dirs:
            # Extract experiment info
            info = self._get_experiment_info(exp_dir)
            
            # If we can't extract info, skip this directory
            if info is None:
                continue
            
            # Check if this experiment matches our cache key
            if info.get("cache_key") == cache_key:
                matching_exps.append(info)
        
        # If no matching experiments, return None
        if not matching_exps:
            return None
        
        # Sort by timestamp (newest first)
        matching_exps.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        # Get the most recent experiment
        result = matching_exps[0]
        
        # Check if the result has errors
        has_error = (result.get("err_msg") is not None or 
                    result.get("stack_trace") is not None)
        
        # Always skip results with errors
        if has_error:
            print(f"Skipping cached result for {task_name} due to errors, will rerun")
            return None
            
        return result
    
    def _create_cache_key(
        self, 
        task_name: str, 
        agent_args: AbstractAgentArgs, 
        env_args_dict: Dict[str, Any]
    ) -> str:
        """
        Create a unique cache key for a task-agent-env combination.
        
        Args:
            task_name: Name of the task
            agent_args: Arguments for the agent
            env_args_dict: Dictionary of arguments for the environment
            
        Returns:
            A string key for the cache
        """
        # Extract core agent info for the cache key
        agent_model = getattr(agent_args, "model_name", "unknown")
        agent_type = agent_args.agent_name if hasattr(agent_args, "agent_name") else type(agent_args).__name__
        
        # Extract core environment settings
        max_steps = env_args_dict.get("max_steps", "default")
        
        # Check if this is a leaderboard run
        is_leaderboard = self.leaderboard if hasattr(self, "leaderboard") else False
        leaderboard_suffix = "_leaderboard" if is_leaderboard else ""
        
        # Create a reproducible cache key with leaderboard flag
        cache_key = f"{task_name}_{agent_type}_{agent_model}_{max_steps}{leaderboard_suffix}"
        
        return cache_key
    
    def _find_experiment_dirs(self, results_dir: str) -> List[Path]:
        """
        Find all experiment directories in the results directory.
        
        Args:
            results_dir: Directory containing experiment results
            
        Returns:
            List of experiment directory paths
        """
        results_path = Path(results_dir)
        
        # Experiment directories are identified by the presence of summary_info.json
        exp_dirs = []
        
        # Walk through all directories in results_dir
        for root, dirs, files in os.walk(results_dir):
            root_path = Path(root)
            
            # Check if this directory has the required files to be an experiment directory
            if "summary_info.json" in files:
                exp_dirs.append(root_path)
        
        return exp_dirs
    
    def _get_experiment_info(self, exp_dir: Path) -> Optional[Dict[str, Any]]:
        """
        Extract information about an experiment from its directory.
        
        Args:
            exp_dir: Path to experiment directory
            
        Returns:
            Dictionary with experiment information, or None if info can't be extracted
        """
        try:
            # Get modification time as timestamp
            timestamp = os.path.getmtime(exp_dir / "summary_info.json")
            
            # Load summary info
            with open(exp_dir / "summary_info.json", "r") as f:
                summary_info = json.load(f)
            
            # Extract relevant information directly from summary_info.json
            task_name = summary_info.get("task_name")
            agent_type = summary_info.get("agent_type")
            model_name = summary_info.get("model_name", "unknown")
            max_steps = summary_info.get("max_steps")
            
            # Create complete info dict
            info = {
                "task_name": task_name,
                "agent_type": agent_type,
                "model_name": model_name,
                "max_steps": max_steps,
                "timestamp": timestamp,
                "exp_dir": str(exp_dir),
                "cache_key": f"{task_name}_{agent_type}_{model_name}_{max_steps}",
            }
            
            # Add any other summary information
            info.update(summary_info)
            
            return info
        except Exception as e:
            print(f"Warning: Failed to extract info from {exp_dir}: {e}")
            return None

# Make AbstractAgentArgs and Agent classes available at the top level for convenient imports
AbstractAgentArgs = AbstractAgentArgs
Agent = Agent