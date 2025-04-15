from typing import Callable, Literal, Optional, Union, List, Dict, Any
import os
import importlib.resources
import json
import multiprocessing
from functools import partial
from .eval import check_evals
from .cdp_utils import launch_chromium
from .results_utils import show_results


# Import optional Playwright utilities
try:
    from .playwright_utils import (
        setup_playwright, cleanup_playwright, get_finish_json, PLAYWRIGHT_AVAILABLE
    )
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class EvalHarness:
    def __init__(self, 
                 agent_fn: Callable[[str, Any], str],
                 type: Literal["url", "playwright", "cdp"] = "playwright",
                 max_steps: int = 25,
                 headless: bool = False):
        """
        Initialize the evaluation harness.
        
        Args:
            agent_fn: Function that implements the agent logic
            type: Type of harness to use (url, playwright, cdp)
            max_steps: Maximum number of steps allowed per task
            headless: Whether to run browsers in headless mode
        """
        self.agent_fn = agent_fn
        self.type = type
        self.max_steps = max_steps
        self.headless = headless
        
    def _run_task_wrapper(self, task):
        """Wrapper function to run a single task in a separate process."""
        return self.run_task(task)
        
    def run(self,
            local: bool = True,
            use_cache: bool = True,
            dir: str = "./results",
            tasks: Union[Literal["all"], List[str], str] = "all",
            parallel: bool = True,
            num_workers: int = 4):
        """Run evaluation harness on tasks.
        
        Args:
            local: Run locally
            use_cache: Use cached results if available
            dir: Output directory for results
            tasks: Task selection, with multiple formats:
                - "all": Run all available tasks
                - List[str]: List of specific task IDs to run (e.g. ["udriver-1", "udriver-2"])
                - str with pattern: Run tasks matching the pattern (e.g. "udriver" runs all udriver tasks)
                - str with exact ID: Run a single specific task (e.g. "udriver-1")
            parallel: Whether to run tasks in parallel using multiprocessing
            num_workers: Number of parallel worker processes to use
        """
        self.results_dir = dir
        self.use_cache = use_cache
        os.makedirs(dir, exist_ok=True)
        
        # Load all tasks
        all_tasks = []
        tasks_dir = importlib.resources.files("agisdk.tasks")
        
        # First, create a list of all available tasks
        available_tasks = []
        for task_json in tasks_dir.iterdir():
            if task_json.name.endswith('.json'):
                obj = json.loads(task_json.read_text())
                available_tasks.append(obj)
        
        # Filter tasks based on the tasks parameter
        if tasks == "all":
            # Use all tasks
            all_tasks = available_tasks
        elif isinstance(tasks, list):
            # Filter by list of specific task IDs
            all_tasks = [t for t in available_tasks if t.get('id') in tasks]
        elif isinstance(tasks, str):
            # Single task ID or pattern
            if "-" in tasks:
                # Specific task ID (e.g., "udriver-1")
                all_tasks = [t for t in available_tasks if t.get('id') == tasks]
            else:
                # Pattern match (e.g., "udriver" to run all udriver tasks)
                all_tasks = [t for t in available_tasks if tasks in t.get('id', "")]
                print(f"Pattern '{tasks}' matched {len(all_tasks)} tasks")
        
        if not all_tasks:
            print("No tasks found or matched the filter criteria.")
            return
        
        print(f"Selected {len(all_tasks)} tasks: {[t.get('id') for t in all_tasks]}")
            
        print(f"Running {len(all_tasks)} tasks...")
        
        # Run tasks sequentially or in parallel
        if parallel and num_workers > 1:
            # Use multiprocessing for parallel execution
            with multiprocessing.Pool(processes=min(num_workers, len(all_tasks))) as pool:
                # We don't need to collect results since they're saved to disk
                pool.map(self._run_task_wrapper, all_tasks)
            print(f"Completed {len(all_tasks)} tasks in parallel mode with {min(num_workers, len(all_tasks))} workers")
        else:
            # Run tasks sequentially
            for task in all_tasks:
                self.run_task(task)
            print(f"Completed {len(all_tasks)} tasks sequentially")
        
        print("All tasks completed!")
                        
    def run_task(self, task_obj):
        """Run a single task and save results to disk.
        
        Args:
            task_obj: Task object with task details
        """
        task_id = task_obj['id']
        process_id = os.getpid()
        print(f"Process {process_id}: Running task {task_id}")
        
        # Create task directory
        task_dir = os.path.join(self.results_dir, task_id)
        os.makedirs(task_dir, exist_ok=True)
        
        # Path to results file
        results_file = os.path.join(task_dir, "results.json")
        
        # Check if we can use cached results
        if self.use_cache and os.path.exists(results_file):
            try:
                with open(results_file, 'r') as f:
                    results = json.load(f)
                
                # Check if task completed successfully with no errors
                if results.get('completed', False) and not results.get('error'):
                    print(f"Process {process_id}: Using cached results for task {task_id}")
                    return
            except (json.JSONDecodeError, IOError) as e:
                print(f"Process {process_id}: Error reading cache for {task_id}: {e}")
                # Continue with execution if cache read fails
        task_result = {
            "completed": False,
            "success": False,
            "error": None,
            "score": 0.0,
            "task_id": task_id
        }

        if self.type == "playwright":
            if not PLAYWRIGHT_AVAILABLE:
                raise ImportError("Playwright is not available. Please install it.")
            
            
            # Get task website details
            base_url = task_obj['website']['url']
            
            try:
                # Setup Playwright
                browser, context, main_page, background_page = setup_playwright(
                    task_id=task_id,
                    base_url=base_url,
                    run_id="local",
                    headless=self.headless,
                )
            except Exception as e:
                print(f"Process {process_id}: Error setting up Playwright: {e}")
                task_result["env_setup_error"] = str(e)
                task_result["error"] = True
                with open(results_file, 'w') as f:
                    json.dump(task_result, f, indent=2)
                print(f"Process {process_id}: Task {task_id} failed")
                return
            
            try:
                # Run the agent function and pass the browser instance along with max_steps and task_dir
                agent_response = self.agent_fn(
                    task_obj['goal'], 
                    browser,
                    self.max_steps,
                    task_dir
                )
                task_result["agent_response"] = agent_response
                
                # Add submission step for Playwright
                import urllib.parse
                # Handle None or empty response
                if agent_response is None or agent_response.strip() == "":
                    encoded_response = "None"
                else:
                    encoded_response = urllib.parse.quote(agent_response)
                    
                submit_url = f"{base_url}/submit?retrieved_answer={encoded_response}"
                main_page.goto(submit_url)
                # Wait for submission to complete
                import time
                time.sleep(3)
                
            except Exception as e:
                print(f"Process {process_id}: Error running agent function: {e}")
                task_result["agent_error"] = str(e)
                task_result["error"] = True
                with open(results_file, 'w') as f:
                    json.dump(task_result, f, indent=2)
                cleanup_playwright(browser, context, main_page, background_page)
                return
            try:
                finish_state, error = get_finish_json(base_url, main_page)
            except Exception as e:
                print(f"Process {process_id}: Error getting finish state: {e}")
                task_result["finish_state_error"] = str(e)
                task_result["error"] = True
                with open(results_file, 'w') as f:
                    json.dump(task_result, f, indent=2)
                cleanup_playwright(browser, context, main_page, background_page)
                return
            task_result["finish_state"] = finish_state
            eval_results = check_evals(
                task_obj['evals'],
                finish_state,
                model_response=agent_response,
            )
            task_result["eval_results"] = eval_results
            if eval_results[0]:
                task_result["success"] = True
                task_result["score"] = 1.0
            else:
                task_result["success"] = False
                task_result["score"] = 0.0
            
            task_result["completed"] = True
            task_result["error"] = False
            task_result["env_setup_error"] = None
            task_result["agent_error"] = None
            task_result["finish_state_error"] = None
            # save results
            with open(results_file, 'w') as f:
                json.dump(task_result, f, indent=2)
            print(f"Process {process_id}: Task {task_id} completed successfully (Playwright)")
            cleanup_playwright(browser, context, main_page, background_page)
        
        elif self.type == "cdp":
            # Start CDP with cdp_utils
            kill_cdp, cdp_port = launch_chromium(headless=self.headless, suppress_output=True)
            
            import requests
            import websocket
            import time
            # setup the connection and navigate to the task URL + config
            try:
                # Wait for Chrome to start up
                time.sleep(3)
                
                # Get task website details
                base_url = task_obj['website']['url']
                
                # Get the list of available targets
                debug_url = f"http://localhost:{cdp_port}/json"
                response = requests.get(debug_url)
                targets = response.json()
                
                # Find a target with WebSocket debugger URL
                target = None
                for t in targets:
                    if "webSocketDebuggerUrl" in t:
                        target = t
                        break
                
                if target is None:
                    raise Exception("No target with a WebSocket debugger URL was found.")
                
                ws_url = target["webSocketDebuggerUrl"]
                
                # Connect to the target using WebSocket
                ws = websocket.create_connection(ws_url)
                
                # Configure the task
                config_url = f"{base_url}/config?run_id=local&task_id={task_id}"
                navigate_config_cmd = {
                    "id": 1,
                    "method": "Page.navigate",
                    "params": {
                        "url": config_url
                    }
                }
                ws.send(json.dumps(navigate_config_cmd))
                ws.recv()  # Get navigation response
                
                # Wait for page to load
                time.sleep(3)
                
                # Navigate to the main task URL
                navigate_cmd = {
                    "id": 2,
                    "method": "Page.navigate",
                    "params": {
                        "url": base_url
                    }
                }
                ws.send(json.dumps(navigate_cmd))
                ws.recv()  # Get navigation response
                
                # Wait for page to load
                time.sleep(3)
            except Exception as e:
                print(f"Error setting up CDP: {e}")
                task_result["env_setup_error"] = str(e)
                task_result["error"] = True
                with open(results_file, 'w') as f:
                    json.dump(task_result, f, indent=2)
                ws.close()
                kill_cdp()
                with open(results_file, 'w') as f:
                    json.dump(task_result, f, indent=2)
                print(f"Process {process_id}: Task {task_id} failed")
                return
            
            # Run the agent function
            # disconnect the websocket
            ws.close()
            cdp_url = f"http://localhost:{cdp_port}"
            try:
                # Run the agent function with CDP port along with max_steps and task_dir
                agent_response = self.agent_fn(
                    task_obj['goal'], 
                    cdp_url, 
                    self.max_steps,
                    task_dir
                )
                task_result["agent_response"] = agent_response
                
                # Reconnect to the WebSocket for submission
                ws = websocket.create_connection(ws_url)
                
                # Add submission step for CDP
                import urllib.parse
                # Handle None or empty response
                if agent_response is None or agent_response.strip() == "":
                    encoded_response = "None"
                else:
                    encoded_response = urllib.parse.quote(agent_response)
                    
                submit_url = f"{base_url}/submit?retrieved_answer={encoded_response}"
                
                # Navigate to the submit URL
                submit_cmd = {
                    "id": 5,
                    "method": "Page.navigate",
                    "params": {
                        "url": submit_url
                    }
                }
                
                ws.send(json.dumps(submit_cmd))
                ws.recv()  # Get navigation response
                
                # Wait for submission to complete
                time.sleep(3)
                
                # Close the WebSocket after submission
                ws.close()
                
            except Exception as e:
                print(f"Process {process_id}: Error running agent function: {e}")
                task_result["agent_error"] = str(e)
                task_result["error"] = True
                with open(results_file, 'w') as f:
                    json.dump(task_result, f, indent=2)
                ws.close()
                kill_cdp()
                return
            print(f"Process {process_id}: Agent finished running, back to harness")
            
            # Reconnect to the WebSocket
            ws = websocket.create_connection(ws_url)
            
            # extract state and evals
            try:
                # Navigate to the finish endpoint
                finish_url = f"{base_url}/finish"
                finish_cmd = {
                    "id": 3,
                    "method": "Page.navigate",
                    "params": {
                        "url": finish_url
                    }
                }
                
                ws.send(json.dumps(finish_cmd))
                ws.recv()  # Get navigation response
                
                # Wait for page to load
                time.sleep(5)
                
                # Extract JSON from the page using CDP
                cmd = {
                    "id": 4,  # unique ID for this command
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": "document.documentElement.outerHTML",
                        "returnByValue": True  # ensures the HTML is returned directly as a JSON value
                    }
                }
                
                # Send the command
                ws.send(json.dumps(cmd))
                
                # Receive and parse the response
                response = ws.recv()
                result = json.loads(response)
                page_text = result.get("result", {}).get("result", {}).get("value", "")
                # get the text in the <pre></pre> tag
                import re
                match = re.search(r'<pre.*?>(.*?)</pre>', page_text, re.DOTALL)
                if match:
                    json_text = match.group(1)
                    finish_state = json.loads(json_text)
                else:
                    raise Exception("No JSON found in the <pre> tag")
            except Exception as e:
                import traceback
                import sys
                exc_type, exc_value, exc_traceback = sys.exc_info()
                trace_details = traceback.format_exception(exc_type, exc_value, exc_traceback)
                error_trace = "".join(trace_details)
                
                print(f"Process {process_id}: Error getting finish state: {e}")
                print(f"Error type: {exc_type.__name__}")
                print(f"Full traceback:\n{error_trace}")
                
                task_result["finish_state_error"] = str(e)
                task_result["error_traceback"] = error_trace
                task_result["error"] = True
                with open(results_file, 'w') as f:
                    json.dump(task_result, f, indent=2)
                ws.close()
                kill_cdp()
                with open(results_file, 'w') as f:
                    json.dump(task_result, f, indent=2)
                print(f"Process {process_id}: Task {task_id} failed")
                return
                
            task_result["finish_state"] = finish_state
            eval_results = check_evals(
                task_obj['evals'],
                finish_state,
                model_response=agent_response,
            )
            task_result["eval_results"] = eval_results
            if eval_results[0]:
                task_result["success"] = True
                task_result["score"] = 1.0
            else:
                task_result["success"] = False
                task_result["score"] = 0.0
            
            task_result["completed"] = True
            task_result["error"] = False
            task_result["env_setup_error"] = None
            task_result["agent_error"] = None
            task_result["finish_state_error"] = None
            
            ws.close()
            kill_cdp()
            with open(results_file, 'w') as f:
                json.dump(task_result, f, indent=2)
            print(f"Process {process_id}: Task {task_id} completed successfully (CDP)")
            return
        
        else:
            raise ValueError(f"Unsupported harness type: {self.type}")
        # Save results
        
    def show_results(self, dir: str = None):
        """
        Compute and display statistics from task results in the specified directory.
        
        Args:
            dir: Directory containing the results (default: self.results_dir or "./results")
        
        Returns:
            Dict with statistics about task results
        """
        # Use the directory from run() if available, otherwise use parameter or default
        results_dir = dir or getattr(self, 'results_dir', "./results")
        return show_results(results_dir)
        