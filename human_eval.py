#!/usr/bin/env python3
"""
Human evaluation script for RealGym tasks.
Allows humans to manually solve tasks and record their performance.
Enhanced to support jmespath_llm evaluations.
"""

import argparse
import logging
import os
import time
import threading
import signal
import sys
import abc

# browsergym experiments utils
from agisdk.REAL.browsergym.experiments import EnvArgs, ExpArgs, get_exp_result

# Set up logging
logger = logging.getLogger(__name__)

# Define our own Agent class since we can't import it
class Agent(abc.ABC):
    """Abstract agent class that handles decision making."""
    
    @abc.abstractmethod
    def get_action(self, obs):
        """Process observation and return an action."""
        pass
    
    def obs_preprocessor(self, obs):
        """Process observation before decision making."""
        return obs


class HumanAgent(Agent):
    """Human agent that allows a person to interact with the browser manually."""
    
    def __init__(self, chat_mode=False, llm_model="gpt-4o"):
        """Initialize the human agent."""
        self.chat_mode = chat_mode
        self.action_set = None  # No need for action mapping for human control
        self.final_answer = None
        self.done = False
        self.llm_model = llm_model
        self.waiting_for_answer = False
        self.answer_submitted = False
        self.step_count = 0  # Track the number of steps
    

    def get_action(self, obs):
        """
        Get action from human user - for human agents, we just return None
        to indicate the human should interact directly with the browser.
        """
        print(obs.goal)
        user_response = input("Type in Final Answer Here")
        return f"send_msg_to_user(\"{user_response}\")", {}

class HumanAgentArgs:
    """Arguments for creating a human agent."""
    
    def __init__(self, chat_mode=False, llm_model="gpt-4o"):
        """Initialize the human agent arguments."""
        self.agent_name = "HumanAgent"
        self.chat_mode = chat_mode
        self.llm_model = llm_model
    
    def make_agent(self):
        """Create a human agent."""
        return HumanAgent(chat_mode=self.chat_mode, llm_model=self.llm_model)
    
    def prepare(self):
        """Prepare the agent before running the experiment."""
        pass
    
    def close(self):
        """Close the agent after running the experiment."""
        pass


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def parse_args():
    parser = argparse.ArgumentParser(description="Run human evaluation of RealGym tasks.")
    
    # Task selection
    task_group = parser.add_argument_group("Task Selection")
    parser.add_argument(
        "--task_name",
        type=str,
        default="webclones.networkin1_jmespath_llm",
        help="Name of the Browsergym task to run. If 'openended', you need to specify a 'start_url'",
    )
    parser.add_argument(
        "--task_type", 
        help="Task type to filter (e.g., 'omnizon', 'dashdish')"
    )
    parser.add_argument(
        "--task_id", 
        type=int, 
        help="Specific task ID to run (requires --task_type)"
    )
    
    # LLM configuration for jmespath_llm evaluations
    llm_group = parser.add_argument_group("LLM Configuration")
    parser.add_argument(
        "--llm_model",
        type=str,
        default="gpt-4o",
        help="LLM model to use for jmespath_llm evaluations"
    )
    parser.add_argument(
        "--llm_api_key",
        type=str,
        default=None,
        help="API key for the LLM service (defaults to OPENAI_API_KEY environment variable)"
    )
    
    # Special parameters
    special_group = parser.add_argument_group("Special Parameters")
    parser.add_argument(
        "--start_url",
        type=str,
        default="https://www.google.com",
        help="Starting URL (only for the openended task).",
    )
    parser.add_argument(
        "--chat_mode",
        type=str2bool,
        default=False,
        help="Enable chat mode for tasks that support it.",
    )
    
    # Environment setup
    env_group = parser.add_argument_group("Environment Configuration")
    parser.add_argument(
        "--golden_user_data_dir",
        type=str,
        default=None,
        help="Path to a user data directory to use as a golden profile.",
    )
    parser.add_argument(
        "--extensions_dir",
        type=str,
        default=None,
        help="Path to a directory containing Chrome extensions to load.",
    )
    parser.add_argument(
        "--viewport_width",
        type=int,
        default=1280,
        help="Width of the browser viewport.",
    )
    parser.add_argument(
        "--viewport_height",
        type=int,
        default=720,
        help="Height of the browser viewport.",
    )
    parser.add_argument(
        "--max_steps",
        type=int,
        default=100,
        help="Maximum number of steps per task.",
    )
    
    # Output configuration
    output_group = parser.add_argument_group("Output Configuration")
    parser.add_argument(
        "--results_dir",
        type=str,
        default="./results",
        help="Directory to store results.",
    )
    parser.add_argument(
        "--detailed_output",
        action="store_true",
        help="Show detailed output including jmespath_llm evaluations"
    )
    
    return parser.parse_args()


def setup_llm_env(args):
    """Set up environment variables for LLM evaluations."""
    if args.llm_api_key:
        os.environ["OPENAI_API_KEY"] = args.llm_api_key
    elif "OPENAI_API_KEY" not in os.environ:
        api_key = input("OPENAI_API_KEY not found. Enter your OpenAI API key for jmespath_llm evaluations: ")
        if api_key.strip():
            os.environ["OPENAI_API_KEY"] = api_key
        else:
            logger.warning("No API key provided. jmespath_llm evaluations may fail.")


def run_single_task(task_name, agent_args, env_args, results_dir="./results"):
    """Run a single task with human interaction and get results."""
    
    # Create the agent first so we can reference it
    human_agent = agent_args.make_agent()
    
    # Set up the experiment
    env_args.task_name = task_name
    exp_args = ExpArgs(
        env_args=env_args,
        agent_args=agent_args,
    )
    
    # Prepare results directory
    exp_args.prepare(results_dir)
    exp_dir = exp_args.exp_dir
    
    # Set up events for synchronization
    experiment_running = threading.Event()
    experiment_done = threading.Event()
    answer_provided = threading.Event()
    
    # Define signal handler for clean termination
    def signal_handler(sig, frame):
        print("\nInterrupted! Cleaning up...")
        experiment_done.set()
        sys.exit(0)
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Keep the browser active by printing a message periodically
    def keep_alive():
        counter = 0
        while not experiment_done.is_set() and not answer_provided.is_set():
            time.sleep(15)  # Check every 15 seconds
            counter += 1
            if counter % 2 == 0:  # Print message every 30 seconds
                print("Browser session active. Complete the task and return here to submit your answer.")
    
    # Start the keep-alive thread
    keep_alive_thread = threading.Thread(target=keep_alive)
    keep_alive_thread.daemon = True
    keep_alive_thread.start()
    
    # Function to run the experiment
    def run_experiment():
        try:
            experiment_running.set()
            # Keep a reference to the ExpArgs to prevent garbage collection
            nonlocal exp_args
            exp_args.run()
        except Exception as e:
            logger.error(f"Error running experiment: {e}")
        finally:
            experiment_done.set()
    
    # Start the experiment in a separate thread
    experiment_thread = threading.Thread(target=run_experiment)
    experiment_thread.daemon = True
    experiment_thread.start()
    
    # Wait for the browser to load and experiment to start running
    print("Waiting for browser to open...")
    experiment_running.wait(timeout=30)
    time.sleep(5)  # Additional time to ensure browser is fully loaded
    
    # Let the user interact with the browser
    print("\nBrowser is open. Please complete the task as instructed.")
    print("IMPORTANT: The browser will remain open while you're solving the task.")
    print("Complete the task fully, then return here to provide your answer.")
    
    # First, just let the user interact with the browser
    human_agent.waiting_for_answer = True
    
    # Wait for user to provide their answer
    try:
        while not experiment_done.is_set() and not answer_provided.is_set():
            print("\nWhen you have completed the task in the browser, type your answer below.")
            print("Type your answer and press ENTER to submit for evaluation:")
            user_answer = input("> ")
            
            if user_answer.strip():
                print("\nThank you! Submitting your answer for evaluation...")
                human_agent.set_final_answer(user_answer)
                answer_provided.set()
                
                # Wait a bit for the agent's action to be processed
                time.sleep(3)
                
                # Wait for the evaluation to complete (but not too long)
                wait_count = 0
                while not experiment_done.is_set() and wait_count < 20:
                    print("Waiting for evaluation to complete...")
                    time.sleep(1)
                    wait_count += 1
                
                # Force completion if it's taking too long
                if not experiment_done.is_set():
                    print("Evaluation is taking longer than expected. Proceeding anyway.")
                    break
                else:
                    break
            else:
                print("Please provide an answer to complete the task.")
    except KeyboardInterrupt:
        print("\nInterrupted! Cleaning up...")
    
    # Give some time for any pending operations to complete
    time.sleep(5)
    
    # Get results
    try:
        exp_result = get_exp_result(exp_dir)
        return exp_result, exp_dir
    except Exception as e:
        logger.error(f"Error getting experiment results: {e}")
        return None, exp_dir


def print_jmespath_llm_results(exp_result):
    """Print detailed results from jmespath_llm evaluations."""
    detailed_results = False
    
    try:
        for step_info in exp_result.steps_info:
            if hasattr(step_info, 'task_info') and step_info.task_info and 'results' in step_info.task_info:
                for i, eval_result in enumerate(step_info.task_info['results']):
                    if len(eval_result) > 1 and isinstance(eval_result[1], dict) and 'jmespath_result' in eval_result[1]:
                        if not detailed_results:
                            print("\n=== DETAILED JMESPATH_LLM EVALUATIONS ===")
                            detailed_results = True
                        print(f"\nEvaluation {i+1}:")
                        print(f"  Query: {eval_result[1].get('query', 'N/A')}")
                        print(f"  Result: {eval_result[1].get('jmespath_result', 'N/A')}")
                        print(f"  Similarity Score: {eval_result[1].get('similarity', 'N/A')}")
                        print(f"  Passed: {eval_result[0]}")
                        if 'rubric' in eval_result[1]:
                            print(f"  Rubric: {eval_result[1].get('rubric')}")
    except Exception as e:
        logger.error(f"Error printing jmespath_llm details: {e}")


def main():
    # Parse arguments
    args = parse_args()
    
    # Set up LLM environment for jmespath_llm evaluations
    setup_llm_env(args)
    
    print(
        """\
--- HUMAN EVALUATION MODE ---
This enhanced mode allows you to manually solve tasks and evaluate them,
including jmespath_llm evaluations that use AI to evaluate your performance.
"""
    )
    
    # Determine which tasks to run
    tasks = []
    if args.task_name:
        tasks = [args.task_name]
    elif args.task_type:
        # We don't have access to get_tasks from realeval, so provide a warning
        print("Warning: task_type filtering is not supported. Using task_name only.")
        if args.task_name:
            tasks = [args.task_name]
    
    if not tasks:
        print("No tasks specified. Please provide --task_name.")
        return
    
    # Print which tasks will be run
    print(f"Running human evaluation on {len(tasks)} task(s):")
    for task in tasks:
        print(f"  {task}")
    
    # Set up human agent arguments
    agent_args = HumanAgentArgs(
        chat_mode=args.chat_mode,
        llm_model=args.llm_model
    )
    
    # Set up environment configuration
    env_args = EnvArgs(
        task_name=args.task_name if "openended" not in tasks else "openended",
        task_seed=None,
        max_steps=args.max_steps,
        headless=False,  # Always show browser for human evaluation
        wait_for_user_message=True,  # Wait for user input before proceeding
        viewport={"width": args.viewport_width, "height": args.viewport_height},
    )
    
    # Add special parameters for openended task
    if "openended" in tasks:
        env_args.task_kwargs = {"start_url": args.start_url}
    
    # Results storage
    results = []
    
    # Run each task
    for task_name in tasks:
        print(f"\n=== Running task: {task_name} ===")
        print("The browser will open shortly. Please complete the task as instructed.")
        print("When you're done, return to this terminal to provide your answer.")
        
        # Run the task
        exp_result, exp_dir = run_single_task(
            task_name=task_name,
            agent_args=agent_args,
            env_args=env_args,
            results_dir=args.results_dir
        )
        
        if exp_result:
            # Print basic results
            exp_record = exp_result.get_exp_record()
            print("\n=== EVALUATION RESULTS ===")
            for key, val in exp_record.items():
                print(f"{key}: {val}")
            
            # Print detailed jmespath_llm results if requested
            if args.detailed_output:
                print_jmespath_llm_results(exp_result)
            
            # Store result for overall summary
            results.append({
                "task_name": task_name,
                "exp_dir": exp_dir,
                "exp_record": exp_record,
                "result": exp_result
            })
        else:
            print(f"Failed to get results for task: {task_name}")
    
    # Print overall summary
    if len(results) > 1:
        print("\n=== OVERALL SUMMARY ===")
        for i, result in enumerate(results):
            print(f"Task {i+1}: {result['task_name']}")
            print(f"  Status: {result['exp_record'].get('experiment_status', 'Unknown')}")
            print(f"  Terminated: {result['exp_record'].get('terminated', 'Unknown')}")
            print(f"  Truncated: {result['exp_record'].get('truncated', 'Unknown')}")


if __name__ == "__main__":
    main() 