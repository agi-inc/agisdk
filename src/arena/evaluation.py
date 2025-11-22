import json
import importlib.util
import sys
from pathlib import Path
import importlib.resources
from typing import Optional, Tuple, TYPE_CHECKING
from abc import ABC, abstractmethod
from arena.result import ExperimentResult

if TYPE_CHECKING:
    from arena.browser import AgentBrowser
    from arena.state import AgentState


class BaseEvaluator(ABC):
    """Base class for all task evaluators."""

    def __init__(self, browser: "AgentBrowser", task_dict: dict, task_path: str = None):
        """
        Initialize evaluator.

        Args:
            browser: Browser instance
            task_dict: Task configuration dictionary
            task_path: Path to task JSON file (optional)
        """
        self.browser = browser
        self.task_dict = task_dict
        self.task_path = task_path

    @abstractmethod
    async def setup(self) -> Tuple[str, str]:
        """
        Setup the task and return goal and URL.

        Returns:
            Tuple of (goal, url)
        """
        pass

    @abstractmethod
    async def evaluate(self, state: "AgentState") -> "ExperimentResult":
        """Evaluate the agent's performance on the task."""
        pass


class Evaluation:
    @staticmethod
    def get_evaluator(task_dict: dict, task_json_path: str) -> type:
        # Search upward from task path to find evaluator.py
        task_path = Path(task_json_path)
        benchmark_dir = Evaluation._find_benchmark_dir(task_path)
        benchmark_name = benchmark_dir.name

        # First try relative to current working directory (local clone)
        if benchmark_dir.exists() and (benchmark_dir / "evaluator.py").exists():
            evaluator_module = Evaluation._load_benchmark_evaluator(
                benchmark_dir, benchmark_name
            )
        else:
            # Try installed package location (pip installed / site-packages)
            with importlib.resources.files("benchmarks") as benchmarks_pkg:
                benchmark_dir = benchmarks_pkg / benchmark_name
                if (
                    not benchmark_dir.is_dir()
                    or not (benchmark_dir / "evaluator.py").is_file()
                ):
                    raise ValueError(
                        f"No evaluator found for benchmark: {benchmark_name}"
                    )
                evaluator_module = Evaluation._load_benchmark_evaluator(
                    benchmark_dir, benchmark_name
                )

        # Find evaluator class in the module that inherits from BaseEvaluator
        for attr_name in dir(evaluator_module):
            attr = getattr(evaluator_module, attr_name)
            if (
                isinstance(attr, type)
                and attr_name.endswith("Evaluator")
                and attr != BaseEvaluator
                and issubclass(attr, BaseEvaluator)
            ):
                return attr

        raise ValueError(f"No evaluator class found in benchmark: {benchmark_name}")

    @staticmethod
    def _find_benchmark_dir(task_path: Path) -> Path:
        """
        Search upward from task JSON path to find directory containing evaluator.py.

        Args:
            task_path: Path to the task JSON file

        Returns:
            Path to the benchmark directory containing evaluator.py

        Raises:
            ValueError: If no evaluator.py found in any parent directory
        """
        current_dir = task_path.parent

        # Search upward until we find evaluator.py or hit the root
        while current_dir != current_dir.parent:  # Not at filesystem root
            if (current_dir / "evaluator.py").exists():
                return current_dir
            current_dir = current_dir.parent

        # If we get here, no evaluator.py was found
        raise ValueError(
            f"No evaluator.py found in any parent directory of {task_path}"
        )

    @staticmethod
    def _load_benchmark_evaluator(benchmark_dir: Path, benchmark_name: str):
        package_name = f"benchmark_{benchmark_name}"

        # Create the package if it doesn't exist
        if package_name not in sys.modules:
            # Create package spec
            package_spec = importlib.util.spec_from_loader(
                package_name, loader=None, origin=str(benchmark_dir)
            )
            package_spec.submodule_search_locations = [str(benchmark_dir)]

            # Create and register package
            package = importlib.util.module_from_spec(package_spec)
            sys.modules[package_name] = package

        # Load evaluator module as part of the package
        evaluator_spec = importlib.util.spec_from_file_location(
            f"{package_name}.evaluator", benchmark_dir / "evaluator.py"
        )
        evaluator_module = importlib.util.module_from_spec(evaluator_spec)
        sys.modules[f"{package_name}.evaluator"] = evaluator_module

        # Load other Python modules in the benchmark directory for relative imports
        for py_file in benchmark_dir.glob("*.py"):
            if py_file.name not in ["__init__.py", "evaluator.py"]:
                module_name = py_file.stem
                module_spec = importlib.util.spec_from_file_location(
                    f"{package_name}.{module_name}", py_file
                )
                if module_spec:
                    module = importlib.util.module_from_spec(module_spec)
                    sys.modules[f"{package_name}.{module_name}"] = module
                    module_spec.loader.exec_module(module)

        # Execute the evaluator module last so relative imports work
        evaluator_spec.loader.exec_module(evaluator_module)

        return evaluator_module

    @staticmethod
    async def setup_evaluator(
        browser: "AgentBrowser", task_json_path: Optional[str]
    ) -> Optional[Tuple[object, str, str]]:
        if not task_json_path:
            return None

        with open(task_json_path, "r") as f:
            task_dict = json.load(f)

        evaluator_class = Evaluation.get_evaluator(task_dict, task_json_path)
        evaluator = evaluator_class(browser, task_dict, task_json_path)

        goal, url = await evaluator.setup()

        return evaluator, goal, url
