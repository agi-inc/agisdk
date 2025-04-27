import os
from agisdk import REAL
from dotenv import load_dotenv

load_dotenv()

# Create a harness with a pre-configured model
harness = REAL.harness(
    model="gpt-4o-mini",
    task_name="webclones.omnizon-1",
    headless=True
)

# Run the experiment
results = harness.run()

