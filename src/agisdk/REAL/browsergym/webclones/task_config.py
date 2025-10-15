"""
This module provides functionality to load and manage task configurations.
"""

import json
from typing import Dict, Any, Optional, Tuple
import requests
import os

from dataclasses import dataclass, asdict

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VERSION = "v2"
SUPPORTED_VERSIONS = ("v2",)


def _build_version_dirs() -> Dict[str, str]:
    dirs: Dict[str, str] = {}
    for version in SUPPORTED_VERSIONS:
        version_dir = os.path.join(CURRENT_DIR, version)
        tasks_dir = os.path.join(version_dir, "tasks")
        if os.path.isdir(tasks_dir):
            dirs[version] = version_dir
    if DEFAULT_VERSION not in dirs:
        raise FileNotFoundError(f"Default task version '{DEFAULT_VERSION}' is missing.")
    return dirs


VERSION_DIRS = _build_version_dirs()


def _tasks_for_version(version: str) -> list[str]:
    if version not in VERSION_DIRS:
        raise ValueError(f"Unknown task version '{version}'")
    tasks_dir = os.path.join(VERSION_DIRS[version], "tasks")
    task_files = [
        task[:-5] for task in os.listdir(tasks_dir) if task.endswith(".json")
    ]
    return sorted(task_files)


TASKS_BY_VERSION = {version: _tasks_for_version(version) for version in VERSION_DIRS}


CANONICAL_TASK_IDS = sorted(
    {f"{version}.{slug}" for version, tasks in TASKS_BY_VERSION.items() for slug in tasks}
)


LEGACY_TASK_IDS = sorted({slug for tasks in TASKS_BY_VERSION.values() for slug in tasks})


TASKS = sorted(set(LEGACY_TASK_IDS) | set(CANONICAL_TASK_IDS))


def _resolve_task_reference(task_ref: str) -> Tuple[str, str]:
    if not TASKS:
        raise ValueError("No tasks available for WebClones.")

    reference = (task_ref or DEFAULT_VERSION).strip()
    version = DEFAULT_VERSION
    remainder = reference

    if "." in reference:
        potential_version, rest = reference.split(".", 1)
        if potential_version in VERSION_DIRS:
            version = potential_version
            remainder = rest
        else:
            remainder = reference
    elif reference in VERSION_DIRS:
        version = reference
        remainder = ""

    tasks = TASKS_BY_VERSION.get(version, [])
    if not tasks:
        raise ValueError(f"No tasks found for version '{version}'")

    if remainder == "":
        return version, tasks[0]

    if remainder in tasks:
        return version, remainder

    if "-" not in remainder:
        prefix_matches = [task for task in tasks if task.startswith(f"{remainder}-")]
        if prefix_matches:
            return version, prefix_matches[0]

    # Legacy fallback (no version provided)
    if "." not in reference and reference in tasks:
        return version, reference

    raise FileNotFoundError(f"Task reference '{task_ref}' could not be resolved.")

@dataclass
class Eval:
    """
    A class to represent evaluation configurations.
    :param type: The type of evaluation
    :param state_variable_path: The path to the state variable to evaluate
    :param expected_value: The expected value of the state variable
    :param reference_answer: The reference answer for the task
    :param query: The JMESPath query to evaluate
    :param description: A description of the evaluation
    :param script: The Python script filename for subprocess-based evaluation
    """
    type: str = ""
    expected_value: str = ""
    state_variable_path: str = ""
    rubric: str = ""
    query: str = ""
    description: str = ""
    possible: bool = True
    script: str = ""

    

    def to_json(self) -> Dict[str, Any]:
        """
        Convert the evaluation configuration to a JSON dictionary.
        :return: The evaluation configuration as a dictionary.
        """
        return asdict(self)

@dataclass
class Task:
    """
    A class to represent a specific task configuration.
    :param id: The unique identifier for the task
    :param start_url: The starting URL for the task
    :param goal: The goal or objective that needs to be accomplished
    :param eval: The evaluation configuration for determining task completion
    """

    id: str
    evals: list[Eval]
    start_url: str
    goal: str
    difficulty: str
    challengeType: str
    points: float
    config: Optional[Dict[str, Any]] = None
    possible: bool = True
    description: str = ""


    def to_json(self) -> Dict[str, Any]:
        """
        Convert the task configuration to a JSON dictionary.
        :return: The task configuration as a dictionary.
        """
        return asdict(self)

class TaskConfig:
    def __init__(self, input_source: str, is_path: bool = False) -> None:
        self.version = DEFAULT_VERSION
        self.task_slug = ""
        self.base_dir = ""
        self.tasks_dir = ""
        self.eval_scripts_dir = ""
        self.canonical_id = ""

        # Check if the input is a file path or an ID
        if os.path.exists(input_source) and input_source.endswith('.json'):
            # It's a file path
            abs_path = os.path.abspath(input_source)
            self.config_json = self.from_json_file(abs_path)
            self.task_slug = os.path.splitext(os.path.basename(abs_path))[0]
            rel_parts = os.path.relpath(abs_path, CURRENT_DIR).split(os.sep)
            maybe_version = rel_parts[0] if rel_parts else DEFAULT_VERSION
            if maybe_version in VERSION_DIRS:
                self._set_version_paths(maybe_version)
            else:
                self._set_version_paths(DEFAULT_VERSION)
            self.canonical_id = f"{self.version}.{self.task_slug}"
        else:
            # It's an ID
            self.config_json = self.load_from_id(input_source)

        self.id = self.canonical_id if self.canonical_id else input_source
        
        # Validate configuration first
        if not self.is_valid_config():
            raise ValueError(f"Invalid task configuration for task ID: {self.id}")
        
        # Create Eval instance
        eval_configs = self.config_json['evals']
        eval_instances = []
        for eval_config in eval_configs:
            # Check if this is a script-based eval
            if 'script' in eval_config and eval_config['script']:
                # Set type to 'script' for subprocess-based evaluation
                if 'type' not in eval_config or not eval_config['type']:
                    eval_config['type'] = 'script'
            eval_instances.append(Eval(**eval_config))

        # Fetch url
        url = self.config_json['website']['url']
        
        # Remove eval and url from config_json to avoid duplication
        config_without_eval_and_url = self.config_json.copy()
        config_without_eval_and_url.pop('evals')
        config_without_eval_and_url.pop('website')
        
        # Create Task instance with the eval instance
        self.task = Task(evals=eval_instances, start_url=url, **config_without_eval_and_url)
    
    def _set_version_paths(self, version: str) -> None:
        if version not in VERSION_DIRS:
            raise ValueError(f"Unknown task version '{version}'")
        self.version = version
        self.base_dir = VERSION_DIRS[version]
        self.tasks_dir = os.path.join(self.base_dir, "tasks")
        self.eval_scripts_dir = os.path.join(self.base_dir, "eval_scripts")

    def load_from_id(self, task_ref: str) -> Dict[str, Any]:
        """
        Load the task configuration from a JSON file given a task ID.
        :param id: The id of the task.
        :return: The task configuration as a dictionary.
        """
        version, task_slug = _resolve_task_reference(task_ref)
        self._set_version_paths(version)
        self.task_slug = task_slug
        self.canonical_id = f"{self.version}.{self.task_slug}"
        path = os.path.join(self.tasks_dir, f"{task_slug}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Task configuration file not found: {path}")
        return self.from_json_file(path)

    def from_json_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load the task configuration from a JSON file.
        :param file_path: The path to the JSON file.
        :return: The task configuration as a dictionary.
        """
        with open(file_path, "r", encoding="utf-8") as file:
            config_json = json.load(file)
        return config_json
    
    def to_json(self) -> Dict[str, Any]:
        """
        Convert the task configuration to a JSON dictionary.
        :return: The task configuration as a dictionary.
        """
        return self.task.to_json()

    def get_task_id(self) -> str:
        """
        Get the task ID from the configuration.
        :return: The task ID as a string.
        """
        return self.task.id
    
    def get_start_url(self) -> str:
        """
        Get the start URL from the configuration.
        :return: The start URL as a string.
        """
        return self.task.start_url
    
    def get_goal(self) -> str:
        """
        Get the goal from the configuration.
        :return: The goal as a string.
        """
        return self.task.goal
    
    def get_evals(self) -> str:
        """
        Get the goal from the configuration.
        :return: The goal as a string.
        """
        return self.task.evals
    
    def is_task_url_reachable(self):
        try:
            response = requests.get(self.get_start_url(), timeout=5000)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            return False

    def is_valid_config(self) -> bool:
        """
        Validate the task configuration. Ensure necessary fields are present.
        :return: True if valid, False otherwise.
        """
        # required_keys = ["id", "start_url", "goal", "eval"]
        required_keys = ["id", "website", "goal", "evals"]
        for key in required_keys:
            if key not in self.config_json:
                print(f"Missing required key: {key}")
                return False
        return True

    # def get_config_variable_paths(self) -> str:
    #     """
    #     Get the state variable path from the configuration.
    #     :return: The state variable path as a string.
    #     """
    #     return self.task.eval.state_variable_path

    def get_evaluation_type(self) -> str:
        """
        Get the evaluation type from the configuration.
        :return: The evaluation type as a string.
        """
        return self.task.challengeType
    
    def get_reference_answer(self) -> str:
        """
        Get the reference answer from the configuration.
        :return: The reference answer as a string.
        """
        return self.task.eval.reference_answer
    
    def get_expected_value(self) -> str:
        """
        Get the expected value from the configuration.
        :return: The expected value as a string.
        """
        return self.task.eval.expected_value
        

    
