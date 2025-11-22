import asyncio

from agi_agents.qwen.qwen import QwenAgent
from arena import RunHarness


async def main():
    agent = QwenAgent()

    harness = RunHarness(
        agent=agent,
        tasks=[
            "src/benchmarks/hackathon/tasks/*"
        ],
        parallel=60,
        sample_count=1,
        max_steps=60,
        headless=True,
    )

    results = await harness.run()
    print(results)


if __name__ == "__main__":
    asyncio.run(main())
