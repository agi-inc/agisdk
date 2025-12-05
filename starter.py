from agisdk import REAL


def run_agent(api_key=None, run_name=None):
    harness = REAL.harness(
        model="gpt-4o",
        headless=True,
        max_steps=25,
        use_screenshot=True,
        use_axtree=True,
        num_workers=1,
    )
    return harness.run()


if __name__ == "__main__":
    run_agent()
