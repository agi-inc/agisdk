import os
import json

import playwright.sync_api
from agisdk.real.browsergym.core.task import AbstractBrowserTask
from agisdk.real.browsergym.webclones.task_config import TaskConfig
from agisdk.real.browsergym.webclones.evaluate import WebCloneEvaluator

class AbstractWebCloneTask(AbstractBrowserTask):
    """
    Abstract class for all WebClones tasks
    """

    @classmethod
    def get_task_id(cls):
        return cls.task_id

    def __init__(self, seed: int, task_id: str, run_id: str = None) -> None:
        """
        Args:
            seed: Random seed for the task.
            task_id: ID of the task to load.
            run_id: Optional run ID for the task. If provided, overrides the run_id in the task config.
                   This is used for leaderboard submissions.
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
        # then check task config, finally default to '0'
        env_run_id = os.environ.get("RUNID")
        if env_run_id:
            self.run_id = env_run_id
        elif run_id is not None:
            self.run_id = run_id
        elif 'run_id' in self.task_config.task.config:
            self.run_id = self.task_config.task.config['run_id']
        else:
            self.run_id = '0'
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
        config_url = self.url + f"/config?run_id={self.run_id}&task_id={self.task_id}"
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
                    self.background_page.goto(self.url + "/submit?retrieved_answer=" + encoded_response)
                except Exception as e:
                    print(f"Warning: Failed to submit response to server: {e}")
        print(f"reward: {reward}, done: {done}, user message: '{message}', model response: {response}")
        return reward, done, message, info

