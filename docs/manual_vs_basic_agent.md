# Manual vs. Basic Demo Agent

This note contrasts the LLM-driven `DemoAgent` (`src/agisdk/REAL/demo_agent/basic_agent.py`) with the manual-intervention `ManualAgent` (`src/agisdk/REAL/demo_agent/manual_agent.py`). The methods are listed side-by-side to highlight shared responsibilities and the key differences in how each implementation fulfils them.

## Core Class Structure Overview

| Component | `DemoAgent` | `ManualAgent` |
| --- | --- | --- |
| Base class | `Agent` | `Agent` |
| Action set | `HighLevelActionSet` (chat/bid/infeas) | Same subsets; demo-mode used only for visual cues |
| Primary purpose | Query an LLM to decide every action | Pause automation and let a human perform the task, only rejoining to close out the episode |

## Method-by-Method Comparison

### `__init__`

| Method | Description |
| --- | --- |
| `DemoAgent.__init__(model_name, chat_mode, demo_mode, use_html, use_axtree, use_screenshot, …)` | Builds the high-level action set and wires up an LLM client depending on the requested provider (OpenAI, Anthropic, OpenRouter, local vLLM). Stores observation toggles and validates that at least one structure (`use_html` or `use_axtree`) is enabled. |
| `ManualAgent.__init__(demo_mode, wait_prompt, settle_wait_ms, show_goal_panel, completion_message)` | Constructs the same action-set subset but does not speak to any LLM. Instead it stores CLI-facing configuration: the terminal prompt shown while waiting, the post-confirmation delay, and the fallback completion message that will be sent if the operator does not type a custom summary. It also initialises internal flags used by a small state machine that tracks where the human-intervention flow currently sits. |

### `obs_preprocessor`

| Method | Description |
| --- | --- |
| `DemoAgent.obs_preprocessor(obs)` | Converts raw observations into the text/blobs expected by the LLM prompt: flattens DOM + AX tree, prunes HTML, preserves screenshot and chat history. |
| `ManualAgent.obs_preprocessor(obs)` | Mirrors the exact same transformation so recorded traces look identical; the human still sees the same metadata alongside the browser. |

### Session lifecycle helpers

| Method | `DemoAgent` role | `ManualAgent` role |
| --- | --- | --- |
| `_display_start_instructions` | n/a | Logs the goal/current URL via Rich; optionally shows the goal panel to the terminal operator. |
| `_await_user_confirmation` | n/a | Blocks the agent until the terminal operator presses Enter; captures interruption via `KeyboardInterrupt`. |
| `_format_send_action` | n/a | (Manual only) Escapes the final summary into a `send_msg_to_user("…")` action so the harness captures an assistant chat turn. |
| `_make_noop_action` | n/a | Returns `noop()` or `noop(ms)` based on the configured settle delay; used to allow the `/finish` endpoint to stabilise before evaluation. |

### `get_action`

| Agent | Behaviour |
| --- | --- |
| `DemoAgent.get_action(obs)` | 1. Emits a rich console banner for the first step.<br>2. Builds system + user message stacks containing goal, chat, observation text, action history, and optional screenshot.<br>3. Calls the configured `query_model` to get an LLM response.<br>4. Logs the action summary, tracks history, and returns the action string plus empty info dict. |
| `ManualAgent.get_action(obs)` | 1. On first invocation logs the goal panel and console instructions.<br>2. Immediately afterwards waits for the operator to finish the task and press Enter (optionally typing the final summary in the same prompt).<br>3. Sends that summary—falling back to the configured completion message if the operator left it blank—to create the assistant chat turn required by the verifier.<br>4. Issues a single `noop(settle_wait_ms)` to let the web clone settle.<br>5. Finally returns `None` with stats (including the captured manual summary) so the harness terminates the episode gracefully.<br>6. On the next task, `_reset_episode_state()` clears the internal flags (prompted/done/noop sent, etc.) so the agent waits for human input again rather than short-circuiting subsequent episodes. |

### `close` / end-of-run reporting

| Agent | Description |
| --- | --- |
| `DemoAgent.close()` | Emits a rich “task complete” panel: reports success/failure (if the environment supplied it), total reward, time spent, and action count. |
| `ManualAgent` | Relies on console logging inside `get_action` when returning `None`; there is no separate `close` override because the manual flow finishes as soon as the episode terminates. |

### `ManualAgentArgs` vs. `DemoAgentArgs`

Both dataclasses inherit from `AbstractAgentArgs` and expose configuration knobs for harness consumers:

| Field | `DemoAgentArgs` | `ManualAgentArgs` |
| --- | --- | --- |
| Model connectivity | `model_name`, API keys, system-message handling, etc. | None; manual agent ignores model settings. |
| Observation toggles | `use_html`, `use_axtree`, `use_screenshot` | Uses harness defaults (`use_axtree=True` and `use_screenshot=True`) passed in through the harness directly. |
| Manual-specific knobs | n/a | `wait_prompt`, `settle_wait_ms`, `completion_message`, `show_goal_panel`, `demo_mode`. |
| `make_agent()` | Instantiates `DemoAgent` with the captured LLM configuration. | Instantiates `ManualAgent` with the terminal UX strings and timing configuration. |

## Key Takeaways

1. **Identical observation footprints:** both agents preprocess observations the same way. This keeps experiment logs uniform for downstream verifiers.
2. **Different control flow:** the basic agent is fully autonomous via an LLM; the manual agent blocks for a human to finish the task, then sends their typed summary and hands control back to the harness.
3. **Verifier compatibility:** the manual agent captures the human’s final summary (or a default) and sends it as an assistant message, ensuring BrowserGym fetches `/finish` and scores the run.
4. **Harness integration is unchanged:** both agents are instantiated through their respective `…AgentArgs` dataclasses, so swapping between them in the harness is a one-line change.

Use this comparison when you need to understand where to extend the manual agent (e.g., different chat phrasing or extra telemetry) or when exploring how to create a hybrid that combines manual oversight with occasional LLM actions.
