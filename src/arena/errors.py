"""
Arena exception hierarchy for distinguishing error sources and handling.

AgentError subclasses are recoverable (log to state, continue execution).
All other exceptions are fatal (bubble up to run harness).
"""


class ArenaError(Exception):
    """Base class for all Arena-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message)
        # Automatically assign any keyword arguments as attributes
        # This allows rich error context without custom subclasses
        for key, value in kwargs.items():
            setattr(self, key, value)


class AgentError(ArenaError):
    """Agent implementation issues"""
