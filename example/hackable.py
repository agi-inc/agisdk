#!/usr/bin/env python3

# A minimal agent that you can modify to suit your needs.

import argparse
import base64
import dataclasses
import io
import logging
from typing import Literal

import numpy as np
from openai import OpenAI
from PIL import Image

from agisdk import REAL
from agisdk.REAL.browsergym.core.action.highlevel import HighLevelActionSet
from agisdk.REAL.browsergym.experiments import AbstractAgentArgs, Agent
from agisdk.REAL.browsergym.utils.obs import (
    flatten_axtree_to_str,
    flatten_dom_to_str,
    prune_html,
)
from agisdk.REAL.demo_agent.run_demo import str2bool

logger = logging.getLogger(__name__)


def image_to_jpg_base64_url(image: np.ndarray | Image.Image) -> str:
    """Convert image to base64 encoded JPEG URL."""
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    if image.mode in ("RGBA", "LA"):
        image = image.convert("RGB")

    with io.BytesIO() as buffer:
        image.save(buffer, format="JPEG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/jpeg;base64,{image_base64}"


class DemoAgent(Agent):
    """A basic agent using OpenAI API, to demonstrate BrowserGym's functionalities."""

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

    def __init__(
        self,
        model_name: str,
        chat_mode: bool,
        demo_mode: str,
        use_html: bool,
        use_axtree: bool,
        use_screenshot: bool,
        system_message_handling: Literal["separate", "combined"] = "separate",
    ) -> None:
        super().__init__()
        self.chat_mode = chat_mode
        self.use_html = use_html
        self.use_axtree = use_axtree
        self.use_screenshot = use_screenshot
        self.system_message_handling = system_message_handling

        if not (use_html or use_axtree):
            raise ValueError("Either use_html or use_axtree must be set to True.")

        self.client = OpenAI()
        self.model_name = "gpt-4o"

        self.action_set = HighLevelActionSet(
            subsets=["chat", "bid", "infeas"],
            strict=False,
            multiaction=False,
            demo_mode=demo_mode,
        )
        self.action_history = []

    def _build_system_messages(self) -> list[dict]:
        """Build system messages based on chat mode."""
        if self.chat_mode:
            return [
                {
                    "type": "text",
                    "text": """# Instructions

You are a UI Assistant, your goal is to help the user perform tasks using a web browser. You can
communicate with the user via a chat, to which the user gives you instructions and to which you
can send back messages. You have access to a web browser that both you and the user can see,
and with which only you can interact via specific commands.

Review the instructions from the user, the current state of the page and all other information
to find the best possible next action to accomplish your goal. Your answer will be interpreted
and executed by a program, make sure to follow the formatting instructions.""",
                }
            ]
        else:
            return [
                {
                    "type": "text",
                    "text": """# Instructions

Review the current state of the page and all other information to find the best
possible next action to accomplish your goal. Your answer will be interpreted
and executed by a program, make sure to follow the formatting instructions.""",
                }
            ]

    def _build_user_messages(self, obs: dict) -> list[dict]:
        """Build user messages from observation."""
        user_msgs = []

        if self.chat_mode:
            user_msgs.append({"type": "text", "text": "# Chat Messages"})
            for msg in obs["chat_messages"]:
                if msg["role"] in ("user", "assistant", "infeasible"):
                    user_msgs.append(
                        {"type": "text", "text": f"- [{msg['role']}] {msg['message']}"}
                    )
                elif msg["role"] == "user_image":
                    user_msgs.append({"type": "image_url", "image_url": msg["message"]})
                else:
                    raise ValueError(f"Unexpected chat message role {repr(msg['role'])}")
        else:
            assert obs["goal_object"], "The goal is missing."
            user_msgs.append({"type": "text", "text": "# Goal"})
            user_msgs.extend(obs["goal_object"])

        if self.use_axtree:
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"# Current page Accessibility Tree\n\n{obs['axtree_txt']}",
                }
            )

        if self.use_html:
            user_msgs.append(
                {"type": "text", "text": f"# Current page DOM\n\n{obs['pruned_html']}"}
            )

        if self.use_screenshot:
            user_msgs.extend(
                [
                    {"type": "text", "text": "# Current page Screenshot"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_to_jpg_base64_url(obs["screenshot"]),
                            "detail": "auto",
                        },
                    },
                ]
            )

        user_msgs.append(
            {
                "type": "text",
                "text": f"""# Action Space

{self.action_set.describe(with_long_description=False, with_examples=True)}

Here are examples of actions with chain-of-thought reasoning:

I now need to click on the Submit button to send the form. I will use the click action on the button, which has bid 12.
```click("12")```

I found the information requested by the user, I will send it to the chat.
```send_msg_to_user("The price for a 15\\" laptop is 1499 USD.")```""",
            }
        )

        if self.action_history:
            user_msgs.append({"type": "text", "text": "# History of past actions"})
            user_msgs.extend([{"type": "text", "text": action} for action in self.action_history])

            if obs["last_action_error"]:
                user_msgs.append(
                    {
                        "type": "text",
                        "text": f"# Error message from last action\n\n{obs['last_action_error']}",
                    }
                )

        user_msgs.append(
            {
                "type": "text",
                "text": """# Next action

You will now think step by step and produce your next best action. Reflect on your past actions, any resulting error message, the current state of the page before deciding on your next action.""",
            }
        )

        return user_msgs

    def _query_model(self, system_msgs: list[dict], user_msgs: list[dict]) -> str:
        """Query OpenAI model with messages."""
        if self.system_message_handling == "combined":
            combined_content = ""
            if system_msgs:
                combined_content += system_msgs[0]["text"] + "\n\n"
            for msg in user_msgs:
                if msg["type"] == "text":
                    combined_content += msg["text"] + "\n"

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": combined_content}],
            )
        else:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_msgs},
                    {"role": "user", "content": user_msgs},
                ],
            )
        return response.choices[0].message.content

    def get_action(self, obs: dict) -> tuple[str, dict]:
        system_msgs = self._build_system_messages()
        user_msgs = self._build_user_messages(obs)

        prompt_text_strings = []
        for message in system_msgs + user_msgs:
            match message["type"]:
                case "text":
                    prompt_text_strings.append(message["text"])
                case "image_url":
                    image_url = message["image_url"]
                    if isinstance(message["image_url"], dict):
                        image_url = image_url["url"]
                    if image_url.startswith("data:image"):
                        prompt_text_strings.append(
                            "image_url: " + image_url[:30] + "... (truncated)"
                        )
                    else:
                        prompt_text_strings.append("image_url: " + image_url)
                case _:
                    raise ValueError(
                        f"Unknown message type {repr(message['type'])} in the task goal."
                    )

        full_prompt_txt = "\n".join(prompt_text_strings)
        logger.info(full_prompt_txt)

        action = self._query_model(system_msgs, user_msgs)
        self.action_history.append(action)

        return action, {}


@dataclasses.dataclass
class DemoAgentArgs(AbstractAgentArgs):
    """Arguments for the DemoAgent."""

    agent_name: str = "DemoAgent"
    model_name: str = "gpt-4o"
    chat_mode: bool = False
    demo_mode: str = "off"
    use_html: bool = False
    use_axtree: bool = True
    use_screenshot: bool = False
    system_message_handling: Literal["separate", "combined"] = "separate"

    def make_agent(self):
        """Create and return an instance of DemoAgent with the configured parameters."""
        return DemoAgent(
            model_name=self.model_name,
            chat_mode=self.chat_mode,
            demo_mode=self.demo_mode,
            use_html=self.use_html,
            use_axtree=self.use_axtree,
            use_screenshot=self.use_screenshot,
            system_message_handling=self.system_message_handling,
        )


def run_demo_agent(
    model_name="gpt-4o",
    task_name="v2.omnizon-1",
    headless=False,
    leaderboard=False,
    run_id=None,
):
    """Run a test with the DemoAgent on a browsergym task."""
    logger.info(f"Starting DemoAgent test with model: {model_name} on task: {task_name}")

    agent_args = DemoAgentArgs(
        model_name=model_name,
        chat_mode=False,
        demo_mode="off",
        use_html=False,
        use_axtree=True,
        use_screenshot=True,
        system_message_handling="separate",
    )

    harness = REAL.harness(
        agentargs=agent_args,
        task_name=task_name,
        headless=headless,
        max_steps=25,
        use_axtree=agent_args.use_axtree,
        use_screenshot=agent_args.use_screenshot,
        leaderboard=leaderboard,
        run_id=run_id,
    )

    logger.info("Running task...")
    results = harness.run()

    logger.info("Task completed")
    logger.info(f"Results: {results}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run DemoAgent on browsergym tasks")
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o",
        help="Model to use with the agent (default: gpt-4o)",
    )
    parser.add_argument(
        "--task",
        type=str,
        default="v2.omnizon-1",
        help="Task to run (default: v2.omnizon-1)",
    )
    parser.add_argument(
        "--headless", type=str2bool, default=False, help="Run headless (default: False)"
    )
    parser.add_argument(
        "--run_id",
        type=str,
        default=None,
        help="Run ID for leaderboard submission (required for leaderboard)",
    )
    parser.add_argument(
        "--leaderboard",
        type=str2bool,
        default=False,
        help="Submit results to leaderboard (default: False)",
    )

    args = parser.parse_args()

    results = run_demo_agent(
        model_name=args.model,
        task_name=args.task,
        headless=args.headless,
        leaderboard=args.leaderboard,
        run_id=args.run_id,
    )
