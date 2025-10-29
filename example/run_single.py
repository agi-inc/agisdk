import sys
from pathlib import Path

# Ensure the repository src/ directory is importable when running from examples/
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))
import os
import time

# Enforce running from the repo root using the existing `.venv`.
if Path.cwd().resolve() != repo_root:
    raise SystemExit(
        "Run this script from the repository root inside the existing `.venv`,\n"
        "e.g. `source .venv/bin/activate && python example/run_single.py`."
    )

from agisdk import REAL

# Hardcoded API keys
os.environ["OPENROUTER_API_KEY"] =  "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"
os.environ["REAL_RUN_ID"] = "ad994b7d-1e82-402c-9681-66c95fb116f2"

# OpenRouter models to test
models_to_test = [
    "openrouter/openai/gpt-5",

]

print("🚀 Testing OpenRouter Models")
print("=" * 50)

for i, model in enumerate(models_to_test, 1):
    print(f"\n[{i}/{len(models_to_test)}] Testing: {model}")
    print("-" * 50)

    start_time = time.perf_counter()
    harness = REAL.harness(
        model=model,
        task_version="v2",
        run_id="ad994b7d-1e82-402c-9681-66c95fb116f2",
        api_key="8a427b5b4dd458b684056042d8c4a61309bdf2607071fe70cd9a1658cdac8507",
        headless=True,
        leaderboard=True,
        max_steps=35,
        num_workers=15
    )

    try:
        result = harness.run()
        elapsed = time.perf_counter() - start_time
        print(f"✅ Completed in {elapsed:.2f}s")
        print(f"📊 Result: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    # Small delay between tests
    time.sleep(2)

print(f"\n🎉 All {len(models_to_test)} models tested!")
