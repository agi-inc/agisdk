#!/usr/bin/env python3
import argparse
import dataclasses
import logging

from agisdk import REAL
from agisdk.REAL.browsergym.experiments import AbstractAgentArgs, Agent

logger = logging.getLogger(__name__)


class HumanAgent(Agent):
    """Minimal agent for human task execution."""

    def __init__(self) -> None:
        super().__init__()

    def get_action(self, obs: dict) -> tuple[str, dict]:
        # Simply ask for user input
        print("\n" + "=" * 50)
        print("Type your final answer:")
        print("=" * 50)
        user_answer = input()

        # Format as a send_msg_to_user action to trigger completion
        action = f'send_msg_to_user("{user_answer}")'

        return action, {}


@dataclasses.dataclass
class HumanAgentArgs(AbstractAgentArgs):
    """Arguments for the HumanAgent."""

    agent_name: str = "HumanAgent"

    def make_agent(self):
        """Create and return an instance of HumanAgent."""
        return HumanAgent()


def run_human_agent(task_name="v1.omnizon-1", headless=False, run_id=None):
    """Run a task with human input."""
    logger.info(f"Starting human task: {task_name}")

    agent_args = HumanAgentArgs()

    harness = REAL.harness(
        agentargs=agent_args,
        task_name=task_name,
        headless=headless,
        max_steps=25,
        use_axtree=False,
        use_screenshot=False,
        run_id=run_id,
    )

    logger.info("Running task...")
    results = harness.run()

    logger.info("Task completed")
    logger.info(f"Results: {results}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tasks with human input")
    parser.add_argument(
        "--task",
        type=str,
        default="v1.omnizon-1",
        help="Task to run (default: v1.omnizon-1)",
    )
    parser.add_argument("--headless", action="store_true", help="Run headless (default: False)")
    parser.add_argument("--run_id", type=str, default=None, help="Run ID for task")

    args = parser.parse_args()

    results = run_human_agent(task_name=args.task, headless=args.headless, run_id=args.run_id)
