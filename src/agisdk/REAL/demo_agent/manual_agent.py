import dataclasses
import json
import logging
import textwrap
import time
from typing import Optional

from agisdk.REAL.browsergym.core.action.highlevel import HighLevelActionSet
from agisdk.REAL.browsergym.experiments import AbstractAgentArgs, Agent
from agisdk.REAL.browsergym.utils.obs import (
    flatten_axtree_to_str,
    flatten_dom_to_str,
    prune_html,
)

from ..logging import logger as rich_logger

logger = logging.getLogger(__name__)


def _goal_to_str(goal_object) -> str:
    if goal_object is None:
        return ""
    if isinstance(goal_object, str):
        return goal_object
    if isinstance(goal_object, list):
        parts: list[str] = []
        for entry in goal_object:
            if isinstance(entry, dict):
                text = entry.get("text")
                if text:
                    parts.append(text)
            else:
                parts.append(str(entry))
        return "\n".join(parts)
    return str(goal_object)


class ManualAgent(Agent):
    """Agent that keeps the environment open for manual task execution."""

    def __init__(
        self,
        demo_mode: str,
        wait_prompt: str,
        settle_wait_ms: int,
        show_goal_panel: bool,
        completion_message: str,
    ) -> None:
        super().__init__()
        self.action_set = HighLevelActionSet(
            subsets=["chat", "bid", "infeas"],
            strict=False,
            multiaction=False,
            demo_mode=demo_mode,
        )
        self.wait_prompt = wait_prompt.rstrip() + " "
        self.settle_wait_ms = max(settle_wait_ms, 0)
        self.show_goal_panel = show_goal_panel
        self.completion_message = completion_message.strip() or "Task completed manually."

        self.session_start_time: Optional[float] = None
        self.session_finish_time: Optional[float] = None
        self.action_history: list[str] = []
        self.last_observation: Optional[dict] = None

        self._session_started = False
        self._user_prompted = False
        self._user_done = False
        self._settle_action_sent = False
        self._interrupted = False
        self._completion_message_sent = False
        self._final_message: Optional[str] = None

    def _reset_episode_state(self) -> None:
        """Reset stateful flags when the environment starts a new episode."""
        self.session_start_time = None
        self.session_finish_time = None
        self.action_history = []
        self.last_observation = None
        self._session_started = False
        self._user_prompted = False
        self._user_done = False
        self._settle_action_sent = False
        self._interrupted = False
        self._completion_message_sent = False
        self._final_message = None

    def obs_preprocessor(self, obs: dict) -> dict:
        return {
            "chat_messages": obs["chat_messages"],
            "screenshot": obs["screenshot"],
            "goal_object": obs["goal_object"],
            "last_action": obs["last_action"],
            "last_action_error": obs["last_action_error"],
            "axtree_txt": flatten_axtree_to_str(obs["axtree_object"]),
            "pruned_html": prune_html(flatten_dom_to_str(obs["dom_object"])),
        }

    def _display_start_instructions(self, obs: dict) -> None:
        goal_text = _goal_to_str(obs.get("goal_object"))
        url = obs.get("url", "")

        rich_logger.task_start(goal_text or "Manual Browser Session", model="manual")

        if self.show_goal_panel:
            lines = []
            if goal_text:
                lines.append(f"Goal:\n{goal_text}")
            if url:
                lines.append(f"Current URL:\n{url}")
            lines.append(
                "Interact with the open browser window directly. "
                "Use this run to validate the verifier by completing the task yourself."
            )
            panel_text = "\n\n".join(lines)
            rich_logger.panel(panel_text, title="Manual Agent")
        else:
            rich_logger.info("Manual agent active. Complete the task in the browser.")

    def _await_user_confirmation(self) -> str:
        try:
            response = input(self.wait_prompt)
        except KeyboardInterrupt:
            self._interrupted = True
            rich_logger.warning("Manual session interrupted. Ending run early.")
            return ""
        else:
            rich_logger.info("Manual confirmation received. Capturing final state.")
            return response

    @staticmethod
    def _format_send_action(message: str) -> str:
        return f"send_msg_to_user({json.dumps(message)})"

    def _make_noop_action(self) -> str:
        if self.settle_wait_ms > 0:
            return f"noop({self.settle_wait_ms})"
        return "noop()"

    def get_action(self, obs: dict) -> tuple[Optional[str], dict]:
        self.last_observation = obs

        # Detect a fresh episode after a completed run and reset internal state.
        if self._user_done and self._settle_action_sent and obs.get("last_action") in (None, ""):
            self._reset_episode_state()
            self.last_observation = obs

        if not self._session_started:
            self._session_started = True
            self.session_start_time = time.time()
            self._display_start_instructions(obs)

        if not self._user_prompted:
            self._user_prompted = True
            goal_excerpt = _goal_to_str(obs.get("goal_object"))
            prompt_lines = [
                "Manual control granted. Complete the task in the live browser.",
            ]
            if goal_excerpt:
                trimmed_goal = textwrap.shorten(goal_excerpt, width=200, placeholder="...")
                prompt_lines.append(f"Goal excerpt: {trimmed_goal}")
            prompt_lines.append("When you are satisfied with the result, confirm below.")
            rich_logger.info(" ".join(prompt_lines))

        if not self._user_done:
            user_response = self._await_user_confirmation()
            self._user_done = True
            self.session_finish_time = time.time()

            if not self._completion_message_sent:
                final_message = user_response.strip() or self.completion_message
                self._final_message = final_message
                action = self._format_send_action(final_message)
                self.action_history.append(action)
                rich_logger.task_step(len(self.action_history), action)
                self._completion_message_sent = True
                return action, {}

        if self._user_done and not self._settle_action_sent:
            action = self._make_noop_action()
            self.action_history.append(action)
            rich_logger.task_step(len(self.action_history), action)
            self._settle_action_sent = True
            return action, {}

        stats = {}
        if self.session_start_time and self.session_finish_time:
            stats["manual_duration_s"] = max(
                0.0, self.session_finish_time - self.session_start_time
            )
        if self._interrupted:
            stats["manual_interrupted"] = True

        rich_logger.info("Ending manual run. Returning control to harness.")
        info = {"stats": stats}
        if self._final_message is not None:
            info["manual_message"] = self._final_message
        return None, info


@dataclasses.dataclass
class ManualAgentArgs(AbstractAgentArgs):
    demo_mode: str = "off"
    wait_prompt: str = (
        "Type your final summary (optional), then press Enter once you have finished the task."
    )
    settle_wait_ms: int = 1000
    show_goal_panel: bool = True
    completion_message: str = "Task completed manually."

    def make_agent(self):
        return ManualAgent(
            demo_mode=self.demo_mode,
            wait_prompt=self.wait_prompt,
            settle_wait_ms=self.settle_wait_ms,
            show_goal_panel=self.show_goal_panel,
            completion_message=self.completion_message,
        )
