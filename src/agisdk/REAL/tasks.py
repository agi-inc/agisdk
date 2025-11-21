import json
from pathlib import Path

from agisdk.REAL.browsergym.webclones.task_config import (
    DEFAULT_VERSION,
    VERSION_DIRS,
)

# Default to the canonical version directory.
tasks_dir = Path(VERSION_DIRS[DEFAULT_VERSION]) / "tasks"

all_tasks = []
for file_path in tasks_dir.glob("*.json"):
    with file_path.open("r", encoding="utf-8") as handle:
        task = json.load(handle)
    task["_filename"] = file_path.name
    all_tasks.append(task)


def load_experimental_tasks():
    experimental_file = tasks_dir / "experimental" / "llm-generated.json"
    if experimental_file.exists():
        with experimental_file.open("r", encoding="utf-8") as handle:
            tasks = json.load(handle)
        for task in tasks:
            task["_filename"] = "experimental/llm-generated.json"
        return tasks
    return []


experimental_tasks = load_experimental_tasks()
all_including_experimental = all_tasks + experimental_tasks
