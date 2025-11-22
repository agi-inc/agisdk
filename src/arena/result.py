from typing import Any
from dataclasses import dataclass


@dataclass
class ExperimentResult:
    """
    Represents the result of an experiment evaluation.

    Attributes:
        success (bool): Whether the experiment was successful overall
    """

    success: bool = False

    def __setattr__(self, name: str, value: Any) -> None:
        """Allow setting arbitrary attributes"""
        super().__setattr__(name, value)

    def __repr__(self) -> str:
        """Show all set attributes with just keys for large values"""
        attrs = []
        for key, value in vars(self).items():
            if not key.startswith("_"):
                if isinstance(value, (str, int, float, bool, type(None))):
                    attrs.append(f"{key}={value!r}")
                else:
                    attrs.append(f"{key}=<{type(value).__name__}>")
        return f"ExperimentResult({', '.join(attrs)})"

    def __rich_repr__(self):
        """Make sure rich sees all values assigned to this object"""
        for key, value in vars(self).items():
            if not key.startswith("_"):
                yield key, value
