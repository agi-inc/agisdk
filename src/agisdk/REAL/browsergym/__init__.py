from . import core, utils, webclones
from .core.action.base import AbstractActionSet
from .core.action.highlevel import HighLevelActionSet
from .core.action.python import PythonActionSet
from .experiments.agent import Agent, AgentInfo
from .experiments.loop import (
    AbstractAgentArgs,
    EnvArgs,
    ExpArgs,
    ExpResult,
    StepInfo,
    StepTimestamps,
)


def hello(name="World"):
    """A real greeting function for the browsergym real submodule."""
    message = f"Hello {name}, from the browsergym real world!"
    print(message)
    return message
