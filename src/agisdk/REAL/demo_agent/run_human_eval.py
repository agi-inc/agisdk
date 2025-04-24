import argparse
import os
import time
import abc
import threading
import signal
import sys

# browsergym experiments utils
from agisdk.REAL.browsergym.experiments import EnvArgs, ExpArgs, get_exp_result

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
    
    def __init__(self, chat_mode=False):
        """Initialize the human agent."""
        self.chat_mode = chat_mode
        self.action_set = None  # No need for action mapping for human control
        self.final_answer = None
        self.done = False
    
    def get_action(self, obs):
        """
        Get action from human user - for human agents, we just return None
        to indicate the human should interact directly with the browser.
        """
        if self.done and self.final_answer:
            # If we've marked the task as done, return the final answer
            return self.final_answer, {"think": "Human has completed the task"}
            
        if self.chat_mode and "last_user_message" in obs:
            # In chat mode, just return the user's message as is
            return obs.get("last_user_message", ""), {}
        
        # For non-chat mode, just return None to let human interact directly
        return None, {"think": "Human is manually controlling the browser"}
    
    def obs_preprocessor(self, obs):
        """Simple observation preprocessor that just returns the observation as is."""
        return obs
    
    def set_final_answer(self, answer):
        """Set the final answer for the task."""
        self.final_answer = answer
        self.done = True


class HumanAgentArgs:
    """Arguments for creating a human agent."""
    
    def __init__(self, chat_mode=False):
        """Initialize the human agent arguments."""
        self.agent_name = "HumanAgent"
        self.chat_mode = chat_mode
    
    def make_agent(self):
        """Create a human agent."""
        return HumanAgent(chat_mode=self.chat_mode)
    
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
    parser = argparse.ArgumentParser(description="Run human evaluation on tasks.")
    parser.add_argument(
        "--task_name",
        type=str,
        default="webclones.networkin1_jmespath_llm",
        help="Name of the Browsergym task to run. If 'openended', you need to specify a 'start_url'",
    )
    parser.add_argument(
        "--start_url",
        type=str,
        default="https://www.google.com",
        help="Starting URL (only for the openended task).",
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
    parser.add_argument(
        "--chat_mode",
        type=str2bool,
        default=False,
        help="Enable chat mode for tasks that support it.",
    )

    return parser.parse_args()


def main():
    print(
        """\
--- HUMAN EVALUATION MODE ---
This mode allows you to manually interact with the browser to complete the task.
The system will evaluate your performance using the same criteria used for AI agents.
Complete the task in the browser, then provide your answer in the terminal.
"""
    )

    args = parse_args()

    # Print task information
    print(f"Task: {args.task_name}")
    
    # setting up human agent config
    agent_args = HumanAgentArgs(
        chat_mode=args.chat_mode
    )

    # setting up environment config
    env_args = EnvArgs(
        task_name=args.task_name,
        task_seed=None,
        max_steps=args.max_steps,
        headless=False,  # keep the browser open
        viewport={"width": args.viewport_width, "height": args.viewport_height},
        wait_for_user_message=True,  # Wait for user input before proceeding
    )

    # for openended task, set environment to interactive chat mode on a start url
    if args.task_name == "openended":
        agent_args.chat_mode = True
        env_args.wait_for_user_message = True
        env_args.task_kwargs = {"start_url": args.start_url}

    # Create the agent first so we can reference it
    human_agent = agent_args.make_agent()
    
    # setting up the experiment
    exp_args = ExpArgs(
        env_args=env_args,
        agent_args=agent_args,
    )

    # Prepare results directory
    exp_args.prepare("./results")
    
    # Define a global to track if experiment is done
    experiment_done = threading.Event()
    exp_dir = exp_args.exp_dir
    answer_provided = threading.Event()
    
    # Define signal handler for clean termination
    def signal_handler(sig, frame):
        print("\nInterrupted! Cleaning up...")
        experiment_done.set()
        sys.exit(0)
    
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Function to run the experiment and set flag when done
    def run_experiment():
        try:
            exp_args.run()
        except Exception as e:
            print(f"Error running experiment: {e}")
        finally:
            experiment_done.set()
    
    # Print instructions
    print("\nThe browser will open shortly. Please complete the task as instructed.")
    print("When you're done with the browser interaction, return to this terminal to provide your answer.")
    
    # Start the experiment in a separate thread
    experiment_thread = threading.Thread(target=run_experiment)
    experiment_thread.daemon = True
    experiment_thread.start()
    
    # Wait for the browser to load
    time.sleep(3)
    
    # Wait for user to indicate completion or for experiment to finish on its own
    try:
        while not experiment_done.is_set() and not answer_provided.is_set():
            # Check if user wants to finish and get their answer
            print("\nAFTER completing the task in the browser, provide your answer below.")
            print("Type your answer and press ENTER to submit. This will be used for evaluation.")
            user_answer = input("> ")
            
            if user_answer.strip():
                print("\nThank you! Submitting your answer and completing the evaluation...")
                human_agent.set_final_answer(user_answer)
                answer_provided.set()
                # Give some time for the environment to process the answer
                time.sleep(5)
                break
            else:
                print("Please provide an answer to complete the task.")
    except KeyboardInterrupt:
        print("\nInterrupted! Cleaning up...")
    
    # Wait for the experiment to fully complete
    experiment_done.wait(timeout=20)
    
    # Give some time for any pending operations to complete
    time.sleep(5)
    
    # loading and printing results
    try:
        exp_result = get_exp_result(exp_dir)
        exp_record = exp_result.get_exp_record()

        print("\n=== EVALUATION RESULTS ===")
        for key, val in exp_record.items():
            print(f"{key}: {val}")
            
        # Print additional jmespath_llm details if available
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
                            print(f"  Similarity: {eval_result[1].get('similarity', 'N/A')}")
                            print(f"  Passed: {eval_result[0]}")
        except Exception as e:
            print(f"Error retrieving detailed results: {e}")
    except Exception as e:
        print(f"Error loading results: {e}")
        print(f"Results directory: {exp_dir}")


if __name__ == "__main__":
    main() 