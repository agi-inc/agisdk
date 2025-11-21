import os
from agisdk import REAL

# Optional leaderboard configuration.
# Set REAL_API_KEY / REAL_RUN_ID / REAL_MODEL_NAME / REAL_RUN_NAME in your environment
# (or replace the placeholders below) to submit results to the REAL portal.
API_KEY = os.environ.get("REAL_API_KEY") or "<Your API key>"
RUN_ID = os.environ.get("REAL_RUN_ID") or "<Your run ID>"

submit_to_leaderboard = (
    API_KEY not in ("", "<YOUR_REAL_API_KEY>")
    and RUN_ID not in ("", "<YOUR_RUN_ID>")
)

harness = REAL.harness(
    model="gpt-5",
    task_version="v2",
    task_name="omnizon-2",
    headless=False,
    leaderboard=submit_to_leaderboard,
    run_id=RUN_ID if submit_to_leaderboard else None,
    api_key=API_KEY if submit_to_leaderboard else None,
    force_refresh=True,
    use_cache=False,
)

print(harness.run())
