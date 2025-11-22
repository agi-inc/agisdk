import sys
import traceback
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from rich import print

from arena.image import Base64Image
from arena.errors import ArenaError


@dataclass
class AgentState:
    """
    Represents the current state of an agent during task execution.
    Automatically persists to database when save() is called.

    This class encapsulates all information about an agent's progress through a task,
    including execution metadata, goals, and visual history via screenshots.
    States are saved to the database as complete snapshots for each step.

    Note: You can freely assign additional attributes to this class as needed
    for your specific agent implementation. Keep attributes serializable
    (strings, numbers, lists, dicts) for easy persistence and debugging.
    """

    finished: bool = False
    goal: Optional[str] = None
    url: Optional[str] = None
    step: int = 0
    messages: List[Dict[str, Any]] = field(default_factory=list)
    task_execution_id: Optional[int] = None
    error: Optional[Dict[str, Any]] = None
    error_count: int = 0
    images: List[Base64Image] = field(default_factory=list)

    def register_error(self, exception: ArenaError) -> None:
        """Register an error for this step"""
        exc_type, exc_value, exc_tb = sys.exc_info()
        traceback_lines = traceback.format_exception(exc_type, exc_value, exc_tb)

        self.error = {
            "type": type(exception).__name__,
            "message": str(exception),
            "traceback": traceback_lines,
            **vars(exception),  # Capture any custom attributes from agent's error class
        }
        self.error_count += 1
        print("ArenaError encountered, registering for next step.", str(exception))

    def __getattr__(self, name: str) -> None:
        return None

    def __rich_repr__(self):
        # Make sure rich sees values assigned to this object other than those
        # specified in the dataclass, e.g. state.random = "Hello!"
        for key, value in vars(self).items():
            if not key.startswith("_"):
                yield key, value
