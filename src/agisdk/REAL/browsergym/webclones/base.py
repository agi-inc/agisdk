import os
import json
import urllib.parse
import requests
import logging

import playwright.sync_api
from agisdk.REAL.browsergym.core.task import AbstractBrowserTask
from agisdk.REAL.browsergym.webclones.task_config import TaskConfig
from agisdk.REAL.browsergym.webclones.evaluate import WebCloneEvaluator
from agisdk.REAL.logging import logger as rich_logger

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
        self.requested_task_id = task_id
        self.task_config = TaskConfig(self.requested_task_id)
        self.task_id = getattr(self.task_config, "task_slug", task_id)
        self.task_version = getattr(self.task_config, "version", None)
        self.canonical_task_id = getattr(self.task_config, "canonical_id", self.task_id)
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
        else:
            if api_key is not None and model_id_name is not None and run_name is not None:
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
            
        self.evaluator = WebCloneEvaluator(task_config=self.task_config)
        self.goal = self.task_config.get_goal()
        self.url = self.task_config.get_start_url()
        if not self.url:
            if "WEBCLONE_URL" in os.environ:
                self.url = os.environ["WEBCLONE_URL"]
            else:
                raise ValueError("Provide a WebClones base URL or set it up as WEBCLONES_URL env var.")
        display_task_id = self.canonical_task_id or self.task_id
        rich_logger.info(f"⚙️ Initialized {display_task_id} task.")
        rich_logger.info(f"🎯 Goal: {self.goal}")

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

    def _is_v2_task(self) -> bool:
        """
        Determine if this is a v2 task.
        Checks multiple indicators:
        1. Task version attribute
        2. Task name contains '-v2' or '_v2'
        3. Task is loaded from v2/tasks/ directory
        4. Task config has version field
        """
        # Check version attribute
        if hasattr(self, 'task_version') and self.task_version:
            if str(self.task_version).lower() in ('v2', '2', '2.0'):
                return True
        
        # Check task config for version field
        if hasattr(self, 'task_config') and hasattr(self.task_config, 'task'):
            if hasattr(self.task_config.task, 'version'):
                version = str(self.task_config.task.version).lower()
                if version in ('v2', '2', '2.0'):
                    return True
        
        # Check if task is from v2 directory
        # Tasks in v2/tasks/ are v2 tasks even without -v2 suffix
        if hasattr(self, 'requested_task_id'):
            # Check if this is a webclones task (they're all in v2/tasks/ now)
            if 'webclones' in self.requested_task_id.lower():
                return True  # All webclones tasks use v2 evaluation
        
        # Check task ID for v2 suffix (explicit naming)
        if hasattr(self, 'task_id'):
            task_id_lower = self.task_id.lower()
            if '-v2' in task_id_lower or '_v2' in task_id_lower or task_id_lower.endswith('v2'):
                return True
        
        # Check canonical task ID
        if hasattr(self, 'canonical_task_id'):
            canonical_lower = self.canonical_task_id.lower()
            if '-v2' in canonical_lower or '_v2' in canonical_lower or canonical_lower.endswith('v2'):
                return True
        
        return False


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
        print("done", done)
        if done:
            env_state_json = self.get_finish_json(timeout=timeout)
            
            # LOCAL EVALUATION (always runs for immediate feedback)
            reward, _, message, info = self.evaluator.evaluate(env_state_json, model_response)
            message = "Task completed!" if done else "Task still in progress"
            info = {"env_state": env_state_json}
            info["local_reward"] = reward  # Track local evaluation result
            
            if model_response is None or model_response == "":
                model_response = "Done"
            
            # Check if this is a leaderboard submission
            is_leaderboard = getattr(self, 'run_id', '0') != '0'
            is_v2_task = self._is_v2_task()
                
            # Handle leaderboard submissions
            if is_leaderboard:
                print("is_leaderboard", is_leaderboard)
                if is_v2_task:
                    print("is_v2_task", is_v2_task)
                    # V2 TASK: Send to Railway for server-side evaluation and leaderboard submission
                    railway_api_base = os.getenv("RAILWAY_API_BASE")
                    if railway_api_base:
                        try:
                            railway_url = f"{railway_api_base.rstrip('/')}/evaluate"
                            
                            # Prepare task config for Railway API
                            # Note: evals and points are direct attributes of task, not in task.config
                            task_config_dict = {
                                'evals': [e.to_json() for e in self.task_config.task.evals],
                                'points': self.task_config.task.points,
                            }
                            
                            payload = {
                                "env_state": env_state_json,
                                "model_response": model_response,
                                "task_config": task_config_dict,
                                "llm": os.getenv("EVAL_LLM", "gpt-4.1"),
                                "run_id": self.run_id,
                                "task_id": self.task_id,
                                "leaderboard_api_url": os.getenv("LEADERBOARD_API_URL")
                            }
                            
                            logger.info(f"🚂 V2 Task: Sending to Railway for evaluation and leaderboard submission...")
                            
                            # Send to Railway (Railway will evaluate AND submit to leaderboard)
                            railway_response = requests.post(
                                railway_url, 
                                json=payload, 
                                timeout=30
                            )
                            
                            if railway_response.status_code == 200:
                                railway_result = railway_response.json()
                                railway_reward = railway_result.get('reward', 0.0)
                                info["railway_reward"] = railway_reward
                                info["railway_verified"] = True
                                info["leaderboard_submitted"] = railway_result.get('leaderboard_submitted', False)
                                logger.info(f"✅ Railway evaluation complete: reward={railway_reward}")
                                
                                # Warn if local and railway results don't match
                                if reward != railway_reward:
                                    logger.warning(f"⚠️ Evaluation mismatch! Local: {reward}, Railway: {railway_reward}")
                            else:
                                logger.error(f"❌ Railway returned status {railway_response.status_code}")
                                info["railway_verified"] = False
                                info["leaderboard_submitted"] = False
                                
                        except requests.exceptions.Timeout:
                            logger.error("❌ Railway request timed out")
                            info["railway_verified"] = False
                            info["leaderboard_submitted"] = False
                        except Exception as e:
                            logger.error(f"❌ Failed to send to Railway: {e}")
                            info["railway_verified"] = False
                            info["leaderboard_submitted"] = False
                    else:
                        logger.error("❌ RAILWAY_API_BASE not set for v2 task leaderboard submission")
                        info["railway_verified"] = False
                        info["leaderboard_submitted"] = False
                
                else:
                    # NON-V2 TASK: Use old behavior (optional Railway verification + webclones submit)
                    railway_api_base = os.getenv("RAILWAY_API_BASE")
                    if railway_api_base:
                        try:
                            railway_url = f"{railway_api_base.rstrip('/')}/evaluate"
                            
                            task_config_dict = {
                                'evals': [e.to_json() for e in self.task_config.task.evals],
                                'points': self.task_config.task.points,
                            }
                            
                            payload = {
                                "env_state": env_state_json,
                                "model_response": model_response,
                                "task_config": task_config_dict,
                                "llm": os.getenv("EVAL_LLM", "gpt-4.1"),
                                "run_id": self.run_id,
                                "task_id": self.task_id
                            }
                            
                            logger.info(f"🚂 Sending to Railway for verification...")
                            
                            railway_response = requests.post(
                                railway_url, 
                                json=payload, 
                                timeout=10
                            )
                            
                            if railway_response.status_code == 200:
                                railway_result = railway_response.json()
                                railway_reward = railway_result.get('reward', 0.0)
                                info["railway_reward"] = railway_reward
                                info["railway_verified"] = True
                                logger.info(f"✅ Railway verification complete: reward={railway_reward}")
                                
                                if reward != railway_reward:
                                    logger.warning(f"⚠️ Evaluation mismatch! Local: {reward}, Railway: {railway_reward}")
                            else:
                                logger.warning(f"⚠️ Railway returned status {railway_response.status_code}")
                                info["railway_verified"] = False
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Railway verification failed: {e}")
                            info["railway_verified"] = False
                    
                    # Submit to webclones /submit endpoint (old behavior for non-v2)
                    try:
                        import urllib.parse
                        encoded_response = urllib.parse.quote(model_response)
                        response = self.background_page.goto(
                            self.url + "/submit?retrieved_answer=" + encoded_response
                        )
                        if response is None:
                            print("Warning: No response received when submitting to leaderboard")
                        else:
                            status = response.status
                            if status is not None and status >= 400:
                                status_text = response.status_text or "Unknown status"
                                print(f"Warning: Leaderboard submission returned HTTP {status} ({status_text})")
                    except Exception as e:
                        print(f"Warning: Failed to submit response to server: {e}")
                    
        return reward, done, message, info