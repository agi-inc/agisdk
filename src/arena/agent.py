from abc import ABC, abstractmethod

from arena.state import AgentState
from arena.browser import AgentBrowser


class BaseAgent(ABC):
    @abstractmethod
    def step(self, browser: AgentBrowser, state: AgentState) -> AgentState: ...
