import os
import time
from typing import Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeRemainingColumn,
    )
    from rich.syntax import Syntax
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Global console instance with forced color support
console = Console(force_terminal=True, color_system="truecolor") if RICH_AVAILABLE else None


# Enhanced color scheme constants
class Colors:
    SUCCESS = "bold green"
    ERROR = "bold red"
    INFO = "bold blue"
    WARNING = "bold yellow"
    HEADER = "bold cyan"
    VALUE = "bold magenta"
    SECONDARY = "dim white"
    ACCENT = "bright_white"
    TASK = "bold purple"
    STEP = "bold bright_cyan"


class RichLogger:
    """Rich-based logger that provides structured console output."""

    def __init__(self, enabled: bool = None):
        """Initialize the Rich logger.

        Args:
            enabled: Whether to use Rich logging. If None, auto-detect based on Rich availability.
        """
        if enabled is None:
            enabled = RICH_AVAILABLE and not os.getenv("DISABLE_RICH_LOGGING", "").lower() == "true"

        self.enabled = enabled and RICH_AVAILABLE
        self.console = (
            Console(force_terminal=True, color_system="truecolor") if self.enabled else None
        )
        self._current_progress = None
        self._progress_task = None

    def print(self, message: str, style: str = None, **kwargs):
        """Print a message with optional styling.

        Args:
            message: The message to print
            style: Rich style string (e.g., "green", "bold red")
            **kwargs: Additional arguments passed to console.print
        """
        if self.enabled and self.console:
            self.console.print(message, style=style, **kwargs)
        else:
            # Fallback to standard print, stripping Rich markup
            clean_message = self._strip_rich_markup(message)
            print(clean_message, **kwargs)

    def success(self, message: str):
        """Print a success message."""
        self.print(f"[{Colors.SUCCESS}]✅ {message}[/{Colors.SUCCESS}]")

    def error(self, message: str):
        """Print an error message."""
        self.print(f"[{Colors.ERROR}]❌ {message}[/{Colors.ERROR}]")

    def info(self, message: str):
        """Print an info message."""
        self.print(f"[{Colors.INFO}] {message}[/{Colors.INFO}]")

    def warning(self, message: str):
        """Print a warning message."""
        self.print(f"[{Colors.WARNING}] {message}[/{Colors.WARNING}]")

    def header(self, message: str):
        """Print a header message."""
        self.print(f"[{Colors.HEADER}]📋 {message}[/{Colors.HEADER}]")

    def task_start(self, task_name: str, model: str = None):
        """Print a beautifully formatted task start message."""
        self.print(
            f"[{Colors.SECONDARY}]─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ──[/{Colors.SECONDARY}]"
        )
        content = f"[{Colors.TASK}]🚀 Starting New Task - 🎯 Task:[/{Colors.TASK}] [{Colors.VALUE}]{task_name}[/{Colors.VALUE}]"
        if model:
            content += f" [{Colors.INFO}]🤖 Model:[/{Colors.INFO}] [{Colors.VALUE}]{model}[/{Colors.VALUE}]"
        self.print(content)
        self.print(
            f"[{Colors.SECONDARY}]─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ──[/{Colors.SECONDARY}]"
        )

    def task_step(self, step_num: int, action: str, details: str = None):
        """Print a formatted task step."""
        content = f"[{Colors.STEP}]Step {step_num}:[/{Colors.STEP}] [cyan]{action}[/cyan]"
        if details:
            content += f"\n[{Colors.SECONDARY}]{details}[/{Colors.SECONDARY}]"
        self.print(content)

    def task_complete(
        self,
        success: bool,
        reward: float = None,
        time_taken: float = None,
        task_id: str = None,
    ):
        """Print a task completion message."""
        self.print(
            f"[{Colors.SECONDARY}]─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ──[/{Colors.SECONDARY}]"
        )
        if success:
            status = f"[{Colors.SUCCESS}]📊 Task Results - ✅ Task Completed Successfully![/{Colors.SUCCESS}]"
        else:
            status = f"[{Colors.ERROR}]📊 Task Results - ❌ Task Failed[/{Colors.ERROR}]"

        content = status
        if task_id:
            content += f" [{Colors.INFO}]🆔 Task ID:[/{Colors.INFO}] [{Colors.VALUE}]{task_id}[/{Colors.VALUE}]"
        if reward is not None:
            content += f" [{Colors.INFO}]💰 Reward:[/{Colors.INFO}] [{Colors.VALUE}]{reward}[/{Colors.VALUE}]"
        if time_taken is not None:
            content += f" [{Colors.INFO}]⏱️ Time:[/{Colors.INFO}] [{Colors.VALUE}]{time_taken:.2f}s[/{Colors.VALUE}]"

        self.print(content)
        self.print(
            f"[{Colors.SECONDARY}]─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ─── ──[/{Colors.SECONDARY}]"
        )

    def panel(self, content: str, title: str = None, border_style: str = "blue"):
        """Print content in a panel.

        Args:
            content: The content to display
            title: Optional panel title
            border_style: Border color style
        """
        if self.enabled and self.console:
            panel = Panel(content, title=title, border_style=border_style)
            self.console.print(panel)
        else:
            # Fallback display
            title_line = f"=== {title} ===" if title else "============"
            print(title_line)
            print(content)
            print("=" * len(title_line))

    def table(self, data: list[dict[str, Any]], title: str = None) -> None:
        """Print data in a formatted table.

        Args:
            data: List of dictionaries representing table rows
            title: Optional table title
        """
        if not data:
            return

        if self.enabled and self.console:
            table = Table(title=title)

            # Add columns based on first row keys
            for key in data[0].keys():
                table.add_column(key, style=Colors.VALUE)

            # Add rows
            for row in data:
                table.add_row(*[str(value) for value in row.values()])

            self.console.print(table)
        else:
            # Fallback table display
            if title:
                print(f"\n{title}")
                print("-" * len(title))

            if data:
                headers = list(data[0].keys())
                print(" | ".join(headers))
                print("-" * (len(" | ".join(headers))))

                for row in data:
                    print(" | ".join(str(row[key]) for key in headers))
            print()

    def progress_bar(self, description: str = "Processing..."):
        """Create a progress bar context manager.

        Args:
            description: Description text for the progress bar

        Returns:
            Context manager for progress tracking
        """
        if self.enabled and self.console:
            return RichProgressBar(description, self.console)
        else:
            return FallbackProgressBar(description)

    def status_panel(self, title: str, content: dict[str, Any]):
        """Display a status panel with key-value pairs.

        Args:
            title: Panel title
            content: Dictionary of status information
        """
        status_lines = []
        for key, value in content.items():
            status_lines.append(
                f"[{Colors.HEADER}]{key}:[/{Colors.HEADER}] [{Colors.VALUE}]{value}[/{Colors.VALUE}]"
            )

        status_content = "\n".join(status_lines)
        self.panel(status_content, title=title, border_style=Colors.SUCCESS)

    def code_block(self, code: str, language: str = "python", theme: str = "monokai"):
        """Display a syntax-highlighted code block.

        Args:
            code: The code to display
            language: Programming language for syntax highlighting
            theme: Color theme for syntax highlighting
        """
        if self.enabled and self.console:
            syntax = Syntax(code, language, theme=theme)
            self.console.print(syntax)
        else:
            print(f"```{language}")
            print(code)
            print("```")

    def _strip_rich_markup(self, text: str) -> str:
        """Remove Rich markup from text for fallback display."""
        import re

        # Remove Rich markup tags like [green], [/green], [bold red], etc.
        clean_text = re.sub(r"\[[^\]]*\]", "", text)
        return clean_text


class RichProgressBar:
    """Rich progress bar context manager."""

    def __init__(self, description: str, console):
        self.description = description
        self.console = console
        self.progress = None
        self.task_id = None
        self.total = None

    def __enter__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console,
        )
        self.progress.start()
        self.task_id = self.progress.add_task(self.description, total=None)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.progress:
            self.progress.stop()

    def set_total(self, total: int):
        """Set the total number of items to process."""
        self.total = total
        if self.progress and self.task_id:
            self.progress.update(self.task_id, total=total)

    def advance(self, amount: int = 1):
        """Advance the progress bar."""
        if self.progress and self.task_id:
            self.progress.advance(self.task_id, amount)

    def update(self, completed: int, description: str = None):
        """Update progress with absolute completion count."""
        if self.progress and self.task_id:
            kwargs = {"completed": completed}
            if description:
                kwargs["description"] = description
            self.progress.update(self.task_id, **kwargs)


class FallbackProgressBar:
    """Fallback progress bar for when Rich is not available."""

    def __init__(self, description: str):
        self.description = description
        self.completed = 0
        self.total = None
        self.last_update = time.time()

    def __enter__(self):
        print(f"Starting: {self.description}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.total:
            print(f"Completed: {self.description} ({self.completed}/{self.total})")
        else:
            print(f"Completed: {self.description}")

    def set_total(self, total: int):
        """Set the total number of items to process."""
        self.total = total

    def advance(self, amount: int = 1):
        """Advance the progress bar."""
        self.completed += amount
        current_time = time.time()

        # Update every 2 seconds or at completion
        if current_time - self.last_update > 2.0 or (self.total and self.completed >= self.total):
            if self.total:
                percentage = (self.completed / self.total) * 100
                print(f"Progress: {self.completed}/{self.total} ({percentage:.1f}%)")
            else:
                print(f"Progress: {self.completed} items completed")
            self.last_update = current_time

    def update(self, completed: int, description: str = None):
        """Update progress with absolute completion count."""
        self.completed = completed
        if description:
            print(f"Status: {description}")


# Global logger instance
logger = RichLogger()


# Convenience functions for backwards compatibility
def console_print(*args, **kwargs):
    """Print to console with Rich formatting if available."""
    if logger.enabled:
        logger.print(*args, **kwargs)
    else:
        print(*args, **kwargs)


def create_progress_bar(description: str = "Processing..."):
    """Create a progress bar context manager."""
    return logger.progress_bar(description)


def create_results_table(data: list[dict[str, Any]], title: str = None):
    """Create and display a results table."""
    logger.table(data, title)


def create_status_panel(title: str, content: dict[str, Any]):
    """Create and display a status panel."""
    logger.status_panel(title, content)


# Export main components
__all__ = [
    "logger",
    "console_print",
    "create_progress_bar",
    "create_results_table",
    "create_status_panel",
    "RichLogger",
    "Colors",
]
