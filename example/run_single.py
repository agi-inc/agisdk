import sys
from pathlib import Path

# Ensure the repository src/ directory is importable when running from examples/
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))
import os
from agisdk import REAL
import time

# Ray + uv expect to be invoked from the repository root so they see pyproject.toml.
if Path.cwd().resolve() != repo_root.resolve():
    raise SystemExit(
        "Run this script from the repository root so Ray can locate pyproject.toml,\n"
        "e.g. `python example/run_single.py`."
    )

# Hardcoded API keys
os.environ["OPENROUTER_API_KEY"] = "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"
os.environ["REAL_RUN_ID"] = "c7cd577f-c18b-4532-802f-4b5efc19bd22"

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
        run_id="c7cd577f-c18b-4532-802f-4b5efc19bd22",
        api_key="d424c804a5b7326b590ba1f59340f1718ff02e1afdf81626ccfb3376edcaaefc",
        run_name="OpenAI-GPT-5 2025-10-28",
        model_id_name="OpenAI-GPT-5",
        headless=True,
        leaderboard=True,   
        max_steps=35,
        num_workers=15,
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
