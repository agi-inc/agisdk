from agisdk import REAL

def run_agent(api_key=None, run_name=None):
    harness = REAL.harness(
        model="gpt-4o-mini",
        task_name="webclones.omnizon-2",
        headless=True,  # Change this if you want to see the browser
        max_steps=25,
        use_screenshot=True,
        use_axtree=True,
        api_key=api_key,
        run_name=run_name
    )
    return harness.run()

if __name__ == "__main__":
    run_agent()