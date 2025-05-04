#!/usr/bin/env python3
import dataclasses
from typing import Dict, Tuple, Union, Optional

from agisdk import REAL

import base64
import dataclasses
import numpy as np
import io
import logging
import os
import uuid
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from PIL import Image
from typing import Literal

# Import str2bool function for boolean command line arguments
from agisdk.REAL.demo_agent.run_demo import str2bool

from agisdk.REAL.browsergym.experiments import Agent, AbstractAgentArgs
from agisdk.REAL.browsergym.core.action.highlevel import HighLevelActionSet
from agisdk.REAL.browsergym.core.action.python import PythonActionSet
from agisdk.REAL.browsergym.utils.obs import flatten_axtree_to_str, flatten_dom_to_str, prune_html

# Import the AgentLogger class
import sys
import os
# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rl_training.agents.agent_logger_class import AgentLogger

# Configure logging with more detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Handling Screenshots
def image_to_jpg_base64_url(image: np.ndarray | Image.Image):
    """Convert a numpy array to a base64 encoded image url."""

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
        
    def reset(self):
        """Called when the environment is reset"""
        super().reset()
        # Reset action history
        self.action_history = []
        
    def close(self):
        """Called when the agent is being closed"""
        # Complete the agent logger session if available
        if hasattr(self, 'agent_logger') and self.agent_logger is not None:
            try:
                session_id = self.agent_logger.complete()
                print(f"Agent logger session completed with ID: {session_id}")
            except Exception as e:
                logger.error(f"Failed to complete agent logger session: {e}")
                
        super().close()

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

        from openai import OpenAI
        import os

        # Initialize OpenAI client for GPT-4o with API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.warning("OPENAI_API_KEY not found in environment, using a dummy key")
            openai_api_key = "sk-dummy-key-for-testing"

        self.client = OpenAI(api_key=openai_api_key, base_url=os.getenv('OPENAI_API_BASE'))
        self.model_name = "gpt-4o"  # Always use GPT-4o regardless of input model_name
        
        # Initialize the agent logger for Multion API logging
        try:
            # Get API key from environment variables
            api_key = os.getenv("MULTION_API_KEY")
            if not api_key:
                logger.warning("MULTION_API_KEY not found in environment variables")
                self.agent_logger = None
            else:
                # Initialize the agent logger with a descriptive prompt
                initial_prompt = f"Agent using {self.model_name} for browsergym interaction"
                self.agent_logger = AgentLogger(prompt=initial_prompt, api_key=api_key)
                print(f"Agent logger initialized with session ID: {self.agent_logger.SESSION_ID}")
                
                # Log an initial event
                self.agent_logger.log_step(
                    {"initialization": "Agent initialized", "model": self.model_name},
                    {"status": "ready", "chat_mode": self.chat_mode, "screenshot_enabled": self.use_screenshot}
                )
        except Exception as e:
            logger.error(f"Failed to initialize agent logger: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.agent_logger = None
        
        # Define function to query OpenAI models (with simulation for testing)
        def query_model(system_msgs, user_msgs):
            if openai_api_key.startswith("sk-dummy"):
                # Simulate a model response for testing
                # Silently use simulated response without logging
                return "```click(\"1\")```"
            
            try:
                if self.system_message_handling == "combined":
                    # Combine system and user messages into a single user message
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
            except Exception as e:
                logger.error(f"Error querying OpenAI model: {str(e)}")
                # Return a fallback action for testing
                return "```send_msg_to_user(\"I encountered an error.\")```"
                
        self.query_model = query_model

        self.action_set = HighLevelActionSet(
            subsets=["chat", "bid", "infeas"],  # define a subset of the action space
            # subsets=["chat", "bid", "coord", "infeas"] # allow the agent to also use x,y coordinates
            strict=False,  # less strict on the parsing of the actions
            multiaction=False,  # does not enable the agent to take multiple actions at once
            demo_mode=demo_mode,  # add visual effects
        )
        # use this instead to allow the agent to directly use Python code
        # self.action_set = PythonActionSet())

        self.action_history = []

    def get_action(self, obs: dict) -> tuple[str, dict]:
        system_msgs = []
        user_msgs = []

        if self.chat_mode:
            system_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
                            # Instructions

                            You are a UI Assistant, your goal is to help the user perform tasks using a web browser. You can
                            communicate with the user via a chat, to which the user gives you instructions and to which you
                            can send back messages. You have access to a web browser that both you and the user can see,
                            and with which only you can interact via specific commands.

                            Review the instructions from the user, the current state of the page and all other information
                            to find the best possible next action to accomplish your goal. Your answer will be interpreted
                            and executed by a program, make sure to follow the formatting instructions.
                            """,
                }
            )
            # append chat messages
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
                            # Chat Messages
                            """,
                }
            )
            for msg in obs["chat_messages"]:
                if msg["role"] in ("user", "assistant", "infeasible"):
                    user_msgs.append(
                        {
                            "type": "text",
                            "text": f"""\
                                    - [{msg['role']}] {msg['message']}
                                    """,
                        }
                    )
                elif msg["role"] == "user_image":
                    user_msgs.append({"type": "image_url", "image_url": msg["message"]})
                else:
                    raise ValueError(f"Unexpected chat message role {repr(msg['role'])}")

        else:
            assert obs["goal_object"], "The goal is missing."
            system_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
                            # Instructions

                            Review the current state of the page and all other information to find the best
                            possible next action to accomplish your goal. Your answer will be interpreted
                            and executed by a program, make sure to follow the formatting instructions.
                            """,
                }
            )
            # append goal header
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
                            # Goal
                            
                            {obs["goal_object"]}
                            """,
                }
            )
            # goal_object is directly presented as a list of openai-style messages
            user_msgs.extend(obs["goal_object"])

        # append page AXTree (if asked)
        if self.use_axtree:
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
                            # Current page Accessibility Tree

                            {obs["axtree_txt"]}

                            """,
                }
            )
        # append page HTML (if asked)
        if self.use_html:
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
                            # Current page DOM

                            {obs["pruned_html"]}

                            """,
                }
            )

        # append page screenshot (if asked)
        if self.use_screenshot:
            user_msgs.append(
                {
                    "type": "text",
                    "text": """\
                            # Current page Screenshot

                            """,
                }
            )
            user_msgs.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_to_jpg_base64_url(obs["screenshot"]),
                        "detail": "auto",
                    },  # Literal["low", "high", "auto"] = "auto"
                }
            )

        # append action space description
        user_msgs.append(
            {
                "type": "text",
                "text": f"""\
                            # Action Space

                            {self.action_set.describe(with_long_description=False, with_examples=True)}

                            Here are examples of actions with chain-of-thought reasoning:

                            I now need to click on the Submit button to send the form. I will use the click action on the button, which has bid 12.
                            ```click("12")```

                            I found the information requested by the user, I will send it to the chat.
                            ```send_msg_to_user("The price for a 15\\" laptop is 1499 USD.")```
""",
            }
        )

        # append past actions (and last error message) if any
        if self.action_history:
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
                            # History of past actions
                            """,
                }
            )
            user_msgs.extend(
                [
                    {
                        "type": "text",
                        "text": f"""\
                                {action}
                                """,
                    }
                    for action in self.action_history
                ]
            )

            if obs["last_action_error"]:
                user_msgs.append(
                    {
                        "type": "text",
                        "text": f"""\
                            # Error message from last action

                            {obs["last_action_error"]}

                            """,
                    }
                )

        # ask for the next action
        user_msgs.append(
            {
                "type": "text",
                "text": f"""\
                            # Next action

                            You will now think step by step and produce your next best action. Reflect on your past actions, any resulting error message, the current state of the page before deciding on your next action.
                            """,
            }
        )

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
        # Don't log the full prompt text to keep console output clean
        # logger.info(full_prompt_txt)

        # query model using the abstraction function
        action = self.query_model(system_msgs, user_msgs)

        self.action_history.append(action)
        
        # Log this step through the Multion API
        if hasattr(self, 'agent_logger') and self.agent_logger is not None:
            try:
                # Create a structured representation of inputs
                inputs = {
                    "prompt": full_prompt_txt[:500] + "..." if len(full_prompt_txt) > 500 else full_prompt_txt,
                    "observation": {
                        "num_chat_messages": len(obs.get("chat_messages", [])),
                        "has_screenshot": "screenshot" in obs and obs["screenshot"] is not None,
                        "has_axtree": "axtree_object" in obs and obs["axtree_object"] is not None,
                        "has_html": "dom_object" in obs and obs["dom_object"] is not None,
                        "goal": str(obs.get("goal_object", ""))[:100] + "..." if obs.get("goal_object") and len(str(obs["goal_object"])) > 100 else str(obs.get("goal_object", "")),
                        "last_action": obs.get("last_action", ""),
                        "last_action_error": obs.get("last_action_error", ""),
                    }
                }
                
                # Create a structured representation of outputs
                outputs = {
                    "action": action,
                    "action_type": action.split("(")[0] if "(" in action else "unknown"
                }
                
                # Extract action type for a cleaner summary
                action_type = action.split("(")[0] if "(" in action else "unknown"
                action_args = action.split("(", 1)[1].rstrip(")") if "(" in action else ""
                
                # Log the step with Multion API
                self.agent_logger.log_step(inputs, outputs)
                
                # Only log a summary of the action to the console
                print(f"Step {self.agent_logger.step_count}: {action_type} {action_args[:30]}{'...' if len(action_args) > 30 else ''}")
            except Exception as e:
                logger.error(f"Failed to log step to Multion API: {e}")

        return action, {}


@dataclasses.dataclass
class DemoAgentArgs(AbstractAgentArgs):

    agent_name: str = "DemoAgent"  # Agent name for the SDK to recognize
    model_name: str = "gpt-4o"     # Default model, can be changed at runtime
    chat_mode: bool = False        # Whether to enable chat mode
    demo_mode: str = "off"         # Visual effects mode (off, minimal, full)
    use_html: bool = False         # Whether to include HTML in observations
    use_axtree: bool = True        # Whether to include accessibility tree
    use_screenshot: bool = False   # Whether to include screenshots
    system_message_handling: Literal["separate", "combined"] = "separate"  # How to handle system messages

    def make_agent(self):
        """Create and return an instance of DemoAgent with the configured parameters."""
        # This method is called by the agisdk harness to instantiate the agent
        return DemoAgent(
            model_name=self.model_name,
            chat_mode=self.chat_mode,
            demo_mode=self.demo_mode,
            use_html=self.use_html,
            use_axtree=self.use_axtree,
            use_screenshot=self.use_screenshot,
            system_message_handling=self.system_message_handling,
        )


# Example creating and using the DemoAgent
def run_demo_agent(model_name="gpt-4o", headless=False, leaderboard=False, run_id=None, task_name="webclones.omnizon-1"):    
    # Create the agent arguments with the specified parameters
    agent_args = DemoAgentArgs(
        model_name=model_name,
        chat_mode=False,
        demo_mode="off",
        use_html=False,
        use_axtree=True,
        use_screenshot=True,
        system_message_handling="separate"
    )
    
    # Pass the agent arguments to the harness through the agisdk module
    harness = REAL.harness(
        agentargs=agent_args,
        task_name=task_name,        # The specific task to run
        headless=headless,          # Configurable browser visibility
        max_steps=25,               # Maximum steps per task
        use_axtree=agent_args.use_axtree,         # Pass through from agent args
        use_screenshot=agent_args.use_screenshot,  # Pass through from agent args
        leaderboard=leaderboard,    # Whether to submit to leaderboard
        run_id=run_id,              # Run ID for leaderboard submission
    )
    
    # Run the task
    logger.info("Running tasks...")
    results = harness.run()
    
    # Print results summary
    logger.info("Task completed")
    logger.info(f"Results: {results}")
    
    return results


if __name__ == "__main__":
    # Run the agent with the specified parameters
    results = run_demo_agent()
