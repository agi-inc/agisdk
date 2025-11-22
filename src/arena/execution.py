from typing import TYPE_CHECKING, Optional, Tuple
import asyncio

from arena.state import AgentState
from arena.errors import AgentError

if TYPE_CHECKING:
    from arena.browser import AgentBrowser
    from arena.agent import BaseAgent
    from arena.result import ExperimentResult
    from arena.task import Task


MAX_STEP_ERRORS = 3


class TaskExecution:
    def __init__(
        self,
        task: "Task",
        agent: "BaseAgent",
        browser: "AgentBrowser",
        max_steps: int = 60,
        step_timeout: int = 3000,
        task_execution_id: Optional[int] = None,
        ignore_errors: bool = False,
    ):
        """
        Initialize TaskExecution.

        Args:
            task: Task object with goal, url, and evaluator
            agent: The agent to run
            browser: The browser instance
            max_steps: Maximum number of steps to run
            step_timeout: Timeout in seconds for each agent step (default 180s = 3 minutes)
            task_execution_id: Optional ID
        """
        self.task = task
        self.agent = agent
        self.browser = browser
        self.max_steps = max_steps
        self.step_timeout = step_timeout
        self.task_execution_id = task_execution_id
        self.ignore_errors = ignore_errors

    # @observe
    async def run(self) -> Tuple["AgentState", "ExperimentResult"]:
        """
        Run the task and return final state and experiment result.

        Returns:
            Tuple of (final_agent_state, experiment_result)
        """
        print(f"Running task '{self.task.goal}' on {self.task.url}")
        # Navigate to URL and wait
        navigation_wait = getattr(self.browser, "wait_until", None) or "load"
        try:
            await self.browser.page.goto(self.task.url, wait_until=navigation_wait)
        except Exception as _:
            print(f"Failed to navigate to URL: {self.task.url}. Continuing regardless")

        await self.browser.page.wait_for_timeout(2000)

        # Initialize agent state
        state = AgentState(
            goal=self.task.goal,
            url=self.task.url,
            task_execution_id=self.task_execution_id,
        )

        state.messages.append(
            {
                "role": "user",
                "type": "user_input",
                "content": f"Your goal is {state.goal}",
            }
        )

        # Run agent steps
        step = 0  # Initialize step variable
        for step in range(self.max_steps):
            state.step = step

            # Take screenshot and store in state
            screenshot = await self.browser.screenshot()
            state.images.append(screenshot)

            # Execute agent step
            try:
                state = await asyncio.wait_for(
                    self.agent.step(self.browser, state),
                    timeout=self.step_timeout,
                )
                state.error = None  # clear previous error
                state.error_count = 0  # reset error count on success
            except AgentError as e:
                state.register_error(e)
                if state.error_count >= MAX_STEP_ERRORS:
                    raise RuntimeError(
                        f"Step {step} failed {MAX_STEP_ERRORS} times"
                    )
            except TimeoutError:
                state.register_error(TimeoutError(f"Step {step} timed out"))
                if state.error_count >= MAX_STEP_ERRORS:
                    raise RuntimeError(
                        f"Step {step} failed {MAX_STEP_ERRORS} times"
                    )
            except Exception as e:
                if not self.ignore_errors:
                    raise
                agent_error = AgentError(f"Unexpected error: {e}")
                state.register_error(agent_error)

            if state.error_count >= MAX_STEP_ERRORS:
                raise RuntimeError(f"Step {step} failed {MAX_STEP_ERRORS} times")

            state.url = self.browser.page.url
            await asyncio.sleep(0.5)
            if state.finished:
                break

        # Evaluate task
        print("Evaluating task")
        result = await self.task.evaluate(state)

        return state, result
