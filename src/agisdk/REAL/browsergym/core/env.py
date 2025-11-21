import copy
import json
import logging
import os
import re
import tempfile
import time
from abc import ABC
from pathlib import Path
from typing import Literal, Optional, Union

import gymnasium as gym
import numpy as np
import playwright.sync_api

from . import _get_global_playwright
from .action.base import execute_python_code
from .action.highlevel import HighLevelActionSet
from .action.openai_cua import execute_openai_cua_action
from .chat import Chat
from .constants import BROWSERGYM_ID_ATTRIBUTE, EXTRACT_OBS_MAX_TRIES, TEXT_MAX_LENGTH
from .observation import (
    MarkingError,
    _post_extract,
    _pre_extract,
    extract_dom_extra_properties,
    extract_dom_snapshot,
    extract_focused_element_bid,
    extract_merged_axtree,
    extract_screenshot,
)
from .spaces import AnyBox, AnyDict, Unicode
from .task import AbstractBrowserTask

logger = logging.getLogger(__name__)


def _try_to_extract_legacy_goal(goal: list):
    legacy_goal_strings = []
    for message in goal:
        if message["type"] == "text":
            legacy_goal_strings.append(message["text"])
        else:
            logger.debug(
                f"Message type {repr(message['type'])} present in the goal, cannot be converted to legacy text-only format."
            )
            legacy_goal_strings.append(
                'WARNING: This goal cannot be converted to a text-only goal format. Use the new goal format instead ("goal_object" field). Any agent reading this should abort immediately.'
            )
            break
    legacy_goal = "\n".join(legacy_goal_strings)

    return legacy_goal


class BrowserEnv(gym.Env, ABC):
    """The main BrowserGym class, which encapsulates instruction-following Web browsing into a Gymnasium environment."""

    # gym metadata
    metadata = {"render_modes": None}

    def __init__(
        self,
        # task-related arguments
        task_entrypoint: type[AbstractBrowserTask],
        task_kwargs: dict = None,
        viewport: Optional[dict] = None,  # will override the task's viewport
        slow_mo: Optional[int] = None,  # will override the task's slow_mo
        timeout: Optional[int] = None,  # will override the task's timeout
        tags_to_mark: Literal["all", "standard_html"] = "standard_html",
        # interactive / debugging arguments
        headless: bool = True,
        wait_for_user_message: bool = False,
        terminate_on_infeasible: bool = True,
        resizeable_window: bool = False,
        record_video_dir: Optional[str] = None,
        pw_chromium_kwargs: dict = None,
        pw_context_kwargs: dict = None,
        golden_user_data_dir: Optional[str] = None,
        extensions_dir: Optional[str] = None,
        # agent-related arguments
        action_mapping: Optional[callable] = HighLevelActionSet().to_python_code,
    ):
        """
        Instantiate a ready to use BrowserEnv gym environment.

        Args:
            task_entrypoint: a callable that returns a new task object from a seed. Used for creating a new task during `reset()`.
            task_kwargs: additional arguments passed to `task_entrypoint`.
            viewport: desired viewport size. This will override the value defined by the task, which might change its behaviour and difficulty. Should only be set for debugging/testing.
            slow_mo: desired slow_mo value for Playwright. This will override the value defined by the task, which might change its behaviour and difficulty. Should only be set for debugging/testing.
            timeout: desired timeout value for Playwright. This will override the value defined by the task, which might change its behaviour and difficulty. Should only be set for debugging/testing.
            tags_to_mark: which HTML tags should be marked by BrowserGym and receive a bid. Value "all" will mark every element in the page, while "standard_html" (default) will only mark standard html tags.
            headless: whether the browser should run in headless mode or not. This will affect the viewport size, which might change the behaviour and difficulty of the task. Headless mode should only be disabled for debugging/testing.
            wait_for_user_message: whether the environment should pause and wait for a user message in the chat after a new message is sent by the agent. Useful for running agents in interactive mode.
            resizeable_window: whether the browser window should be resizeable or not. This will affect the viewport size, which might change the behaviour and difficulty of the task. Should only be set for debugging/testing.
            record_video_dir: if set, indicates a directory to which viewport videos will be recorded.
            pw_chromium_kwargs: extra parameters for the playwright Browser. Should only be used for debugging/testing.
            pw_context_kwargs: extra parameters for the playwright BrowserContext. Should only be used for debugging/testing.
            action_mapping: if set, the environment will use this function to map every received action to executable Python code.
            golden_user_data_dir: desired user data directory for persistent browser context. If provided, a copy of this directory will be used for the browser session. This allows reusing a pre-configured browser state (cookies, localStorage, etc).
            extensions_dir: directory containing Chrome extensions to load (can be a single extension directory or a directory of extensions). Requires persistent context and disables headless mode.

        """
        if pw_context_kwargs is None:
            pw_context_kwargs = {}
        if pw_chromium_kwargs is None:
            pw_chromium_kwargs = {}
        if task_kwargs is None:
            task_kwargs = {}
        super().__init__()
        self.task_entrypoint = task_entrypoint
        self.task_kwargs = dict(**task_kwargs)
        self.viewport = viewport
        self.slow_mo = slow_mo
        self.timeout = timeout
        self.tags_to_mark = tags_to_mark
        self.headless = headless
        self.wait_for_user_message = wait_for_user_message
        self.terminate_on_infeasible = terminate_on_infeasible
        self.resizeable_window = resizeable_window
        self.record_video_dir = record_video_dir
        self.pw_chromium_kwargs = pw_chromium_kwargs
        self.pw_context_kwargs = pw_context_kwargs
        self.golden_user_data_dir = golden_user_data_dir
        self.extensions_dir = extensions_dir
        self._temp_user_data_dir = None
        self.action_mapping = action_mapping
        self.active_agent_name = None  # Add attribute to store agent name

        # check argument values
        assert tags_to_mark in ("all", "standard_html")

        # task
        self.task = None

        # playwright
        self.browser: playwright.sync_api.Browser = None
        self.context: playwright.sync_api.BrowserContext = None
        self.page: playwright.sync_api.Page = None
        self.page_history: dict = {}

        # chat
        self.chat: Chat = None

        # observation space
        self.observation_space = gym.spaces.Dict(
            {
                "chat_messages": gym.spaces.Sequence(
                    gym.spaces.Dict(
                        {
                            "role": Unicode(min_length=0, max_length=TEXT_MAX_LENGTH),
                            "message": Unicode(min_length=0, max_length=TEXT_MAX_LENGTH),
                        }
                    )
                ),
                "goal": Unicode(min_length=0, max_length=TEXT_MAX_LENGTH),
                "goal_object": gym.spaces.Sequence(AnyDict()),
                "task_id": Unicode(min_length=0, max_length=TEXT_MAX_LENGTH),
                "open_pages_urls": gym.spaces.Sequence(
                    Unicode(min_length=0, max_length=TEXT_MAX_LENGTH)
                ),
                "active_page_index": gym.spaces.Box(low=0, high=255, dtype=int),
                "url": Unicode(min_length=0, max_length=TEXT_MAX_LENGTH),
                "screenshot": AnyBox(
                    low=0,
                    high=255,
                    shape=(-1, -1, 3),
                    dtype=np.uint8,
                ),  # swapped axes (height, width, RGB)
                "dom_object": AnyDict(),
                "axtree_object": AnyDict(),
                "extra_element_properties": AnyDict(),
                "focused_element_bid": Unicode(min_length=0, max_length=TEXT_MAX_LENGTH),
                "last_action": Unicode(min_length=0, max_length=TEXT_MAX_LENGTH),
                "last_action_error": Unicode(min_length=0, max_length=TEXT_MAX_LENGTH),
                "elapsed_time": gym.spaces.Box(low=0, high=np.inf, dtype=float),
                "browser": AnyDict(),  # Placeholder for browser object
            }
        )

        # action space
        self.action_space = Unicode(min_length=0, max_length=TEXT_MAX_LENGTH)

    def close(self):
        if self.task:
            # stop the task
            self.task.teardown()
            # close the chat
            self.chat.close()
            # close the browser context
            self.context.close()
            # close the browser
            self.browser.close()
            self.task = None

            # Clean up temporary directory if we created one
            if self._temp_user_data_dir:
                import shutil

                logger.info(
                    f"Cleaning up temporary user data directory: {self._temp_user_data_dir}"
                )
                shutil.rmtree(self._temp_user_data_dir, ignore_errors=True)
                self._temp_user_data_dir = None

    def reset(self, seed=None, *args, **kwargs):
        super().reset(seed=seed, *args, **kwargs)
        self.np_random = None  # make sure all randomness is handled by the task

        if self.task:
            self.task.teardown()
            self.context.close()
            self.chat.close()
            self.browser.close()

        # create a new task
        self.task = self.task_entrypoint(seed=seed, **self.task_kwargs)

        def override_property(task, env, property):
            """Extract property value from env if not None, otherwise from task."""
            env_value = getattr(env, property)
            task_value = getattr(task, property)
            if env_value is None:
                return task_value
            else:
                logger.warning(
                    f"Overriding the task's {property} parameter ({repr(task_value)} => {repr(env_value)}). This might change the task's behaviour and difficulty."
                )
                return env_value

        # fetch task's desired parameters for browser setup
        viewport = override_property(self.task, self, "viewport")
        slow_mo = override_property(self.task, self, "slow_mo")
        timeout = override_property(self.task, self, "timeout")

        # use the global Playwright instance
        pw: playwright.sync_api.Playwright = _get_global_playwright()
        # important: change playwright's test id attribute from "data-testid" to "bid"
        pw.selectors.set_test_id_attribute(BROWSERGYM_ID_ATTRIBUTE)

        # Prepare common args
        args = []
        if self.resizeable_window:
            args.append(f"--window-size={viewport['width']},{viewport['height']}")

        # Add extension arguments if needed
        if self.extensions_dir:
            # Extensions require non-headless mode
            assert not self.headless, "Extensions cannot be used in headless mode."

            # Get absolute path to extensions directory
            extensions_dir = os.path.abspath(self.extensions_dir)

            # Look for extensions directories (containing manifest.json)
            extensions_paths = []

            # First check if the directory itself is an extension (has manifest.json)
            if os.path.isfile(os.path.join(extensions_dir, "manifest.json")):
                extensions_paths.append(extensions_dir)
            else:
                # Otherwise, look for subdirectories containing manifest.json
                for item in os.listdir(extensions_dir):
                    item_path = os.path.join(extensions_dir, item)
                    if os.path.isdir(item_path) and os.path.isfile(
                        os.path.join(item_path, "manifest.json")
                    ):
                        extensions_paths.append(item_path)

            if not extensions_paths:
                logger.warning(f"No valid Chrome extensions found in {extensions_dir}")
            else:
                logger.info(f"Found {len(extensions_paths)} Chrome extensions to load")
                extensions_str = ",".join(extensions_paths)
                args.append(f"--disable-extensions-except={extensions_str}")
                args.append(f"--load-extension={extensions_str}")

            # Extensions require persistent context
            if not self.golden_user_data_dir:
                logger.warning(
                    "Extensions require persistent context. Creating a temporary user data directory."
                )
                self._temp_user_data_dir = tempfile.mkdtemp(prefix="browsergym_extensions_")

        args = None if not args else args

        # Setup temp directory for golden profile if needed
        if self.golden_user_data_dir:
            import shutil
            import tempfile

            self._temp_user_data_dir = tempfile.mkdtemp(prefix="browsergym_")
            logger.info(
                f"Copying golden profile from {self.golden_user_data_dir} to {self._temp_user_data_dir}"
            )
            shutil.copytree(self.golden_user_data_dir, self._temp_user_data_dir, dirs_exist_ok=True)

        # PERSISTENT CONTEXT PATH
        if self.golden_user_data_dir or self.extensions_dir:
            if self.extensions_dir:
                assert not self.headless, "Extensions cannot be used in headless mode."

            # Launch persistent context
            self.context = pw.chromium.launch_persistent_context(
                user_data_dir=self._temp_user_data_dir,
                headless=self.headless,
                slow_mo=slow_mo,
                args=args,
                viewport=viewport,
                record_video_dir=(
                    Path(self.record_video_dir) / "task_video" if self.record_video_dir else None
                ),
                record_video_size=viewport,
                **self.pw_context_kwargs,
            )
            # Get browser from context
            self.browser = self.context.browser

        # STANDARD PATH
        else:
            # Launch browser
            self.browser = pw.chromium.launch(
                headless=self.headless,
                slow_mo=slow_mo,
                args=args,
                **self.pw_chromium_kwargs,
            )

            # Create context
            self.context = self.browser.new_context(
                no_viewport=True if self.resizeable_window else None,
                viewport=viewport,
                record_video_dir=(
                    Path(self.record_video_dir) / "task_video" if self.record_video_dir else None
                ),
                record_video_size=viewport,
                **self.pw_context_kwargs,
            )

        # set default timeout
        self.context.set_default_timeout(timeout)

        # hack: keep track of the active page with a javascript callback
        # there is no concept of active page in playwright
        # https://github.com/microsoft/playwright/issues/2603
        self.context.expose_binding(
            "browsergym_page_activated",
            lambda source: self._activate_page_from_js(source["page"]),
        )

        self.context.add_init_script(
            r"""
window.browsergym_page_activated();
window.addEventListener("focus", () => {window.browsergym_page_activated();}, {capture: true});
window.addEventListener("focusin", () => {window.browsergym_page_activated();}, {capture: true});
window.addEventListener("load", () => {window.browsergym_page_activated();}, {capture: true});
window.addEventListener("pageshow", () => {window.browsergym_page_activated();}, {capture: true});
window.addEventListener("mousemove", () => {window.browsergym_page_activated();}, {capture: true});
window.addEventListener("mouseup", () => {window.browsergym_page_activated();}, {capture: true});
window.addEventListener("mousedown", () => {window.browsergym_page_activated();}, {capture: true});
window.addEventListener("wheel", () => {window.browsergym_page_activated();}, {capture: true});
window.addEventListener("keyup", () => {window.browsergym_page_activated();}, {capture: true});
window.addEventListener("keydown", () => {window.browsergym_page_activated();}, {capture: true});
window.addEventListener("input", () => {window.browsergym_page_activated();}, {capture: true});
window.addEventListener("touchstart", () => {window.browsergym_page_activated();}, {capture: true});
window.addEventListener("touchend", () => {window.browsergym_page_activated();}, {capture: true});
document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
        window.browsergym_page_activated();
    }
}, {capture: true});
"""
        )

        # create the chat
        self.chat = Chat(
            headless=self.headless,
            chat_size=(500, max(viewport["height"], 800)),
            record_video_dir=self.record_video_dir,
        )

        # create a new page
        self.page = self.context.new_page()
        recording_start_time = time.time()

        # setup the task
        task_goal, task_info = self.task.setup(page=self.page)

        # process the task goal

        # no goal specified
        if task_goal is None:
            self.goal_object = []
        # convert text-only goal (legacy) to new format
        elif isinstance(task_goal, str):
            self.goal_object = [{"type": "text", "text": task_goal}]
        # new format goal with multiple texts and images (OpenAI style)
        elif isinstance(task_goal, list):
            self.goal_object = task_goal
        else:
            raise ValueError(f"task_goal should be of type str or list, got {task_goal.__class__}")

        # initialize the chat
        self.chat.add_message(
            role="assistant",
            msg="Hi! I am your UI assistant, I can perform web tasks for you. What can I help you with?",
        )

        # send task goal (if any) to the chat
        for message in self.goal_object:
            match message["type"]:
                case "text":
                    self.chat.add_message(role="user", msg=message["text"])
                case "image_url":
                    image_src = message["image_url"]
                    if isinstance(image_src, dict):
                        image_src = image_src["url"]
                    self.chat.add_message(role="user_image", msg=image_src)
                case _:
                    raise ValueError(
                        f"Unknown message type {repr(message['type'])} in the task goal."
                    )

        self._wait_dom_loaded()

        # after the task's setup, the active page might have changed
        # perform a safety check
        self._active_page_check()

        # init start time
        self.start_time = time.time()

        # no action yet
        self.last_action = ""
        self.last_action_error = ""
        self.infeasible_message_received = False

        # if asked, wait for user message
        self._wait_for_user_message()

        # extract obs and info from environment
        obs = self._get_obs()

        info = {}
        info["task_info"] = task_info

        # TODO this is a bit hacky, find a better solution to record videos
        if self.record_video_dir:
            info["recording_start_time"] = recording_start_time
            info["recording_file"] = str(self.page.video.path())
            info["chat"] = {
                "recording_start_time": self.chat.recording_start_time,
                "recording_file": str(self.chat.page.video.path()),
            }

        return obs, info

    def step(self, action: Union[dict, str]) -> tuple:
        # Get agent_name from instance attribute
        agent_name = self.active_agent_name

        # Store a string representation for the observation and logging
        if isinstance(action, dict):
            try:
                # Convert dict action to a JSON string
                self.last_action = json.dumps(action)
            except TypeError:  # Handle potential non-serializable items if any
                self.last_action = str(action)  # Fallback to simple string conversion
        else:
            # Action is already a string
            self.last_action = action

        info = {}
        info["action_exec_start"] = time.time()
        info["action_exec_timeout"] = 0

        def send_message_to_user(text: str):
            self.chat.add_message(role="assistant", msg=text)

        def report_infeasible_instructions(reason: str):
            self.chat.add_message(role="infeasible", msg=reason)
            self.infeasible_message_received = True

        # Reset last action error at the start of the step
        self.last_action_error = ""
        action_executed = False  # Flag to track if a browser action was attempted
        agent_reported_error = False  # Flag if agent itself reported an error

        # try to execute the action
        # Use agent_name read from self.active_agent_name
        logger.debug(f"Executing action for agent '{agent_name}': {self.last_action}")

        try:
            if agent_name == "OperatorAgentArgs":
                if isinstance(action, dict):
                    # Check for special non-executable actions from the agent
                    action_type = action.get("type")
                    if action_type in ["no_op", "error"]:
                        logger.info(
                            f"Received non-executable action from agent: {self.last_action}"
                        )
                        if action_type == "error":
                            # Store the error message from the agent itself
                            self.last_action_error = action.get(
                                "message", "Agent reported an unspecified error"
                            )
                            agent_reported_error = True  # Mark that agent reported error
                        # Do not attempt to execute this in the browser
                        action_executed = False
                    else:
                        # Execute the CUA action dictionary
                        execute_openai_cua_action(
                            action,  # Pass the dict directly
                            self.page,
                            send_message_to_user=send_message_to_user,
                            report_infeasible_instructions=report_infeasible_instructions,
                        )
                        action_executed = True  # A browser action was attempted
                else:
                    # Handle case where CUA agent returns a string unexpectedly
                    logger.warning(
                        f"Received string action '{action}' from CUA agent, expected dict. Attempting Python execution."
                    )
                    # Fallback to execute as Python code
                    execute_python_code(
                        action,  # Assume the string is code
                        self.page,
                        send_message_to_user=send_message_to_user,
                        report_infeasible_instructions=report_infeasible_instructions,
                    )
                    action_executed = True

            else:  # Handle other agents (assuming string actions)
                if isinstance(action, str):
                    code_to_execute = action
                    if self.action_mapping:
                        # Apply mapping if provided
                        code_to_execute = self.action_mapping(action)

                    execute_python_code(
                        code_to_execute,
                        self.page,
                        send_message_to_user=send_message_to_user,
                        report_infeasible_instructions=report_infeasible_instructions,
                    )
                    action_executed = True
                else:
                    # Handle unexpected dict action from non-CUA agent
                    error_msg = f"Received unexpected dictionary action from agent '{agent_name}'"
                    self.last_action_error = error_msg
                    report_infeasible_instructions(error_msg)
                    action_executed = False  # No action attempted

        except Exception as e:
            self.last_action_error = f"{type(e).__name__}: {e}"
            logger.error(
                f"Error during action execution attempt: {self.last_action_error}",
                exc_info=True,
            )  # Log with traceback
            # Check for timeout specifically
            timeout_match = re.match(
                r"TimeoutError: Timeout (\d+)ms exceeded", self.last_action_error
            )
            if timeout_match:
                info["action_exec_timeout"] = float(timeout_match.group(1)) / 1000  # ms to sec

            # Report as infeasible only if we actually tried to execute something
            # and it wasn't an error already reported by the agent itself.
            if action_executed and not agent_reported_error:
                report_infeasible_instructions(f"Execution failed: {self.last_action_error}")

        # Log whether an action was executed or not
        if action_executed:
            logger.debug("Action execution attempt finished.")
        elif not agent_reported_error:  # Avoid double logging if agent already reported error
            logger.debug(f"No browser action executed for this step (Action: {self.last_action}).")

        info["action_exec_stop"] = time.time()

        # wait a bit only if an action was executed that might change state
        if action_executed:
            time.sleep(0.5)  # wait for JS events to be fired (half a second)
            # Try/catch cookies call as it can sometimes fail if context is closed unexpectedly
            try:
                self.context.cookies()  # trigger all waiting Playwright callbacks
            except Exception as e:
                logger.warning(f"Could not trigger Playwright callbacks via context.cookies(): {e}")

        # wait for the network to idle before extracting the observation, reward etc.
        self._wait_dom_loaded()

        # after the action is executed, the active page might have changed
        # perform a safety check
        self._active_page_check()
        logger.debug("Active page checked")

        # if asked, wait for user message
        self._wait_for_user_message()
        logger.debug("User message done")

        logger.debug("Initiating task validation")
        # extract reward, done, user_message, info (task-specific)
        reward, done, user_message, task_info = self._task_validate()
        info["task_info"] = task_info
        logger.debug("Task validation done")

        # add any user message sent by the task to the chat
        if user_message:
            self.chat.add_message(role="user", msg=user_message)

        # extract observation (generic)
        obs = self._get_obs()
        logger.debug("Observation extracted")

        # new step API wants a 5-tuple (gymnasium)
        terminated = done or (
            self.terminate_on_infeasible and self.infeasible_message_received
        )  # task or agent can terminate the episode
        truncated = False

        return obs, reward, terminated, truncated, info

    def _task_validate(self):
        # back-up these in case validate() navigates pages and messes the history
        prev_active_page = self.page
        prev_page_history = self.page_history.copy()
        # call validate
        reward, done, user_message, info = self.task.validate(self.page, self.chat.messages)

        # safety fix, in case validate() did mess up the active page and/or page history
        if prev_active_page != self.page or prev_page_history != self.page_history:
            logger.info(
                "The active page and / or page history has changed during task.validate(). A recovery fix will be applied."
            )
            self.page = prev_active_page
            self.page_history = prev_page_history

        return reward, done, user_message, info

    def _wait_for_user_message(self):
        # if last message is from the assistant, wait for a user message to continue
        # TODO: be smarter about when to wait for a user message (different action from the assistant?)
        if self.chat.messages[-1]["role"] == "assistant" and self.wait_for_user_message:
            self.chat.wait_for_user_message()

    def _wait_dom_loaded(self):
        for page in self.context.pages:
            try:
                page.wait_for_load_state("domcontentloaded", timeout=3000)
            except playwright.sync_api.Error:
                pass
            for frame in page.frames:
                try:
                    frame.wait_for_load_state("domcontentloaded", timeout=3000)
                except playwright.sync_api.Error:
                    pass

    def _activate_page_from_js(self, page: playwright.sync_api.Page):
        logger.debug(f"_activate_page_from_js(page) called, page={str(page)}")
        if not page.context == self.context:
            raise RuntimeError(
                f"Unexpected: activating a page that belongs to a different browser context ({page})."
            )

        # add the activated page to the page history (or move it to last which is the most recent)
        if page in self.page_history:
            self.page_history[page] = self.page_history.pop(
                page
            )  # move page to the end of dictionnary
        else:
            self.page_history[page] = None  # add page to the end of dictionnary

        self.page = page

    def _active_page_check(self):
        # make sure there is always a page open
        # if all pages have been closed, create a new page
        if len(self.context.pages) == 0:
            logger.warning("All pages are closed, opening a new page.")
            self.page = self.context.new_page()

        # if the active page got closed, get the last active page from the history
        while self.page_history and (self.page.is_closed() or self.page not in self.context.pages):
            self.page_history.pop(self.page)  # remove active page from history
            self.page = list(self.page_history.keys())[
                -1
            ]  # set last active page as the active page (most recent)

        # active page should share the same browser context with the environment
        if self.page not in self.context.pages:
            raise RuntimeError(
                f"Unexpected: active page is not part of the browser context's open pages ({self.page})."
            )

        # active page should not be closed
        if self.page.is_closed():
            raise RuntimeError(f"Unexpected: active page has been closed ({self.page}).")

    def _get_obs(self):
        for retries_left in reversed(range(EXTRACT_OBS_MAX_TRIES)):
            try:
                # pre-extraction, mark dom elements (set bid, set dynamic attributes like value and checked)
                _pre_extract(self.page, self.tags_to_mark)

                dom = extract_dom_snapshot(self.page)
                axtree = extract_merged_axtree(self.page)
                focused_element_bid = extract_focused_element_bid(self.page)
                extra_properties = extract_dom_extra_properties(dom)
            except (playwright.sync_api.Error, MarkingError) as e:
                err_msg = str(e)
                # try to add robustness to async events (detached / deleted frames)
                if retries_left > 0 and (
                    "Frame was detached" in err_msg
                    or "Frame with the given frameId is not found" in err_msg
                    or "Execution context was destroyed" in err_msg
                    or "Frame has been detached" in err_msg
                    or "Cannot mark a child frame without a bid" in err_msg
                ):
                    logger.warning(
                        f"An error occured while extracting the dom and axtree. Retrying ({retries_left}/{EXTRACT_OBS_MAX_TRIES} tries left).\n{repr(e)}"
                    )
                    # post-extract cleanup (ARIA attributes)
                    _post_extract(self.page)
                    time.sleep(0.5)
                    continue
                else:
                    raise e
            break

        # post-extraction cleanup of temporary info in dom
        _post_extract(self.page)

        task_id = getattr(self.task, "task_id", None)
        if task_id is None:
            task_getter = getattr(self.task.__class__, "get_task_id", None)
            if callable(task_getter):
                try:
                    task_id = task_getter()
                except TypeError:
                    task_id = None
        task_id = str(task_id) if task_id is not None else ""

        # obs is generic to all tasks
        obs = {
            "chat_messages": copy.deepcopy(self.chat.messages),
            "goal": _try_to_extract_legacy_goal(self.goal_object),  # legacy goal, deprecated
            "goal_object": self.goal_object,  # new goal format, list of messages openai style
            "task_id": task_id,
            "open_pages_urls": [page.url for page in self.context.pages],
            "active_page_index": np.asarray([self.context.pages.index(self.page)]),
            "url": self.page.url,
            "screenshot": extract_screenshot(self.page),
            "dom_object": dom,
            "axtree_object": axtree,
            "extra_element_properties": extra_properties,
            "focused_element_bid": focused_element_bid,
            "last_action": self.last_action,
            "last_action_error": self.last_action_error,
            "elapsed_time": np.asarray([time.time() - self.start_time]),
            "browser": self.browser,  # Direct access to the browser object
        }

        return obs
