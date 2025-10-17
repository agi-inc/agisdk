import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agisdk import REAL
import os
import json

os.environ["RAILWAY_API_BASE"] = "https://evaluate-production.up.railway.app"

results = REAL.harness(
    model="o3",
    task_name="webclones.dashdish-10",  # You changed to dashdish-2
    headless=False,
    leaderboard=True,
    api_key="d424c804a5b7326b590ba1f59340f1718ff02e1afdf81626ccfb3376edcaaefc",
  
    run_id="f03b183e-b978-467a-a719-3021b34f9304",
    force_refresh=True,
    # use_cache=False
).run()

# ✅ First, see what keys are actually in results
print(f"\n🔍 Results type: {type(results)}")
print(f"🔍 Results keys: {list(results.keys())}")
print(f"🔍 Number of results: {len(results)}")

# ✅ Print all results
for key, value in results.items():
    print(f"\n📦 Task: {key}")
    print(f"   Type: {type(value)}")
    if isinstance(value, dict):
        print(f"   Keys: {list(value.keys())[:10]}...")  # First 10 keys
        print(f"   Success: {value.get('success')}")
        print(f"   Reward: {value.get('cum_reward')}")
        
        # Check for Railway info
        if 'railway_verified' in value:
            print(f"   ✅ Railway info found!")
            print(f"   Railway verified: {value.get('railway_verified')}")
            print(f"   Railway reward: {value.get('railway_reward')}")
            print(f"   Leaderboard submitted: {value.get('leaderboard_submitted')}")
