import os
from agisdk import REAL

# Optional leaderboard configuration.
# Set REAL_API_KEY / REAL_RUN_ID / REAL_MODEL_NAME / REAL_RUN_NAME in your environment
# (or replace the placeholders below) to submit results to the REAL portal.
API_KEY = os.environ.get("REAL_API_KEY") or "<YOUR_REAL_API_KEY>"
RUN_ID = os.environ.get("REAL_RUN_ID") or "<YOUR_RUN_ID>"
MODEL_NAME = os.environ.get("REAL_MODEL_NAME") or "my_model_name"
RUN_NAME = os.environ.get("REAL_RUN_NAME") or "my_run_name"

submit_to_leaderboard = (
    API_KEY not in ("", "<YOUR_REAL_API_KEY>")
    and RUN_ID not in ("", "<YOUR_RUN_ID>")
)

harness = REAL.harness(
    model="gpt-4o",
    task_name="webclones.omnizon-1",
    headless=False,
    leaderboard=submit_to_leaderboard,
    run_id=RUN_ID if submit_to_leaderboard else None,
    api_key=API_KEY if submit_to_leaderboard else None,
    run_name=RUN_NAME if submit_to_leaderboard else None,
    model_id_name=MODEL_NAME if submit_to_leaderboard else None,
    force_refresh=True,
    use_cache=False,
)

print(harness.run())
