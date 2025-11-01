"""
Task configuration loading with explicit version support.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple, List

import requests

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VERSION = "v1"


VERSION_DIRS: Dict[str, str] = {
    "v1": os.path.join(CURRENT_DIR, "v1"),
    "v2": os.path.join(CURRENT_DIR, "v2"),
}

for version, path in VERSION_DIRS.items():
    if not os.path.isdir(path):
        raise FileNotFoundError(f"Configured task version '{version}' is missing: {path}")


def _tasks_for_version(version: str) -> list[str]:
    if version not in VERSION_DIRS:
        raise ValueError(f"Unknown task version '{version}'")
    tasks_dir = os.path.join(VERSION_DIRS[version], "tasks")
    return sorted(
        task[:-5]
        for task in os.listdir(tasks_dir)
        if task.endswith(".json")
    )


TASKS_BY_VERSION = {version: _tasks_for_version(version) for version in VERSION_DIRS}


TASK_INDEX: Dict[str, Tuple[str, str]] = {
    f"{version}.{task_name}": (version, task_name)
    for version, task_names in TASKS_BY_VERSION.items()
    for task_name in task_names
}


TASKS = sorted(TASK_INDEX.keys())


def split_task_reference(task_reference: str) -> Tuple[str, str]:
    """
    Split a task reference into (version, task_name).

    Accepts either '<version>.<task_name>' or '<task_name>' (defaults to DEFAULT_VERSION).
    """
    reference = (task_reference or "").strip()
    if not reference:
        raise ValueError("Task reference must be a non-empty string.")

    if "." in reference:
        version_candidate, name = reference.split(".", 1)
        if version_candidate in VERSION_DIRS:
            return version_candidate, name
        raise ValueError(f"Unknown task version '{version_candidate}' in '{reference}'")

    return DEFAULT_VERSION, reference


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
        return asdict(self)


@dataclass
class Task:
    id: str
    version: str
    evals: List[Eval]
    start_url: str
    goal: str
    difficulty: str
    challengeType: str
    points: float
    config: Optional[Dict[str, Any]] = None
    possible: bool = True
    description: str = ""

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)


class TaskConfig:
    """
    Load a task configuration by name and version.
    """

    def __init__(
        self,
        task_name: str,
        version: Optional[str] = None,
        *,
        is_path: bool = False,
    ) -> None:
        self.version = DEFAULT_VERSION
        self.task_name = ""
        self.base_dir = ""
        self.tasks_dir = ""
        self.eval_scripts_dir = ""
        self.canonical_id = ""
        self.config_json: Dict[str, Any] = {}

        if is_path:
            abs_path = os.path.abspath(task_name)
            if not abs_path.endswith(".json"):
                raise ValueError("Task paths must point to a JSON file.")
            self.config_json = self.from_json_file(abs_path)
            self.task_name = os.path.splitext(os.path.basename(abs_path))[0]
            rel_parts = os.path.relpath(abs_path, CURRENT_DIR).split(os.sep)
            inferred_version = rel_parts[0] if rel_parts else DEFAULT_VERSION
            if version is not None:
                inferred_version = version
            self._set_version_paths(inferred_version)
        else:
            resolved_version, resolved_name = (
                (version, task_name) if version is not None else split_task_reference(task_name)
            )
            self._set_version_paths(resolved_version)
            self.task_name = resolved_name
            config_path = os.path.join(self.tasks_dir, f"{self.task_name}.json")
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"Task configuration file not found: {config_path}")
            self.config_json = self.from_json_file(config_path)

        self.config_json.setdefault("version", self.version)
        if self.config_json.get("id") != self.task_name:
            self.config_json["id"] = self.task_name

        self.canonical_id = f"{self.version}.{self.task_name}"
        self.id = self.canonical_id

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

        start_url = self.config_json["website"]["url"]

        trimmed_config = self.config_json.copy()
        trimmed_config.pop("evals")
        trimmed_config.pop("website")
        trimmed_config.setdefault("config", {})

        self.task = Task(
            evals=eval_instances,
            start_url=start_url,
            **trimmed_config,
        )

    def _set_version_paths(self, version: str) -> None:
        if version not in VERSION_DIRS:
            raise ValueError(f"Unknown task version '{version}'")
        self.version = version
        self.base_dir = VERSION_DIRS[version]
        self.tasks_dir = os.path.join(self.base_dir, "tasks")
        self.eval_scripts_dir = os.path.join(self.base_dir, "eval_scripts")

    def from_json_file(self, file_path: str) -> Dict[str, Any]:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def to_json(self) -> Dict[str, Any]:
        return self.task.to_json()

    def get_task_id(self) -> str:
        return self.task.id

    def get_start_url(self) -> str:
        return self.task.start_url

    def get_goal(self) -> str:
        return self.task.goal

    def get_evals(self) -> list[Eval]:
        return self.task.evals

    def is_task_url_reachable(self) -> bool:
        try:
            response = requests.get(self.get_start_url(), timeout=5000)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def is_valid_config(self) -> bool:
        required_keys = ["id", "website", "goal", "evals"]
        for key in required_keys:
            if key not in self.config_json:
                return False
        return True

    def get_evaluation_type(self) -> str:
        return self.task.challengeType

    def get_reference_answer(self) -> str:
        if not self.task.evals:
            return ""
        return getattr(self.task.evals[0], "reference_answer", "")

    def get_expected_value(self) -> str:
        if not self.task.evals:
            return ""
        return getattr(self.task.evals[0], "expected_value", "")
