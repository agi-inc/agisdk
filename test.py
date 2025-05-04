import os
import argparse
from agisdk import REAL
from dotenv import load_dotenv
import multiprocessing

multiprocessing.set_start_method('fork')
load_dotenv()

parser = argparse.ArgumentParser(description="Process model and dataset arguments.")
parser.add_argument('--model', type=str, default="gpt-4o-mini", required=False, help='Model name (e.g., gpt-4o-mini)')
parser.add_argument('--use_html', action='store_true', help='Enable HTML observation')
parser.add_argument('--no_axtree', action='store_false', help='Disable AxTree observation')
parser.add_argument('--no_screenshot', action='store_false', help='Disable Screen observation')
parser.add_argument('--task', type=str, default=None, required=False, help='Task identifier (e.g., webclones.omnizon-1)')
parser.add_argument('--results_dir', type=str, default="results", required=False, help='Directory to put your results')
parser.add_argument('--num_workers', type=int, default=4, help='Number of Parallel execution')
args = parser.parse_args()

# Create a harness with a pre-configured model
# By Default, the observation contains:
# 1. AxTree 2. Screenshot
harness = REAL.harness(
    model=args.model,
    task_name=args.task,
    results_dir=args.results_dir,
    use_html=args.use_html,
    use_axtree=args.no_axtree,
    use_screenshot=args.no_screenshot,
    headless=True,
    parallel=True,
    num_workers=args.num_workers,
)

# Run the experiment
results = harness.run()