# Agent Harness

Minimal browser automation agent harness for running benchmarks with Agents.

## Setup

It's recommended to use [uv](https://docs.astral.sh/uv/), a very fast Python environment manager, to create and manage Python environments

```bash
uv sync
```

## Usage

Set your API key:
```bash
export OPENROUTER_API_KEY="your-key-here"
export OPENAI_API_KEY="your-key-here"
```

Run all hackathon tasks:
```bash
uv run ./scripts/bench.py
```

## Architecture

- **arena/** - Core execution engine (parallel task running, browser management)
- **agi_agents/** - Agent implementations <- Add your own here!
- **benchmarks/hackathon/** - 16 benchmark tasks + evaluator
- **scripts/** - Entry point scripts

## Tasks

The system includes 16 tasks across multiple web applications:
- GoCalendar (4 tasks) - Calendar management
- GoMail (4 tasks) - Email operations
- Marrisuite (4 tasks) - Hotel booking
- Networkin (4 tasks) - Social networking

Each task runs independently in its own browser instance with parallel execution.
