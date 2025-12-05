# AGI SDK Harness System

## Overview

The `harness.py` file is the main orchestrator for running AI agents on browser-based tasks. It provides a unified interface that handles agent setup, task execution, caching, parallel processing, and result collection. The harness abstracts away the complexity of running experiments while providing powerful features for both development and production use.

## Architecture and Flow

### 1. Initialization (`__init__`)

When you create a harness instance, several key components are set up:

**Agent Configuration:**
- If `model` is provided (e.g., "gpt-4o"), creates a `DemoAgentArgs` with the specified model
- If `agentargs` is provided, uses your custom agent implementation
- Handles system message configuration (`"separate"` vs `"combined"` modes)

**Environment Setup:**
- Configures browser settings (headless mode, dimensions, extensions)
- Sets up task parameters (max_steps, observation types)
- Prepares results directory structure

**Task Selection Logic:**
- Stores task filtering parameters (`task_name`, `task_type`, `task_id`)
- These will be used later to determine which tasks to run

**Leaderboard Integration:**
- Optionally retrieves `run_id` from API using `api_key` and `run_name`
- Sets up environment variables for leaderboard submission

### 2. Task Discovery (`_get_tasks`)

When `harness.run()` is called, the system first determines which tasks to execute:

**Task File Discovery:**
- Scans `browsergym/webclones/tasks/*.json` for available tasks
- Filters out tasks marked as `"possible": false` (unless `include_impossible=True`)

**Filtering Logic:**
- If `task_name` is specified: runs that exact task
- If `task_type` is specified: finds all tasks matching that type (e.g., "omnizon-1", "omnizon-2")
- If `task_id` is also specified: runs only that specific task within the type
- Otherwise: runs all available tasks

**Task Sampling:**
- Each selected task is repeated `sample_tasks` times (default: 1)
- Tasks are formatted as `"<version>.{task_name}"` (e.g., `"v1.omnizon-1"`)

### 3. Execution Planning (`_run_tasks`)

Before running any tasks, the harness creates an execution plan:

**Run UUID Generation:**
- Creates a unique identifier for this batch of tasks
- For leaderboard runs, may reuse cached `run_id` if available
- Sets `RUNID` environment variable for leaderboard integration

**Cache Lookup Process:**
- For each task, calls `_find_cached_result()` to check for existing results
- Cache keys are generated using: `{task_name}_{agent_type}_{model_name}_{max_steps}[_leaderboard]`
- Only uses cached results that don't have errors (`err_msg` or `stack_trace`)
- Separates leaderboard and development caches

**Task Queue Preparation:**
- Determines which tasks need to be run (not in cache or `force_refresh=True`)
- Skips tasks if `cache_only=True` and no cache exists

### 4. Parallel Execution (Ray Integration)

When `num_workers > 1`, the harness uses Ray for parallel processing:

**Ray Initialization:**
```python
ray.init(resources={"memory_gb": num_workers})
```
- Creates `num_workers` memory tokens as a concurrency control mechanism
- No CPU resources are explicitly allocated

**Task Submission:**
```python
@ray.remote(resources={"memory_gb": 1})
def run_task_ray(task_name, agent_args, ...):
```
- Each task function requires 1 memory token
- Ray automatically queues tasks when all tokens are in use
- Tasks start immediately when a token becomes available

**Execution Pattern:**
- All tasks are submitted as futures simultaneously
- Ray manages the queue and executes up to `num_workers` tasks concurrently
- Results are collected using `ray.get(ray_futures)`

### 5. Single Task Execution (`_run_single_task` / `run_task_ray`)

Each individual task follows this flow:

**Environment Setup:**
- Creates `EnvArgs` and `ExpArgs` objects with task-specific configuration
- Calls `exp_args.prepare(results_dir)` to create experiment directory

**Metadata Creation:**
- Generates `summary_info.json` with essential cache metadata
- Includes cache key, agent info, task name, run UUID, and leaderboard flag
- This ensures cache integrity even if the task crashes

**Task Execution:**
- Calls `exp_args.run()` to start the browser and run the agent
- Times the execution for performance metrics

**Result Collection:**
- Uses `get_exp_result(exp_dir)` to extract experiment results
- Adds timing information and experiment directory path
- Returns task name and complete result record

### 6. Caching System

The caching system operates on multiple levels:

**Cache Key Generation (`_create_cache_key`):**
- Combines task name, agent type, model name, max_steps
- Adds `_leaderboard` suffix for leaderboard runs
- Ensures cache separation between different configurations

**Cache Storage:**
- Each experiment directory contains `summary_info.json` with metadata
- Results are stored in structured directories under `results_dir`
- Cache keys are embedded in the metadata for fast lookup

**Cache Retrieval (`_find_cached_result`):**
- Scans all experiment directories for matching cache keys
- Returns the most recent result if multiple matches exist
- Automatically skips results with errors to prevent error propagation

### 7. Result Processing and Display

After all tasks complete:

**Result Aggregation:**
- Combines cached results with newly executed results
- Maintains task name as the key for result lookup

**Statistics Calculation:**
- Computes success rates, timing statistics, and error counts
- Groups results by task type for detailed breakdown
- Uses the run UUID to track experiment-specific metrics

**Output Formatting (`_format_results`):**
- Displays overall success rate and timing statistics
- Shows per-task-type breakdowns
- Provides detailed timing analysis for both all tasks and successful tasks only

## Key Design Principles

### 1. Simplicity and Hackability
- Ray memory tokens provide simple concurrency control without complex actor management
- Standard futures pattern instead of custom pooling logic
- Clear separation between caching, execution, and result processing

### 2. Robust Caching
- Cache keys prevent conflicts between different configurations
- Error results are never cached to avoid propagating failures
- Leaderboard and development runs maintain separate caches

### 3. Fault Tolerance
- Each task is isolated - failures don't affect other tasks
- Metadata is written before task execution to ensure cache integrity
- Automatic error detection and exclusion from cache

### 4. Performance Optimization
- Parallel execution using Ray's resource management
- Intelligent cache reuse to avoid redundant computation
- Batched result collection for efficiency

## Configuration Examples

### Development Usage
```python
harness = REAL.harness(
    model="gpt-4o",
    task_type="omnizon",
    headless=False,        # Watch browser actions
    max_steps=10,          # Quick iteration
    num_workers=1,         # Sequential execution
    use_cache=True,        # Reuse previous results
)
```

### Production Benchmarking
```python
harness = REAL.harness(
    model="gpt-4o",
    headless=True,         # Faster execution
    max_steps=25,          # Full evaluation
    num_workers=8,         # Parallel execution
    force_refresh=True,    # Fresh results
)
```

### Leaderboard Submission
```python
harness = REAL.harness(
    model="gpt-4o-mini",
    leaderboard=True,
    run_id="unique-submission-id",
    headless=True,
    num_workers=20,        # High parallelism
    use_cache=True,        # Reuse valid results
)
```

This architecture provides a robust, scalable system for running AI agent evaluations while maintaining simplicity and hackability.
