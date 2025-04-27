import base64
import dataclasses
import numpy as np
import io
import logging

from PIL import Image
from typing import Literal, Optional

from agisdk.REAL.browsergym.experiments import Agent, AbstractAgentArgs
from agisdk.REAL.browsergym.core.action.highlevel import HighLevelActionSet
from agisdk.REAL.browsergym.core.action.python import PythonActionSet
from agisdk.REAL.browsergym.utils.obs import flatten_axtree_to_str, flatten_dom_to_str, prune_html

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

    def __init__(
        self,
        model_name: str, 
        chat_mode: bool,
        demo_mode: str,
        use_html: bool,
        use_axtree: bool,
        use_screenshot: bool,
        system_message_handling: Literal["separate", "combined"] = "separate",
        openai_api_key: Optional[str] = None,
        openrouter_api_key: Optional[str] = None,
        openrouter_site_url: Optional[str] = None,
        openrouter_site_name: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.chat_mode = chat_mode
        self.use_html = use_html
        self.use_axtree = use_axtree
        self.use_screenshot = use_screenshot
        self.previous_thinking_blocks = []
        self.system_message_handling = system_message_handling

        if not (use_html or use_axtree):
            raise ValueError(f"Either use_html or use_axtree must be set to True.")

        from openai import OpenAI
        from anthropic import Anthropic
        import os

        if model_name.startswith("gpt-") or model_name.startswith("o1") or model_name.startswith("o3"):
            # Use provided API key or fall back to environment variable
            if openai_api_key is None:
                openai_api_key = os.getenv('OPENAI_API_KEY')
            base_url = os.getenv('OPENAI_API_BASE')
            self.client = OpenAI(base_url=base_url, api_key=openai_api_key)
            self.model_name = model_name
            # Define function to query OpenAI models
            def query_model(system_msgs, user_msgs):
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
                        messages=[
                            {"role": "user", "content": combined_content},
                        ],
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
            self.query_model = query_model
            
        elif model_name.startswith("openrouter/"):
            # Extract the actual model name without the openrouter/ prefix
            actual_model_name = model_name.replace("openrouter/", "", 1)
            
            # Initialize OpenRouter client (using OpenAI client with custom base URL)
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_api_key or os.getenv("OPENROUTER_API_KEY"),
            )
            # Store site info for headers
            self.openrouter_site_url = openrouter_site_url or os.getenv("OPENROUTER_SITE_URL", "")
            self.openrouter_site_name = openrouter_site_name or os.getenv("OPENROUTER_SITE_NAME", "")
            self.model_name = actual_model_name
            
            # Define function to query OpenRouter models
            def query_model(system_msgs, user_msgs):
                response = self.client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": self.openrouter_site_url,
                        "X-Title": self.openrouter_site_name,
                    },
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_msgs},
                        {"role": "user", "content": user_msgs},
                    ],
                )
                return response.choices[0].message.content
            self.query_model = query_model
        
        elif model_name.startswith("local"):
            actual_model_name = model_name.replace("local/", "", 1)
            
            # Modify OpenAI's API key and API base to use vLLM's load balancer server.
            self.client = OpenAI(
                base_url="http://localhost:7999/v1",
                api_key="FEEL_THE_AGI",
            )
            self.model_name = actual_model_name
            
            # Define function to query OpenRouter models
            def query_model(system_msgs, user_msgs):
                completion = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_msgs},
                        {"role": "user", "content": user_msgs}
                    ],
                    max_tokens=500,
                    temperature=1.0,
                    top_p=0.95,
                    extra_body={"top_k": 64}
                )
                return completion.choices[0].message.content
                
            self.query_model = query_model
    
        elif model_name.startswith("sonnet-3.7"):
            self.client = Anthropic(api_key=anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"))
            self.model_name = "claude-3-7-sonnet-20250219"
            if model_name.endswith(":thinking"):
                thinking = {
                        "type": "enabled",
                        "budget_tokens": 4000,
                    }
                self.thinking_enabled = True
            else:
                thinking = {"type": "disabled"}
                self.thinking_enabled = False
                
            # Define function to query Anthropic models
            def query_model(system_msgs, user_msgs):
                # Convert OpenAI format messages to Anthropic format
                anthropic_content = []
                for msg in user_msgs:
                    if msg["type"] == "text":
                        anthropic_content.append({"type": "text", "text": msg["text"]})
                    elif msg["type"] == "image_url":
                        # Handle base64 image URLs for Anthropic
                        image_url = msg["image_url"]
                        if isinstance(image_url, dict):
                            image_url = image_url["url"]
                        
                        if image_url.startswith("data:image/jpeg;base64,"):
                            base64_data = image_url.replace("data:image/jpeg;base64,", "")
                            anthropic_content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64_data
                                }
                            })
                        else:
                            # Skip external URLs or unsupported image formats
                            anthropic_content.append({"type": "text", "text": "[Image URL not supported by Anthropic API]"})
                
                # Set up messages array for API call
                messages = []
                
                # If we have previous thinking blocks, need to create an assistant message
                if self.thinking_enabled and self.previous_thinking_blocks:
                    # Add previous assistant message with thinking blocks
                    messages.append({
                        "role": "assistant",
                        "content": self.previous_thinking_blocks
                    })
                
                # Add the current user message
                messages.append({
                    "role": "user", 
                    "content": anthropic_content
                })
                
                # Make API request
                response = self.client.messages.create(
                    model=self.model_name,
                    max_tokens=8000,
                    messages=messages,
                    thinking=thinking,
                    system=system_msgs[0]["text"] if system_msgs else "",
                )
                
                # Log complete response for debugging
                logger.info(f"Response content types: {[content.type for content in response.content]}")
                
                # Store thinking blocks for future use
                if self.thinking_enabled:
                    # Clear previous blocks
                    self.previous_thinking_blocks = []
                    
                    # Store all thinking and redacted_thinking blocks
                    for content_block in response.content:
                        if content_block.type in ["thinking", "redacted_thinking"]:
                            self.previous_thinking_blocks.append(content_block)
                
                # Extract only the text content for the agent's action
                text_content = None
                for content_block in response.content:
                    if content_block.type == "text":
                        text_content = content_block.text
                        break
                
                # Fallback if no text content found
                if text_content is None:
                    logger.warning("No text content found in response")
                    # Default to first block's text as a fallback
                    text_content = response.content[0].text
                
                return text_content
            self.query_model = query_model
        else:
            raise ValueError(f"Model {model_name} not supported. Use a model name starting with 'gpt-', 'sonnet-3.7', or 'openrouter/' followed by the OpenRouter model ID.")

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
            # append goal
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
                            # Goal
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
        logger.info(full_prompt_txt)

        # query model using the abstraction function
        action = self.query_model(system_msgs, user_msgs)

        self.action_history.append(action)

        return action, {}


@dataclasses.dataclass
class DemoAgentArgs(AbstractAgentArgs):
    """
    This class stores the arguments that define the DemoAgent configuration.

    By isolating parameters in a dataclass, this ensures serialization without storing
    internal states of the agent.
    
    The model_name parameter can be:
    - An OpenAI model starting with "gpt-" (e.g., "gpt-4o", "gpt-4o-mini")
    - An Anthropic model ("sonnet-3.7" or "sonnet-3.7:thinking")
    - An OpenRouter model with the prefix "openrouter/" (e.g., "openrouter/anthropic/claude-3-5-sonnet")
    
    API keys can be provided directly as parameters or through environment variables:
    - OpenAI models: provide openai_api_key or set OPENAI_API_KEY env var
    - Anthropic models: provide anthropic_api_key or set ANTHROPIC_API_KEY env var
    - OpenRouter models: provide openrouter_api_key or set OPENROUTER_API_KEY env var
      Optional: provide openrouter_site_url/openrouter_site_name or set the corresponding env vars
    """

    model_name: str = "gpt-4o"
    chat_mode: bool = False
    demo_mode: str = "off"
    use_html: bool = False
    use_axtree: bool = True
    use_screenshot: bool = False
    system_message_handling: Literal["separate", "combined"] = "separate"
    
    # API keys and configuration - these can be None and the agent will fall back to environment variables
    openai_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    openrouter_site_url: Optional[str] = None
    openrouter_site_name: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    def make_agent(self):
        return DemoAgent(
            model_name=self.model_name,
            chat_mode=self.chat_mode,
            demo_mode=self.demo_mode,
            use_html=self.use_html,
            use_axtree=self.use_axtree,
            use_screenshot=self.use_screenshot,
            system_message_handling=self.system_message_handling,
            # Pass API keys and configuration
            openai_api_key=self.openai_api_key,
            openrouter_api_key=self.openrouter_api_key,
            openrouter_site_url=self.openrouter_site_url,
            openrouter_site_name=self.openrouter_site_name,
            anthropic_api_key=self.anthropic_api_key,
        )
