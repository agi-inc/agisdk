import dataclasses
from typing import Dict, Tuple, Optional

from agisdk import REAL


class MyCustomAgent(REAL.Agent):
    def __init__(self) -> None:
        super().__init__()
        self.steps = 0
        
    def get_agent_action(self, obs) -> Tuple[Optional[str], Optional[str]]:
        """
        Core agent logic - analyze observation and decide on action.
        
        Returns:
            Tuple of (action, final_message)
            - If action is None, episode ends with final_message
            - If action is not None, the agent takes the action and continues
        """
        self.steps += 1
        
        # Example of simple decision making based on URL
        current_url = obs.get("url", "")
        
    
    def get_action(self, obs: dict) -> Tuple[str, Dict]:
        """
        Convert agent's high-level action to browsergym action.
        This method is required by the browsergym interface.
        """
        agent_action, final_message = self.get_agent_action(obs)
        
        if final_message:
            # End the episode with a message
            return f"send_msg_to_user(\"{final_message}\")", {}
        else:
            # Continue with the specified action
            return agent_action, {}

@dataclasses.dataclass
class MyCustomAgentArgs(REAL.AbstractAgentArgs):
    agent_name: str = "MyCustomAgent"
    
    def make_agent(self):
        return MyCustomAgent()


# Example creating and using a custom agent
def run_custom_agent():
    # Create harness with custom agent
    harness = REAL.harness(
        agentargs=MyCustomAgentArgs(),
        headless=False,
    )
    
    # Run the task
    results = harness.run()
    return results

if __name__ == "__main__":
    results = run_custom_agent()
