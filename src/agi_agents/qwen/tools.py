"""
Tool execution for Qwen agent with text-based tool calling.
"""

from typing import Dict, Any, Tuple

from patchright.async_api import Page


class QwenToolExecutor:
    """Execute tools for Qwen agent."""

    def __init__(
        self,
        page: Page,
        browser: "AgentBrowser",
        state: "AgentState",
        original_width: int,
        original_height: int,
    ):
        self.page = page
        self.browser = browser
        self.state = state
        self.original_width = original_width
        self.original_height = original_height

    def scale_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """Scale coordinates from 0-1000 range to actual viewport dimensions.

        Qwen returns coordinates in 0-1000 range, which we scale to actual image dimensions.
        This matches the behavior in qwen3vl.py.
        """
        scaled_x = int((x / 1000) * self.original_width)
        scaled_y = int((y / 1000) * self.original_height)
        return scaled_x, scaled_y

    async def _get_expanded_select(self):
        """Return first <select> element-handle that is AX-expanded, else None."""
        try:
            selects = await self.page.query_selector_all("select")
            for sel in selects:
                try:
                    ax = await self.page.accessibility.snapshot(root=sel)
                    if ax and ax.get("expanded"):
                        return sel
                except Exception:
                    continue  # element went stale
        except Exception:
            pass  # navigation race
        return None

    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute a tool and return result message."""
        if tool_name == "click":
            return await self._execute_click(tool_input)
        elif tool_name == "double_click":
            return await self._execute_double_click(tool_input)
        elif tool_name == "triple_click":
            return await self._execute_triple_click(tool_input)
        elif tool_name == "hover":
            return await self._execute_hover(tool_input)
        elif tool_name == "press_and_hold":
            return await self._execute_press_and_hold(tool_input)
        elif tool_name == "drag":
            return await self._execute_drag(tool_input)
        elif tool_name == "type":
            return await self._execute_type(tool_input)
        elif tool_name == "hotkey":
            return await self._execute_hotkey(tool_input)
        elif tool_name == "scroll":
            return await self._execute_scroll(tool_input)
        elif tool_name == "goto":
            return await self._execute_goto(tool_input)
        elif tool_name == "finished":
            return await self._execute_finished(tool_input)
        else:
            return f"Unknown tool: {tool_name}"

    async def _execute_click(self, tool_input: Dict[str, Any]) -> str:
        point = tool_input["point_2d"]
        x, y = self.scale_coordinates(point[0], point[1])
        await self.page.mouse.click(x, y)
        return f"Clicked at ({point[0]}, {point[1]})"

    async def _execute_double_click(self, tool_input: Dict[str, Any]) -> str:
        point = tool_input["point_2d"]
        x, y = self.scale_coordinates(point[0], point[1])
        await self.page.mouse.dblclick(x, y)
        return f"Double clicked at ({point[0]}, {point[1]})"

    async def _execute_triple_click(self, tool_input: Dict[str, Any]) -> str:
        point = tool_input["point_2d"]
        x, y = self.scale_coordinates(point[0], point[1])
        await self.page.mouse.click(x, y, click_count=3)
        return f"Triple clicked at ({point[0]}, {point[1]})"

    async def _execute_hover(self, tool_input: Dict[str, Any]) -> str:
        point = tool_input["point_2d"]
        x, y = self.scale_coordinates(point[0], point[1])
        await self.page.mouse.move(x, y)
        return f"Hovered at ({point[0]}, {point[1]})"

    async def _execute_press_and_hold(self, tool_input: Dict[str, Any]) -> str:
        point = tool_input["point_2d"]
        x, y = self.scale_coordinates(point[0], point[1])
        await self.page.mouse.move(x, y)
        await self.page.mouse.down()
        return f"Pressed and held at ({point[0]}, {point[1]})"

    async def _execute_drag(self, tool_input: Dict[str, Any]) -> str:
        start_point = tool_input["start_point_2d"]
        end_point = tool_input["end_point_2d"]
        start_x, start_y = self.scale_coordinates(start_point[0], start_point[1])
        end_x, end_y = self.scale_coordinates(end_point[0], end_point[1])

        await self.page.mouse.move(start_x, start_y)
        await self.page.mouse.down()
        await self.page.mouse.move(end_x, end_y)
        await self.page.mouse.up()
        return f"Dragged from ({start_point[0]}, {start_point[1]}) to ({end_point[0]}, {end_point[1]})"

    async def _execute_type(self, tool_input: Dict[str, Any]) -> str:
        content = tool_input["content"]
        await self.page.keyboard.type(content, delay=50)
        return f"Typed: {content[:50]}{'...' if len(content) > 50 else ''}"

    async def _execute_hotkey(self, tool_input: Dict[str, Any]) -> str:
        key = tool_input["key"]
        await self.page.keyboard.press(key)
        return f"Pressed hotkey: {key}"

    async def _execute_scroll(self, tool_input: Dict[str, Any]) -> str:
        direction = tool_input["direction"]
        pixels = tool_input.get("pixels", 300)

        # If point_2d provided, scroll at that position
        if "point_2d" in tool_input:
            point = tool_input["point_2d"]
            x, y = self.scale_coordinates(point[0], point[1])
            await self.page.mouse.move(x, y)
        else:
            viewport_size = await self.page.evaluate(
                "({width: window.innerWidth, height: window.innerHeight})"
            )
            scroll_x = viewport_size["width"] / 2
            scroll_y = viewport_size["height"] / 2
            await self.page.mouse.move(scroll_x, scroll_y)

        # Focus the element under the cursor
        await self.page.wait_for_timeout(100)
        await self.page.evaluate(f"""
            const element = document.elementFromPoint({scroll_x}, {scroll_y});
            if (element && element.focus) {{
                element.focus();
            }}
        """)

        # Scroll in the specified direction
        if direction == "down":
            await self.page.mouse.wheel(0, pixels)
        elif direction == "up":
            await self.page.mouse.wheel(0, -pixels)
        elif direction == "right":
            await self.page.mouse.wheel(pixels, 0)
        elif direction == "left":
            await self.page.mouse.wheel(-pixels, 0)

        return f"Scrolled {direction} by {pixels} pixels"

    async def _execute_goto(self, tool_input: Dict[str, Any]) -> str:
        url = tool_input["url"].strip()
        await self.page.goto(url)
        return f"Navigated to: {url}"

    async def _execute_finished(self, tool_input: Dict[str, Any]) -> str:
        content = tool_input["content"]
        return f"Task finished: {content}"
