import asyncio
import copy
import datetime
import base64
import io
import json
import re
import os
from typing import List, Dict, Any, Tuple

from patchright.async_api import Page
import pytz
from openai import AsyncOpenAI
from PIL import Image

from arena import BaseAgent, AgentBrowser, AgentState
from agi_agents.prompts import QWEN_AGENT
from .tools import QwenToolExecutor


def _pil_to_data_url(image: Image.Image) -> str:
    """Convert a PIL image to a data URL suitable for OpenAI-compatible image_url content."""
    buf = io.BytesIO()
    fmt = "JPEG"
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    image.save(buf, format=fmt, quality=80)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64}"


class QwenAgent(BaseAgent):
    """Browser automation agent using Qwen with text-based tool calling via DashScope."""

    def __init__(
        self,
        # model: str = "qwen3-vl-plus",
        model: str = "qwen/qwen3-vl-235b-a22b-thinking",
        date_mode: str = "current",
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.model = model
        self.date_mode = date_mode
        assert date_mode in ["fixed", "current"]

        api_key = api_key or os.getenv("OPENAI_API_KEY")
        base_url = (base_url or "https://openrouter.ai/api/v1").rstrip("/")
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )

        # Min/max pixels for Qwen vision model
        self.min_pixels = 64 * 32 * 32
        self.max_pixels = 9800 * 32 * 32
        # Number of recent images to include (including current)
        self.visual_history_length = 4

    async def _get_expanded_select(self, page: Page):
        """Return first <select> element-handle that is AX-expanded, else None."""
        try:
            selects = await page.query_selector_all("select")
            for sel in selects:
                try:
                    ax = await page.accessibility.snapshot(root=sel)
                    if ax and ax.get("expanded"):
                        return sel
                except Exception:
                    continue  # element went stale
        except Exception:
            pass  # navigation race
        return None

    async def _check_dropdown_options(self, page):
        """Check for open dropdowns and return their options."""
        sel = await self._get_expanded_select(page)
        if sel:
            try:
                vals = await sel.evaluate(
                    "s => Array.from(s.options).map(o => o.value)"
                )
                if vals:
                    # Format for agent: show values clearly
                    return [f"'{val}'" if val else "''" for val in vals]
            except Exception:
                pass  # element went stale or other error
        return None

    async def _take_screenshot_cdp(self, browser: AgentBrowser) -> bytes:
        """Take screenshot instantly using CDP."""
        cdp = await browser.context.new_cdp_session(browser.page)
        result = await cdp.send(
            "Page.captureScreenshot", {"format": "jpeg", "quality": 80}
        )
        return base64.b64decode(result["data"])

    def _screenshot_to_data_url(self, screenshot_bytes: bytes) -> str:
        """Convert screenshot bytes to data URL without resizing."""
        b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"

    async def build_messages(
        self, state: AgentState, screenshot: bytes
    ) -> List[Dict[str, Any]]:
        """Build message list for OpenAI API from state."""
        # Build system message
        if self.date_mode == "current":
            pacific_tz = pytz.timezone("US/Pacific")
            current_date = datetime.datetime.now(pacific_tz).strftime("%Y-%m-%d")
            current_date = f"y-m-d: {current_date}"
        else:
            current_date = "Year 2024"

        system_message = {
            "role": "system",
            "content": QWEN_AGENT.format(date=current_date),
        }

        # If no messages yet, create first user message with goal
        if not state.messages:
            state.messages.append(
                {
                    "role": "user",
                    "content": f"## Task Goal\n{state.goal}",
                }
            )

        # Copy messages and then prune older image parts, keeping only the last N images
        messages = [system_message] + copy.deepcopy(state.messages)

        # Gather all image content parts across messages (skip system at index 0)
        image_positions = []
        for mi, msg in enumerate(messages[1:], start=1):
            content = msg.get("content")
            if isinstance(content, list):
                for pi, part in enumerate(content):
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        image_positions.append((mi, pi))

        # Decide which image parts to keep: last self.visual_history_length images
        keep_set = set(
            image_positions[-self.visual_history_length :]
            if self.visual_history_length > 0
            else []
        )

        # Remove image parts not in keep_set; drop empty messages that become [] content
        msgs_to_remove = []
        for mi, msg in enumerate(messages):
            content = msg.get("content")
            if isinstance(content, list):
                new_parts = []
                for pi, part in enumerate(content):
                    is_image = (
                        isinstance(part, dict) and part.get("type") == "image_url"
                    )
                    if not is_image:
                        new_parts.append(part)
                    else:
                        if (mi, pi) in keep_set:
                            part.setdefault("min_pixels", self.min_pixels)
                            part.setdefault("max_pixels", self.max_pixels)
                            new_parts.append(part)
                if len(new_parts) == 0:
                    msgs_to_remove.append(mi)
                else:
                    msg["content"] = new_parts

        # Remove messages that no longer have any content
        for idx in reversed(msgs_to_remove):
            del messages[idx]

        return messages

    def _parse_tool_calls(self, content: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Parse all tool calls from text content.

        Handles formats like:
        - click({"point_2d": [158, 100]})
        - type({"content": "hello"})

        Returns list of (tool_name, tool_args) tuples.
        """
        if not content:
            return []

        pattern = r"(\w+)\s*\(\s*(\{.*?\})\s*\)"
        tool_calls: List[Tuple[str, Dict[str, Any]]] = []

        for match in re.finditer(pattern, content, flags=re.DOTALL):
            func_name = match.group(1)
            json_str = match.group(2)
            try:
                arguments = json.loads(json_str)
            except json.JSONDecodeError:
                continue
            tool_calls.append((func_name, arguments))

        return tool_calls

    async def step(self, browser: AgentBrowser, state: AgentState) -> AgentState:
        """Execute one agent step using Qwen's native tool calling."""
        state.model = self.model

        # Get viewport dimensions for coordinate scaling
        screenshot = await self._take_screenshot_cdp(browser)
        # Always derive dimensions from the screenshot so scaling matches real pixels
        image = Image.open(io.BytesIO(screenshot))
        original_width, original_height = image.width, image.height

        # Ensure first turn includes task goal before image
        if not state.messages:
            state.messages.append(
                {"role": "user", "content": f"## Task Goal\n{state.goal}"}
            )

        # Append current screenshot message to state to interleave with dialogue

        data_url = self._screenshot_to_data_url(screenshot)

        state.messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url},
                        "min_pixels": self.min_pixels,
                        "max_pixels": self.max_pixels,
                    }
                ],
            }
        )

        # Build messages (will filter to the last 4 images)
        messages = await self.build_messages(state, screenshot)

        # Call API with retry logic
        max_retries = 100
        response = None
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.0,
                    max_tokens=1024,
                    messages=messages,
                )
                break
            except Exception as e:
                if attempt == max_retries:
                    raise e
                await asyncio.sleep(1.0)
        if response is None:
            raise RuntimeError("Qwen API call failed without response")
        message = response.choices[0].message

        # Save assistant message to state (just content, no tool parsing)
        state.messages.append({"role": "assistant", "content": message.content or ""})

        # Parse and execute tool calls
        tool_calls = self._parse_tool_calls(message.content)

        if tool_calls:
            tool_executor = QwenToolExecutor(
                page=browser.page,
                browser=browser,
                state=state,
                original_width=original_width,
                original_height=original_height,
            )

            tool_results: List[str] = []

            for tool_name, tool_args in tool_calls:
                try:
                    result_text = await tool_executor.execute_tool(tool_name, tool_args)
                    if tool_name == "finished":
                        state.finished = True
                except Exception as e:
                    result_text = f"Tool execution failed: {str(e)}"
                tool_results.append(result_text)
                if state.finished:
                    break

            await browser.page.wait_for_timeout(2000)

            # Check for open dropdowns
            try:
                dropdown_options = await asyncio.wait_for(
                    self._check_dropdown_options(browser.page), timeout=5.0
                )
            except Exception:
                dropdown_options = None

            # Build result message with dropdown info if found
            result_parts = list(tool_results)
            if dropdown_options:
                dropdown_message = f"""

You just opened a system level dropdown, which cannot be shown in the screenshots so the options are displayed in text form below.
Use the select_dropdown tool to select an option from the dropdown. Use the exact value (the part in quotes) from the available dropdown options.

Available dropdown options: {dropdown_options}"""
                result_parts.append(dropdown_message)

            # Save result as simple user message
            state.messages.append({"role": "user", "content": "\n".join(result_parts)})

        return state
