import warnings

import gymnasium as gym

from agisdk.REAL.logging import logger as rich_logger

from .env import BrowserEnv
from .task import AbstractBrowserTask


def register_task(
    id: str,
    task_class: type[AbstractBrowserTask],
    task_kwargs: dict = None,
    nondeterministic: bool = True,
    *args,
    **kwargs,
):
    # these environment arguments will be fixed, and error will be raised if they are set when calling gym.make()
    fixed_env_kwargs = {}
    if task_kwargs is not None:
        fixed_env_kwargs["task_kwargs"] = task_kwargs

    env_id = f"browsergym/{id}"

    # Check if environment is already registered to avoid warnings
    try:
        # Capture warnings during registration
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            gym.register(
                id=env_id,
                entry_point=lambda *env_args, **env_kwargs: BrowserEnv(
                    task_class, *env_args, **fixed_env_kwargs, **env_kwargs
                ),
                nondeterministic=nondeterministic,
                *args,
                **kwargs,
            )

            # Log any warnings using Rich logger
            for warning in w:
                if "Overriding environment" in str(warning.message):
                    rich_logger.warning(f"🔄 {warning.message}")

    except gym.error.Error:
        # Environment already registered, skip silently
        pass
