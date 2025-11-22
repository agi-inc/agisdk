from typing import TYPE_CHECKING
from dataclasses import dataclass
from pathlib import Path

if TYPE_CHECKING:
    from arena.browser import AgentBrowser
    from arena.state import AgentState
    from arena.result import ExperimentResult
    from arena.evaluation import BaseEvaluator


@dataclass
class Task:
    """Task interface that encapsulates goal, URL, and evaluator."""

    goal: str
    url: str
    evaluator: "BaseEvaluator"

    @classmethod
    async def from_spec(cls, task_spec: str, browser: "AgentBrowser") -> "Task":
        """
        Create a Task from task specification.

        Args:
            task_spec: JSON file path for experiment tasks
            browser: Browser instance needed for evaluator setup

        Returns:
            Task object with goal, url, and evaluator
        """
        if not Path(task_spec).exists():
            raise FileNotFoundError(f"Task JSON file not found: {task_spec}")

        from arena.evaluation import Evaluation  # TODO: move to top

        result = await Evaluation.setup_evaluator(browser, task_spec)
        if not result:
            raise ValueError(f"Failed to setup evaluator for task: {task_spec}")

        evaluator, goal, url = result
        return cls(goal, url, evaluator)

    async def evaluate(self, state: "AgentState") -> "ExperimentResult":
        """Evaluate the task using the associated evaluator."""
        try:
            result = await self.evaluator.evaluate(state)

            result.url = state.url
            result.goal = state.goal

            return result

        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"Evaluation failed: {e}")

            from arena.result import ExperimentResult

            failed_result = ExperimentResult(success=False)
            failed_result.url = state.url
            failed_result.goal = state.goal

            return failed_result
