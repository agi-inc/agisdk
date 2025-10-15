"""
This module provides functionality to load and manage task configurations.
"""

import json
from typing import List, Dict, Any
import requests
import os

from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.join(CURRENT_DIR, "tasks")
TASKS = [task.split(".")[0] for task in os.listdir(TASK_DIR)]

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
        # Check if the input is a file path or an ID
        if os.path.exists(input_source) and input_source.endswith('.json'):
            # It's a file path
            self.config_json = self.from_json_file(input_source)
            self.id = self.config_json.get('id', '')
        else:
            # It's an ID
            self.id = input_source
            self.config_json = self.load_from_id(self.id)
        
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
    
    def load_from_id(self, id: str) -> Dict[str, Any]:
        """
        Load the task configuration from a JSON file given a task ID.
        :param id: The id of the task.
        :return: The task configuration as a dictionary.
        """
        path = os.path.join(TASK_DIR, f"{id}.json")
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
        

    
