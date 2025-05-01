import os
import base64
import io
from sys import argv
from PIL import Image
from model_utils import llm_query

# Read the actions documentation
with open(os.path.join(os.path.dirname(__file__), "ACTIONS.md"), "r") as f:
    ACTIONS_DOC = f.read()

with open(os.path.join(os.path.dirname(__file__), "SYSTEM_PROMPT.md"), "r") as f:
    SYSTEM_PROMPT = f.read()


def get_agent_action(observation, model_config, task_config):
    """
    Obtain the next action from an LLM agent
    
    Args:
        observation: The current browser observation containing axtree, action history, etc.
        model_config: Configuration for the model (API keys, model name, etc.)
        task_config: Configuration for the task (goal, etc.)
        
    Returns:
        String containing the next action to execute
    """
    # Create prompt
    prompt = create_prompt(observation, task_config)
    
    # Make API call based on provider
    response = llm_query(prompt, SYSTEM_PROMPT, model_config)
    
    # Extract the action from the response
    action = extract_action(response)
    
    return action, prompt, response

def create_prompt(observation, task_config) -> str:
    """
    Create a prompt for the model
    
    Args:
        observation: The current browser observation
        task_config: Configuration for the experiment
    
    Returns:
        String containing the prompt
    """
    # Get goal from experiment config
    goal = task_config.get("goal", "Complete the task")
    
    # Get previous actions and error message
    action_list = observation.get("action_list", [])
    previous_actions_text = "\n".join(action_list)
    error_message = observation.get("previous_action_error", None)
    
    # Prepare screenshot if available
    screenshot_text = ""
    if "screenshot" in observation and observation["screenshot"]:
        screenshot_text = "[Screenshot is available but not shown in text prompt]"
    
    # Build the prompt
    prompt = f"""# Task
{goal}

# Current page Accessibility Tree
{observation['axtree']}

# Available Actions
{ACTIONS_DOC}

# Previous Actions
{previous_actions_text}
"""
    
    # Add error message if there is one
    if error_message:
        prompt += f"""
# Error from previous action
{error_message}
"""
    
    # Add screenshot note if available
    if screenshot_text:
        prompt += f"""
# Screenshot
{screenshot_text}
"""

    # Add final instruction
    prompt += """
# Next Action
Think step by step about what action to take next to accomplish the task.
Look at the accessibility tree to find relevant elements, their browsergym IDs, and their properties.
Decide what action to take and return it in the exact format needed, e.g. `click('123')` or `fill('456', 'text to enter')`.

Your answer should be only a single action in the correct format.
"""

    return prompt

def extract_action(response: str) -> str:
    """
    Extract the action from the model response
    
    Args:
        response: The raw response from the model
    
    Returns:
        Cleaned action string
    """
    # Look for code blocks
    import re
    code_block_pattern = r"```(?:python)?\s*(.*?)```"
    code_blocks = re.findall(code_block_pattern, response, re.DOTALL)
    
    if code_blocks:
        # Take the last code block if there are multiple
        action = code_blocks[-1].strip()
    else:
        # If no code blocks, look for common action patterns
        action_pattern = r"([a-zA-Z_]+\(.*?\))"
        actions = re.findall(action_pattern, response)
        if actions:
            action = actions[-1].strip()
        else:
            # Fall back to the entire response
            action = response.strip()
    
    # Clean up the action
    action = action.replace("\n", "").strip()
    
    return action

def encode_image_to_base64(image_bytes: bytes) -> str:
    """
    Encode an image to base64 for including in prompts
    
    Args:
        image_bytes: Raw image data
        
    Returns:
        Base64 encoded image data URI
    """
    try:
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if image.mode in ("RGBA", "LA"):
            image = image.convert("RGB")
        
        # Encode as JPEG and convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/jpeg;base64,{image_base64}"
    except Exception as e:
        print(f"Error encoding image: {e}")
        return None

if __name__ == "__main__":
    from demoagent.browsergym_sync import BrowserController
    import time
    
    model_config = {
        "model_provider": "local",
        "model_name": "unsloth/gemma-3-27b-it-unsloth-bnb-4bit",
        "local_api_key": "FEEL_THE_AGI",
        "local_base_url": "http://localhost:7999/v1",
        "response_kwargs": {
            "max_tokens": 50,
            "temperature": 2.0,
            "top_p": 0.97,
            "extra_body":{"top_k": 128}
        }
    }
    task_config = {
        "goal": "Book a ride from Fitness Urbano to Pacific Cafe "
    }
    with BrowserController() as controller:
        controller.set_show_generic_nodes(False)
        controller.goto("https://evals-udriver.vercel.app/")
        time.sleep(3)
        
        axtree = controller.format_axtree(controller.get_observation())
        observation = {
            "axtree": axtree,
            "action_list": [],
            "previous_action_error": None,
            "screenshot": None
        }
        print(observation)
        
        action = get_agent_action(observation, model_config, task_config)
        print(action)
        
        controller.execute_action(action)
        time.sleep(3)
        
        axtree = controller.format_axtree(controller.get_observation())
        observation = {
            "axtree": axtree,
            "action_list": [action],
            "previous_action_error": None,
            "screenshot": None
        }
        print(observation)