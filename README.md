<p align="center">
  <h3 align="center">AGI SDK</h3>
</p>

<p align="center"><a href="https://arxiv.org/abs/2504.11543">📄 Paper</a> | <a href="https://www.theagi.company/blog/introducing-real-bench">📝 Blog</a> | <a href="https://www.theagi.company">🏢 AGI Inc</a> | <a href="https://www.realevals.xyz">🏆 Leaderboard</a></p>

AGI SDK is a toolkit for building and evaluating AI agents. 

It comes with support for the [REAL benchmark](https://realevals.xyz) (Realistic Evaluations for Agents Leaderboard) to evaluate browser-based agents in real world settings.

<p align="center">
  <img src="images/real.gif" alt="Real benchmark gif">
</p>

## Installation

```bash
# Install from PyPI
pip install agisdk

# Install browser binaries required by Playwright
playwright install --force

# Set your OpenAI API key (required for evaluation)
export OPENAI_API_KEY="your-api-key"
```
To test it out, run:
```bash
python starter.py
```

## Quick Start

Here's a simple example to get you started for benchmarking an AI agent on the REAL Bench environment:

```python
from agisdk import REAL

# Create a harness with a pre-configured model
harness = REAL.harness(
    model="gpt-4o",
    task_name="webclones.omnizon-1",
    headless=False
)

# Run the experiment
results = harness.run()

```

## Running Custom Agents

Checkout the README.md in the `example` folder. There are three examples of custom agents in the `example` directory:

- `example/starter.py`: A simple example to get you started
- `example/custom.py`: A more complex example with a custom agent
- `example/nova.py`: For running custom agents which already have browsers running (in this case, Amazon NovaAct)

Additionally, there is a hackable example in `example/hackable.py` which is a can be configured for better performance and starting of.

## Local Development

Only if you want to develop locally, you can install from source:

```bash
# Clone the repository
git clone https://github.com/agi-inc/agisdk.git
cd agisdk

# Install in development mode
pip install -e .
```

## Available Tasks

The AGI SDK includes high-fidelity, fully-deterministic websites for agents to explore. These are modern web stack sites (React + Next.js) with rich functionality for core user flows, realistic mock data, and consistent behavior for testing and evaluation.

The benchmark includes these environments:

- **Omnizon** (`webclones.omnizon-*`): Similar to Amazon, for e-commerce shopping tasks
- **DashDish** (`webclones.dashdish-*`): Similar to DoorDash, for food delivery tasks
- **Fly Unified** (`webclones.fly-unified-*`): Similar to United Airlines, for flight booking
- **Staynb** (`webclones.staynb-*`): Similar to Airbnb, for accommodation booking
- **GoCalendar** (`webclones.gocalendar-*`): Similar to Google Calendar, for scheduling
- **GoMail** (`webclones.gomail-*`): Similar to Gmail, for email tasks
- **OpenDining** (`webclones.opendining-*`): Similar to OpenTable, for restaurant reservations
- **NetworkIn** (`webclones.networkin-*`): Similar to LinkedIn, for professional networking
- **Udriver** (`webclones.udriver-*`): Similar to Uber, for ride booking
- **TopWork** (`webclones.topwork-*`): Similar to UpWork, for freelance job marketplace
- **Zilloft** (`webclones.zilloft-*`): Similar to Zillow, for real estate browsing

Each task comes with practical, human-written goals that test an agent's ability to navigate and complete realistic web tasks.

## Additional Environment Variables

To use models from other providers, set their respective API keys:

```bash
# For Anthropic models (like sonnet-3.7)
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

## Observation Structure

Your agent gets access to the following observation structure:

```python
{
    'chat_messages': [...],          # History of chat messages
    'goal': "...",                   # Text description of the goal
    'goal_object': [...],            # Structured goal object with text and images
    'open_pages_urls': [...],        # List of open page URLs
    'active_page_index': 0,          # Index of the active page
    'url': "...",                    # Current URL
    'screenshot': np.array(...),     # Screenshot as numpy array
    'dom_object': {...},             # DOM structure
    'axtree_object': {...},          # Accessibility tree
    'extra_element_properties': {...}, # Additional element properties
    'focused_element_bid': "...",    # ID of the focused element
    'last_action': "...",            # Last action performed
    'last_action_error': "...",      # Error from last action (if any)
    'elapsed_time': 0.0,             # Time elapsed in the episode
    'browser': {...}                 # Playwright browser object (for direct control)
}
```

## Available Actions

Actions are specified as strings in the format of function calls. Here are some commonly used actions:

```python
# Navigation
"goto('https://www.google.com')"
"go_back()"
"go_forward()"

# Interaction
"click('element_id')"
"fill('input_id', 'text to enter')"
"press('Enter')"

# Communication
"send_msg_to_user('I found the answer: $42.99')"

# Reporting infeasible tasks
"report_infeasible('The requested item is out of stock')"
```

## Harness Configuration

The harness function accepts the following parameters:

```python
REAL.harness(
    # Agent configuration (provide one of these)
    model="gpt-4o",                                # OpenAI models
    model="sonnet-3.7",                            # Anthropic models
    model="openrouter/deepseek/deepseek-chat-v3-0324", # OpenRouter models (with openrouter/ prefix)
    agentargs=MyAgentArgs(),                       # Or provide your own agent arguments

    # Task selection (provide one of these)
    task_name="webclones.omnizon-1",  # Specific task to run
    task_type="omnizon",              # Run all tasks of this type
    task_id=1,                        # Run specific task ID within a type

    # Browser configuration
    headless=False,                   # Whether to show the browser
    max_steps=25,                     # Maximum number of steps
    browser_dimensions=(1280, 720),   # Browser window dimensions

    # Observation options
    use_html=False,                   # Include HTML in observations
    use_axtree=True,                  # Include accessibility tree
    use_screenshot=True,              # Include screenshots

    # Leaderboard submission
    leaderboard=False,                # Whether to submit to leaderboard
    run_id="my_unique_id",            # Unique ID for the submission

    # Execution options
    parallel=False,                   # Run tasks in parallel
    num_workers=4,                    # Number of parallel workers
    use_cache=True,                   # Use cached results when available
    cache_only=False,                 # Only use cached results
    force_refresh=False,              # Force re-running tasks

    # Output options
    results_dir="./results"           # Where to store results
)
```

# For OpenRouter models
```
export OPENROUTER_API_KEY="your-openrouter-api-key"
```

## Contributing

We welcome any contributions to the AGI SDK, whether it's submitting an idea, fixing a typo, adding a new guide, or improving an existing one.

- For general ideas or issues, share them on the [issues page](https://github.com/agi-inc/agisdk/issues).
- For issues with specific REAL tasks or websites, please report them in the corresponding column in our [project board](https://github.com/orgs/agi-inc/projects/2) so we can track and improve REAL.

If you want to directly contribute code, you can fork the repository, make your changes, and submit a pull request.
To avoid duplication of efforts, please review the existing issues and pull requests before contributing.

Happy building! 🙌
