import os
import argparse
from agisdk import REAL
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser(description="Process model and dataset arguments.")
parser.add_argument('--model', type=str, default="gpt-4o-mini", required=False, help='Model name (e.g., gpt-4o-mini)')
parser.add_argument('--task', type=str, default=None, required=False, help='Dataset identifier (e.g., webclones.omnizon-1)')
args = parser.parse_args()

# Create a harness with a pre-configured model
harness = REAL.harness(
    model=args.model,
    task_name=args.task,
    headless=True
)

# Run the experiment
results = harness.run()