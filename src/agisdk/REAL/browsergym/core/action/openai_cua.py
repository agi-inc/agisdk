import time
from typing import Callable

from playwright.sync_api import Page

# Optional: key mapping if your model uses "CUA" style keys
CUA_KEY_TO_PLAYWRIGHT_KEY = {
    "/": "Divide",
    "\\": "Backslash",
    "alt": "Alt",
    "arrowdown": "ArrowDown",
    "arrowleft": "ArrowLeft",
    "arrowright": "ArrowRight",
    "arrowup": "ArrowUp",
    "backspace": "Backspace",
    "capslock": "CapsLock",
    "cmd": "Meta",
    "ctrl": "Control",
    "delete": "Delete",
    "end": "End",
    "enter": "Enter",
    "esc": "Escape",
    "home": "Home",
    "insert": "Insert",
    "option": "Alt",
    "pagedown": "PageDown",
    "pageup": "PageUp",
    "shift": "Shift",
    "space": " ",
    "super": "Meta",
    "tab": "Tab",
    "win": "Meta",
}


def execute_openai_cua_action(
    action: dict,  # Action is expected to be a dictionary from the OperatorAgent
    page: Page,
    send_message_to_user: Callable[[str], None],
    report_infeasible_instructions: Callable[[str], None],
) -> None:
    """
    Execute a CUA (Computer Use Assistant) action using the OpenAI format.

    Args:
        action: The action dictionary in OpenAI CUA format
        page: The Playwright page to interact with
        send_message_to_user: Function to send messages to the user
        report_infeasible_instructions: Function to report infeasible instructions
    """
    if not isinstance(action, dict):
        report_infeasible_instructions("Action must be a dictionary")
        return

    action_type = action.get("type")
    action_args = {k: v for k, v in action.items() if k != "type"}

    try:
        if action_type == "screenshot":
            # Ignore screenshot actions as requested
            pass
        elif action_type == "click":
            x = action_args.get("x")
            y = action_args.get("y")
            button = action_args.get("button", "left")
            if x is not None and y is not None:
                match button:
                    case "back":
                        page.go_back()
                    case "forward":
                        page.go_forward()
                    case "wheel":
                        page.mouse.wheel(
                            x, y
                        )  # Note: Playwright wheel doesn't use x,y like this. Might need adjustment.
                    case _:
                        button_mapping = {"left": "left", "right": "right"}
                        button_type = button_mapping.get(button, "left")
                        page.mouse.click(x, y, button=button_type)
            else:
                report_infeasible_instructions("Click action requires 'x' and 'y' coordinates.")
        elif action_type == "double_click":
            x = action_args.get("x")
            y = action_args.get("y")
            if x is not None and y is not None:
                page.mouse.dblclick(x, y)
            else:
                report_infeasible_instructions(
                    "Double click action requires 'x' and 'y' coordinates."
                )
        elif action_type == "scroll":
            # Scroll based on scroll_x and scroll_y, ignore x, y for move
            scroll_x = action_args.get("scroll_x", 0)
            scroll_y = action_args.get("scroll_y", 0)
            # Using evaluate for window.scrollBy as in test_cua.py
            page.evaluate(f"window.scrollBy({scroll_x}, {scroll_y})")
        elif action_type == "type":
            text = action_args.get("text", "")
            page.keyboard.type(text)
        elif action_type == "wait":
            ms = action_args.get("ms", 5000)
            print(f"Waiting for {ms / 1000} seconds")
            time.sleep(ms / 1000)
        elif action_type == "move":
            x = action_args.get("x")
            y = action_args.get("y")
            if x is not None and y is not None:
                page.mouse.move(x, y)
            else:
                report_infeasible_instructions("Move action requires 'x' and 'y' coordinates.")
        elif action_type == "keypress":
            keys = action_args.get("keys")
            if keys and isinstance(keys, list):
                mapped_keys = [CUA_KEY_TO_PLAYWRIGHT_KEY.get(key.lower(), key) for key in keys]
                for key in mapped_keys:
                    page.keyboard.down(key)
                for key in reversed(mapped_keys):
                    page.keyboard.up(key)
            else:
                report_infeasible_instructions("Keypress action requires a 'keys' list.")
        elif action_type == "drag":
            path = action_args.get("path")
            if path and isinstance(path, list) and len(path) > 0:
                if all("x" in p and "y" in p for p in path):
                    page.mouse.move(path[0]["x"], path[0]["y"])
                    page.mouse.down()
                    for point in path[1:]:
                        page.mouse.move(point["x"], point["y"])
                    page.mouse.up()
                else:
                    report_infeasible_instructions(
                        "Drag path items must contain 'x' and 'y' coordinates."
                    )
            else:
                report_infeasible_instructions("Drag action requires a non-empty 'path' list.")
        elif action_type == "message":  # Handle message type
            content = action_args.get("content")
            send_message_to_user(content)
        else:
            report_infeasible_instructions(f"Unsupported action type: {action_type}")
    except Exception as e:
        print(f"[bold red]Error executing action {action_type}: {e}[/bold red]")
        report_infeasible_instructions(f"Error executing action {action_type}: {e}")
