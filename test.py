import os
import argparse
from agisdk import REAL
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser(description="Process model and dataset arguments.")
parser.add_argument('--model', type=str, default="gpt-4o-mini", required=False, help='Model name (e.g., gpt-4o-mini)')
parser.add_argument('--task', type=str, default=None, required=False, help='Task identifier (e.g., webclones.omnizon-1)')
parser.add_argument('--results_dir', type=str, default="results", required=False, help='Directory to put your results')
args = parser.parse_args()

# Create a harness with a pre-configured model
harness = REAL.harness(
    model=args.model,
    task_name=args.task,
    results_dir=args.results_dir,
    headless=True,
)

# Run the experiment
results = harness.run()