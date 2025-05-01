import requests
import json
import time
from datetime import datetime
import os
import uuid

getnow = lambda: datetime.utcnow().isoformat() + 'Z'

class AgentLogger:
    """
    Class for logging agent trajectories to Multion API
    """
    
    def __init__(self, prompt, api_key=None, email="prannay@theagi.company"):
        """
        Initialize an agent logger session
        
        Args:
            prompt: Initial input prompt as string
            api_key: Multion API key
            email: User email for session
        """
        # Configuration
        self.BASE_URL = "https://api.multion.ai"
        self.SESSION_ID = str(uuid.uuid4())
        self.runid = str(uuid.uuid4())
        self.prompt = prompt
        self.email = email
        self.step_count = 0
        
        if api_key is None:
            self.api_key = os.getenv("MULTION_API_KEY")
        else:
            self.api_key = api_key
            
        self.headers = {
            "Content-Type": "application/json",
            "X_MULTION_API_KEY": self.api_key
        }
        
        # Initialize the session
        self._create_session()
        self._log_start_event()
        
    def _create_session(self):
        """Create the initial agent session"""
        session_data = {
            "email": self.email,
            "session_id": self.SESSION_ID,
            "scenario": {"prompt": self.prompt},
            "source": "agent-logger",
            "run_id": self.runid,
            "agent_id": "research-agent",
            "agent_params": {"type": "research"},
            "browser_config": {"browser": "chrome", "headless": False},
            "user_id": "user-123",
            "to_delete": False,
            "created_at": getnow(),
            "updated_at": getnow(),
            "tags": ["research-agent"],
        }
        
        session_response = requests.post(
            f"{self.BASE_URL}/api/v1/agent-session",
            headers=self.headers,
            json=session_data
        )
        if session_response.status_code != 200:
            print("Error creating session:", session_response.json())
            raise Exception("Session creation failed")
            
    def _log_start_event(self):
        """Log the initial prompt event"""
        start_time = int(time.time() * 1000)
        prompt_event = {
            "type": "AGENT_START",
            "session_id": self.SESSION_ID,
            "start_time": start_time,
            "latency": 0,
            "inputs": {"prompt": self.prompt},
            "outputs": {},
            "metadata": {"browser": "chrome"},
            "run_id": self.runid,
            "created_at": getnow(),
            "updated_at": getnow(),
        }

        requests.post(
            f"{self.BASE_URL}/api/v1/agent-event",
            headers=self.headers,
            json=prompt_event
        )
    
    def log_step(self, inputs, outputs):
        """
        Log a single step of the agent trajectory
        
        Args:
            inputs: Dict or string containing step inputs
            outputs: Dict or string containing step outputs
        
        Returns:
            None
        """
        self.step_count += 1
        
        # Convert to dict format if string
        if isinstance(inputs, str):
            inputs = {"msg": inputs}
        if isinstance(outputs, str):
            outputs = {"msg": outputs}
            
        start_time = int(time.time() * 1000)            
        event_data = {
            "type": "AGENT_RESPONSE",
            "session_id": self.SESSION_ID,
            "start_time": start_time,
            "latency": 100,
            "inputs": inputs,
            "outputs": {"message": outputs} if isinstance(outputs, str) else outputs,
            "metadata": {"step": self.step_count, "browser": "chrome"},
            "run_id": self.runid,
            "created_at": getnow(),
            "updated_at": getnow(),
        }
        
        event_response = requests.post(
            f"{self.BASE_URL}/api/v1/agent-event",
            headers=self.headers,
            json=event_data
        )
        if event_response.status_code != 200:
            print("Error logging event:", event_response.json())
            raise Exception(f"Event logging failed for step {self.step_count}")
    
    def complete(self):
        """
        Log completion event and finish the trajectory
        
        Returns:
            str: The session ID
        """
        completion_event = {
            "type": "AGENT_COMPLETE",
            "session_id": self.SESSION_ID,
            "start_time": int(time.time() * 1000),
            "latency": 0,
            "inputs": {"status": "complete"},
            "outputs": {"status": "complete"},
            "metadata": {"browser": "chrome"},
            "run_id": self.runid,
            "created_at": getnow(),
            "updated_at": getnow(),
        }
        
        requests.post(
            f"{self.BASE_URL}/api/v1/agent-event",
            headers=self.headers,
            json=completion_event
        )
        
        return self.SESSION_ID


# Example usage
if __name__ == "__main__":
    # Using the class-based approach
    logger = AgentLogger("Search for python tutorials")
    
    logger.log_step({"msg":"Navigate to google.com"}, {"msg": "Loaded google.com"})
    logger.log_step({"msg":"Search for python tutorials"}, {"msg": "Results loaded"})
    logger.log_step({"msg":"Click on the first result"}, {"msg": "Navigated to tutorial page"})
    logger.log_step({"msg":"Read the tutorial"}, {"msg": "Tutorial read"})
    
    session_id = logger.complete()
    print(f"Logged trajectory with session ID: {session_id}")