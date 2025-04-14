import os, sys, asyncio
import multiprocessing
from dotenv import load_dotenv
from pydantic import SecretStr

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set")
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI
from browser_use import Agent, Controller
from browser_use.browser.browser import Browser, BrowserConfig
from agisdk import EvalHarness

async def browseruse_async_agent(prompt, cdp_url, max_steps, task_dir):
    print(f"Agent received prompt: {prompt}")
    print(f"Connecting to CDP URL: {cdp_url}")
    print(f"Max steps: {max_steps}")
    print(f"Task directory: {task_dir}")
    
    # Configure browser with headless=False for visibility
    browser = Browser(config=BrowserConfig(cdp_url=cdp_url))
    model = ChatOpenAI(model="gpt-4o", temperature=0.0, api_key=SecretStr(api_key))
    
    # Set up the gif path if task_dir is provided
    if task_dir:
        os.makedirs(task_dir, exist_ok=True)
        gif_path = os.path.join(task_dir, "session.gif")
        generate_gif = gif_path
        
        # Also set up conversation saving
        save_conversation_path = os.path.join(task_dir, "conversation")
    else:
        save_conversation_path = None
    
    # Initialize the agent with the task and options
    agent = Agent(
        task=prompt, 
        use_vision=True,
        max_actions_per_step=1,
        llm=model, 
        browser=browser,
        save_conversation_path=save_conversation_path
    )
    print("Agent initialized 🔥")
    
    # Run the agent with specified max_steps and get the history
    history = await agent.run(max_steps=max_steps)
    print("Agent finished running 🏃🏼‍♂️")
    
    # Extract the final result from the agent's history
    final_result = history.final_result()
    
    # If no explicit final result, try to get the most relevant information
    if not final_result:
        # Get all extracted content from the history
        all_content = history.extracted_content()
        if all_content:
            # Join all extracted content with newlines
            final_result = "\n".join(all_content)
        else:
            final_result = "Done"
    
    # Save history to JSON if logging directory is provided
    if task_dir:
        history_path = os.path.join(task_dir, "agent_history.json")
        history.save_to_file(history_path)
        print(f"Saved agent history to {history_path}")
    
    # Clean up
    await browser.close()
    print("Browser closed 🧹")
    
    # Return the extracted information instead of just "agent finished"
    return final_result

def browseruse_agent(prompt, cdp_url, max_steps, task_dir):
    return asyncio.run(browseruse_async_agent(prompt, cdp_url, max_steps, task_dir))

# Set up the harness with our agent function
harness = EvalHarness(
    agent_fn=browseruse_agent, 
    type="cdp", 
    max_steps=25,
    headless=False,  # Set to True to run in headless mode    
)

# Define a main function to run the harness
def main():
    # Choose which tasks to run:

    # Option 1: Run all tasks
    # harness.run(local=True, use_cache=True, dir="./browseruse", tasks="all", parallel=True, num_workers=4)

    # Option 2: Run a single specific task
    # harness.run(local=True, use_cache=True, dir="./browseruse", tasks="udriver-1", parallel=True, num_workers=4)

    # Option 3: Run all tasks of a specific type
    harness.run(local=True, use_cache=True, dir="./udrive", tasks="udriver", parallel=False, num_workers=1)

    # Option 4: Run a specific list of tasks
    # harness.run(local=True, use_cache=True, dir="./browseruse", tasks=["udriver-1", "udriver-2"], parallel=True, num_workers=4)
    
    # Show the results statistics
    harness.show_results("./browseruse")

# Proper idiom for multiprocessing
if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()