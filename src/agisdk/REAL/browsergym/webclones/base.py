import os
import json
import urllib.parse
import requests
import logging

import playwright.sync_api
from agisdk.REAL.browsergym.core.task import AbstractBrowserTask
from agisdk.REAL.browsergym.webclones.task_config import (
    TaskConfig,
    DEFAULT_VERSION,
    split_task_reference,
)
from agisdk.REAL.browsergym.webclones.evaluate import WebCloneEvaluator
from agisdk.REAL.logging import logger as rich_logger

RAILWAY_API_BASE = "https://evaluate-production.up.railway.app/"

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

    def __init__(
        self,
        seed: int,
        task_name: str = None,
        task_version: str = None,
        task_id: str = None,
        run_id: str = None,
        api_key: str = None,
        model_id_name: str = None,
        run_name: str = None
    ) -> None:
        """
        Args:
            seed: Random seed for the task.
            task_name: Base task name (e.g. "dashdish-1").
            task_version: Version label (e.g. "v2").
            task_id: Canonical identifier ("v2.dashdish-1"). Deprecated in favour of
                     passing task_name and task_version explicitly.
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
        resolved_name: str
        resolved_version: str

        if task_name and task_version:
            resolved_name, resolved_version = task_name, task_version
        elif task_id:
            resolved_version, resolved_name = split_task_reference(task_id)
        elif task_name:
            resolved_name = task_name
            resolved_version = task_version or DEFAULT_VERSION
        else:
            raise ValueError("task_name and task_version are required.")

        self.task_config = TaskConfig(resolved_name, resolved_version)
        self.task_name = self.task_config.task_name
        self.task_version = self.task_config.version
        self.task_id = self.task_name
        self.canonical_task_id = self.task_config.canonical_id

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
        rich_logger.info(f"⚙️ Initialized {self.canonical_task_id} task.")
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
        logger.debug("Fetching finish JSON...")
        env_state_json = {}
        error_message = ""
        try:
            try:
                logger.debug("Navigating to finish endpoint for env state")
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

    def _has_script_eval(self) -> bool:
        """Return True if any evaluation uses a Python script."""
        logger.debug("Checking for script-based evals")
        try:
            evals = self.task_config.get_evals()
        except AttributeError:
            logger.debug("Task config missing evals list")
            return False
        return any(
            getattr(eval_config, "type", "") == "script"
            or getattr(eval_config, "script", "")
            for eval_config in evals
        )

    def _build_task_config_payload(self) -> dict:
        """Build a minimal task_config payload for remote evaluation."""
        logger.debug("Building task_config payload for Railway submission")
        task = getattr(self.task_config, "task", None)
        if not task:
            logger.warning("Task config missing task details; returning empty payload")
            return {"evals": [], "points": 0.0}

        evals_payload = []
        for eval_config in getattr(task, "evals", []):
            if hasattr(eval_config, "to_json"):
                evals_payload.append(eval_config.to_json())
            else:
                evals_payload.append(getattr(eval_config, "__dict__", {}))

        payload: dict[str, object] = {
            "evals": evals_payload,
            "points": getattr(task, "points", 0.0) or 0.0,
        }
        script_names = [
            getattr(eval_config, "script")
            for eval_config in getattr(task, "evals", [])
            if getattr(eval_config, "script", "")
        ]
        if script_names:
            payload["eval_scripts"] = script_names
        return payload

    def _build_env_state_payload(self, env_state_json: dict) -> dict:
        """Extract the diff-only sections required for remote evaluation."""
        try:
            return {
                "initialfinaldiff": env_state_json["initialfinaldiff"],
                "differences": env_state_json["differences"],
            }
        except KeyError as exc:
            missing_key = exc.args[0]
            raise KeyError(f"Env state missing required diff section: {missing_key}") from exc

    def _submit_script_leaderboard(
        self, env_state_payload: dict, model_response: str, info: dict, local_reward: float
    ) -> None:
        """Submit results for script-based tasks to the external evaluation service."""
        logger.info("Preparing Railway submission for script-based task")
        railway_url = f"{RAILWAY_API_BASE.rstrip('/')}/evaluate"
        payload = {
            "env_state": env_state_payload,
            "model_response": model_response,
            "task_config": self._build_task_config_payload(),
            "run_id": self.run_id,
            "task_id": self.task_id,
        }

        logger.info("🚂 Script task: sending to Railway for evaluation and leaderboard submission...")
        try:
            logger.debug(f"POST {railway_url} with payload keys: {list(payload.keys())}")
            railway_response = requests.post(railway_url, json=payload, timeout=30)
        except requests.exceptions.Timeout:
            logger.error("❌ Railway request timed out")
            info["railway_verified"] = False
            info["leaderboard_submitted"] = False
            return
        except Exception as exc:
            logger.error(f"❌ Failed to send to Railway: {exc}")
            info["railway_verified"] = False
            info["leaderboard_submitted"] = False
            return

        if railway_response.status_code == 200:
            try:
                logger.debug("Railway responded with 200; parsing JSON")
                railway_result = railway_response.json()
            except json.JSONDecodeError as exc:
                logger.error(f"❌ Railway response was not valid JSON: {exc}")
                info["railway_verified"] = False
                info["leaderboard_submitted"] = False
                return

            railway_reward = railway_result.get("reward", 0.0)
            info["railway_reward"] = railway_reward
            info["railway_verified"] = True
            info["leaderboard_submitted"] = railway_result.get("leaderboard_submitted", False)
            logger.info(f"✅ Railway evaluation complete: reward={railway_reward}")
            logger.debug(f"Railway result payload: {railway_result}")

            if local_reward != railway_reward:
                logger.warning(f"⚠️ Evaluation mismatch! Local: {local_reward}, Railway: {railway_reward}")
        else:
            logger.error(f"❌ Railway returned status {railway_response.status_code}: {railway_response.text}")
            info["railway_verified"] = False
            info["leaderboard_submitted"] = False

    def _submit_standard_leaderboard(self, model_response: str) -> None:
        """Submit results to the legacy WebClones leaderboard endpoint."""
        try:
            logger.info("Submitting result to legacy /submit endpoint")
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
        except Exception as exc:
            print(f"Warning: Failed to submit response to server: {exc}")


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
        if len(assistant_messages)>1:
            done = True
        logger.debug(f"Validation called. done={done}, leaderboard_run={getattr(self, 'run_id', '0')}")
        if done:
            env_state_json = self.get_finish_json(timeout=timeout)
            env_state_payload = self._build_env_state_payload(env_state_json)
            reward, _, message, info = self.evaluator.evaluate(env_state_json, model_response)
            message = "Task completed!" if done else "Task still in progress"
            info = {"env_state": env_state_json, "local_reward": reward}
            if model_response is None or model_response == "":
                model_response = "Done"
            is_leaderboard_submission = getattr(self, "run_id", "0") != "0"
            logger.debug(f"Leaderboard submission? {is_leaderboard_submission}")
            if is_leaderboard_submission:
                if self._has_script_eval():
                    logger.debug("Detected script eval; using Railway submission path")
                    self._submit_script_leaderboard(env_state_payload, model_response, info, reward)
                else:
                    logger.debug("No script eval; using legacy submit endpoint")
                    self._submit_standard_leaderboard(model_response)

        return reward, done, message, info
