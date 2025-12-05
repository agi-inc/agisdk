__version__ = "0.8.0"

import importlib.resources
import os
from pathlib import Path

import playwright.sync_api

# we use a global playwright instance
_PLAYWRIGHT = None


def _set_global_playwright(pw: playwright.sync_api.Playwright):
    global _PLAYWRIGHT
    _PLAYWRIGHT = pw


def _get_global_playwright():
    global _PLAYWRIGHT
    if not _PLAYWRIGHT:
        pw = playwright.sync_api.sync_playwright().start()
        _set_global_playwright(pw)

    return _PLAYWRIGHT


# Define chat_files directory to avoid circular import
# This needs to happen BEFORE any modules that import chat_files
current_dir = os.path.dirname(os.path.abspath(__file__))
chat_files = os.path.join(current_dir, "chat_files")

# Now we can safely import modules that might use chat_files
from .registration import register_task
from .task import OpenEndedTask

register_task(OpenEndedTask.get_task_id(), OpenEndedTask)
