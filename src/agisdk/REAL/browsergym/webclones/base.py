import os
import json
import urllib.parse
import requests
import logging

import playwright.sync_api
from agisdk.REAL.browsergym.core.task import AbstractBrowserTask
from agisdk.REAL.browsergym.webclones.task_config import TaskConfig
from agisdk.REAL.browsergym.webclones.evaluate import WebCloneEvaluator

logger = logging.getLogger(__name__)

def get_run_id_from_api(api_key: str, model_id_name: str, run_name: str):
    """
    Get a run ID from the REAL evaluations API using an API key, model name, and run name.
    
    Args:
        api_key: REAL API key
        model_id_name: Name of the model being used
        run_name: Human-readable name for this run
        
    Returns:
        A run ID string if successful, None otherwise
    """
    try:
        # URL encode parameters
        encoded_model_id_name = urllib.parse.quote(model_id_name)
        encoded_run_name = urllib.parse.quote(run_name)
        
        # Construct the API URL
        # Prefer the REAL_API_BASE env override to support domain migrations (e.g., realevals.ai)
        base_url = os.getenv("REAL_API_BASE", "https://www.realevals.ai")
        url = f"{base_url.rstrip('/')}/api/runKey?api_key={api_key}&model_name={encoded_model_id_name}&run_name={encoded_run_name}"
        
        # Make the request
        response = requests.get(url, timeout=10)
        
        # Check if request was successful
        if response.status_code == 200:
            data = response.json()
            if "newRunId" in data:
                return data["newRunId"]
            else:
                logger.error(f"API response did not contain newRunId: {data}")
        else:
            logger.error(f"API request failed with status code {response.status_code}: {response.text}")
            
    except Exception as e:
        logger.error(f"Error getting run ID from API: {e}")
        
    return None

class AbstractWebCloneTask(AbstractBrowserTask):
    """
    Abstract class for all WebClones tasks
    """

    @classmethod
    def get_task_id(cls):
        return cls.task_id

    def __init__(self, seed: int, task_id: str, run_id: str = None, api_key: str = None, model_id_name: str = None, run_name: str = None) -> None:
        """
        Args:
            seed: Random seed for the task.
            task_id: ID of the task to load.
            run_id: Optional run ID for the task. If provided, overrides the run_id in the task config.
                   This is used for leaderboard submissions.
            api_key: Optional REAL API key for automatic run_id generation.
            model_id_name: Optional model name for automatic run_id generation.
            run_name: Optional run name for automatic run_id generation.
            base_url: str (optional), the base URL where the task's HTML file is to be found.
                     If not provided, the WEBCLONES_URL environment variable will be used.
        """
        super().__init__(seed)

        self.seed = seed
        self.task_id = task_id
        self.task_config = TaskConfig(self.task_id)
        if not self.task_config.is_valid_config():
            raise ValueError(f"Invalid task configuration for task ID: {self.task_id}")
            
        # Set run_id: prioritize RUNID environment variable,
        # then the explicitly provided run_id parameter,
        # then try to generate from API if api_key, model_id_name, and run_name are provided,
        # then check task config, finally default to '0'
        env_run_id = os.environ.get("RUNID")
        if env_run_id:
            self.run_id = env_run_id
            logger.info(f"Using run_id from environment variable: {self.run_id}")
        elif run_id is not None:
            self.run_id = run_id
            logger.info(f"Using explicitly provided run_id: {self.run_id}")
        elif api_key is not None and model_id_name is not None and run_name is not None:
            # Try to get run_id from API
            logger.info(f"Attempting to get run_id from API for model '{model_id_name}' and run '{run_name}'")
            api_run_id = get_run_id_from_api(api_key, model_id_name, run_name)
            if api_run_id:
                self.run_id = api_run_id
                # Also set the environment variable for other components
                os.environ["RUNID"] = api_run_id
                logger.info(f"Successfully obtained run_id from API: {self.run_id}")
            else:
                # Fall back to task config or default
                if 'run_id' in self.task_config.task.config:
                    self.run_id = self.task_config.task.config['run_id']
                    logger.info(f"Using run_id from task config: {self.run_id}")
                else:
                    self.run_id = '0'
                    logger.info(f"Using default run_id: {self.run_id}")
        elif 'run_id' in self.task_config.task.config:
            self.run_id = self.task_config.task.config['run_id']
            logger.info(f"Using run_id from task config: {self.run_id}")
        else:
            self.run_id = '0'
            logger.info(f"Using default run_id: {self.run_id}")
            
        # Check if REAL_API_KEY environment variable is set and no run_id was found yet
        if self.run_id == '0' and os.environ.get("REAL_API_KEY") and model_id_name is not None and run_name is not None:
            env_api_key = os.environ.get("REAL_API_KEY")
            logger.info(f"Attempting to get run_id from API using REAL_API_KEY for model '{model_id_name}' and run '{run_name}'")
            api_run_id = get_run_id_from_api(env_api_key, model_id_name, run_name)
            if api_run_id:
                self.run_id = api_run_id
                # Also set the environment variable for other components
                os.environ["RUNID"] = api_run_id
                logger.info(f"Successfully obtained run_id from API: {self.run_id}")
        self.evaluator = WebCloneEvaluator(task_config=self.task_config)
        self.goal = self.task_config.get_goal()
        self.url = self.task_config.get_start_url()
        if not self.url:
            if "WEBCLONE_URL" in os.environ:
                self.url = os.environ["WEBCLONE_URL"]
            else:
                raise ValueError("Provide a WebClones base URL or set it up as WEBCLONES_URL env var.")
        print(f"Initialized {self.task_id} task.")
        print(f"Goal: {self.goal}")

    def setup(self, page: playwright.sync_api.Page) -> tuple[str, dict]:
        self.page = page
        self.background_page = page.context.new_page()
        config_url = self.url + f"/config?run_id={self.run_id}&task_id={self.task_id}&latency=0"
        self.background_page.goto(config_url)
        self.background_page.wait_for_load_state("networkidle")
        finish_url = self.url + "/finish"
        self.background_page.goto(finish_url)
        self.page.bring_to_front()  # Ensure main page stays focused
        self.page.goto(self.url)
        return self.goal, {}

    def teardown(self) -> None:
        self.background_page.close()
        self.page.close()

    def get_finish_json(self, timeout: int = 1000) -> dict:
        env_state_json = {}
        error_message = ""
        try:
            try:
                self.background_page.goto(self.url+"/finish", timeout=timeout)
                self.background_page.wait_for_load_state("networkidle", timeout=timeout)
                pre_element = self.background_page.wait_for_selector("pre")
                if pre_element:
                    env_state = pre_element.inner_text()
                    try:
                        env_state_json = json.loads(env_state)
                    except json.JSONDecodeError as e:
                        error_message = f"Invalid JSON format: {str(e)}"
                else:
                    error_message = "No state data available"
            except playwright.sync_api.TimeoutError:
                error_message = "Validation endpoint not yet available"
        except Exception as e:
            error_message = f"Validation error: {str(e)}"
        if error_message != "":
            raise ValueError(error_message)
        return env_state_json


    def validate(
        self, 
        page: playwright.sync_api.Page, 
        chat_messages: list[str],
        timeout: int = 1000,
        verbose: bool = True
    ) -> tuple[float, bool, str, dict]:
        reward, done, message, info = 0.0, False, "", {}
        # Treat model response as a challenge solution submission
        assistant_messages = [m for m in chat_messages if m["role"] == "assistant"]
        model_response = assistant_messages[-1]['message']
        response = None
        if len(assistant_messages)>1:
            done = True
            response = assistant_messages[1]['message']
        if done:
            env_state_json = self.get_finish_json(timeout=timeout)
            reward, _, message, info = self.evaluator.evaluate(env_state_json, model_response)
            message = "Task completed!" if done else "Task still in progress"
            info = {"env_state": env_state_json}
            if model_response is None or model_response == "":
                model_response = "Done"
                
            # Only submit to the server if a run_id was provided
            # This sends the agent's answer to the leaderboard server
            if getattr(self, 'run_id', '0') != '0':
                try:
                    # URL encode the response for safety 
                    import urllib.parse
                    encoded_response = urllib.parse.quote(model_response)
                    response = self.background_page.goto(
                        self.url + "/submit?retrieved_answer=" + encoded_response
                    )
                    if response is None:
                        print("Warning: No response received when submitting to leaderboard at realevals.")
                    else:
                        status = response.status
                        if status is not None and status >= 400:
                            status_text = response.status_text or "Unknown status"
                            print(
                                f"Warning: Leaderboard submission returned HTTP {status} ({status_text}) "
                                f"from realevals."
                            )
                except Exception as e:
                    print(f"Warning: Failed to submit response to server: {e}")
                    
        return reward, done, message, info
