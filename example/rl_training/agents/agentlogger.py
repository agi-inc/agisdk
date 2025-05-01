import requests
import json
import time
from datetime import datetime
import os
import uuid
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)

getnow = lambda: datetime.utcnow().isoformat() + 'Z'

def log_agent_trajectory(prompt, steps, api_key=None, email="prannay@theagi.company"):
    """
    Log an agent trajectory to Multion API
    
    Args:
        prompt: Initial input prompt as string
        steps: List of dicts with "input" and "output" keys
        api_key: Multion API key
        email: User email for session
    """
    # Configuration
    BASE_URL = "https://api.multion.ai"
    SESSION_ID = str(uuid.uuid4())
    if api_key is None:
        api_key = os.getenv("MULTION_API_KEY")
    
    headers = {
        "Content-Type": "application/json",
        "X_MULTION_API_KEY": api_key
    }
    
    runid = str(uuid.uuid4())
    # Create session
    session_data = {
        "email": email,
        "session_id": SESSION_ID,
        "scenario": {"prompt": prompt},
        "source": "agent-logger",
        "run_id": runid,
        "agent_id": "research-agent",
        "agent_params": {"type": "research"},
        "browser_config": {"browser": "chrome", "headless": False},
        "user_id": "user-123",
        "to_delete": False,
        "created_at": getnow(),
        "updated_at": getnow(),
        "tags": ["research-agent"],
    }
    
    # Log session
    session_response = requests.post(
        f"{BASE_URL}/api/v1/agent-session",
        headers=headers,
        json=session_data
    )
    if session_response.status_code != 200:
        print("Error creating session:", session_response.json())
        raise Exception("Session creation failed")
        
    
    # Log initial prompt event
    start_time = int(time.time() * 1000)
    prompt_event = {
        "type": "AGENT_START",
        "session_id": SESSION_ID,
        "start_time": start_time,
        "latency": 0,
        "inputs": {"prompt": prompt},
        "outputs": {},
        "metadata": {"browser": "chrome"},
        "run_id": runid,
        "created_at": getnow(),
        "updated_at": getnow(),
    }

    
    requests.post(
        f"{BASE_URL}/api/v1/agent-event",
        headers=headers,
        json=prompt_event
    )
    
    # Log each step as an event
    for i, step in enumerate(steps):
        start_time = int(time.time() * 1000)            
        event_data = {
            "type": "AGENT_RESPONSE",  # Using a standard event type from testlogger
            "session_id": SESSION_ID,
            "start_time": start_time,
            "latency": 100,
            "inputs": step.get("inputs", {}),
            "outputs": {"message": step.get("outputs", "")} if isinstance(step.get("outputs"), str) else step.get("outputs", {}),
            "metadata": {"step": i+1, "browser": "chrome"},
            "run_id": runid,
            "created_at": getnow(),
            "updated_at": getnow(),
        }
        
        event_response = requests.post(
            f"{BASE_URL}/api/v1/agent-event",
            headers=headers,
            json=event_data
        )
        if event_response.status_code != 200:
            print("Error logging event:", event_response.json())
            raise Exception(f"Event logging failed for step {i+1}")
    
    # Log completion event
    completion_event = {
        "type": "AGENT_COMPLETE",
        "session_id": SESSION_ID,
        "start_time": int(time.time() * 1000),
        "latency": 0,
        "inputs": {"status": "complete"},
        "outputs": {"status": "complete"},
        "metadata": {"browser": "chrome"},
        "run_id": runid,
        "created_at": getnow(),
        "updated_at": getnow(),
    }
    
    requests.post(
        f"{BASE_URL}/api/v1/agent-event",
        headers=headers,
        json=completion_event
    )
    
    return SESSION_ID

# Example usage
if __name__ == "__main__":
    prompt = "Search for python tutorials"
    steps = [
        {"inputs": {"msg":"Navigate to google.com"}, "outputs": {"msg": "Loaded google.com"}},
        {"inputs": {"msg":"Search for python tutorials"}, "outputs": {"msg": "Results loaded"}},
        {"inputs": {"msg":"Click on the first result"}, "outputs": {"msg": "Navigated to tutorial page"}},
        {"inputs": {"msg":"Read the tutorial"}, "outputs": {"msg": "Tutorial read"}},
    ]
    
    session_id = log_agent_trajectory(prompt, steps)
    print(f"Logged trajectory with session ID: {session_id}")