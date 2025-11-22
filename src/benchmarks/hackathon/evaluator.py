import json
from typing import Dict, Any, Tuple
import asyncio
from urllib.parse import urljoin, urlparse
from rich.console import Console
from arena.browser import AgentBrowser
from arena.state import AgentState
from arena.result import ExperimentResult
from arena.evaluation import BaseEvaluator
import os
from typing import Optional
from deepdiff import DeepDiff
import jmespath
from rich import print

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5")


# ------------------- IndexedDB extractor (as provided) ------------------------
EXTRACT_SCRIPT = """
() => {
    return new Promise(async (resolve) => {
        const result = {};
        try {
            const databases = await indexedDB.databases();
            for (const {name, version} of databases) {
                const db = await new Promise((dbResolve, dbReject) => {
                    const request = indexedDB.open(name, version);
                    request.onsuccess = () => dbResolve(request.result);
                    request.onerror = () => dbReject(request.error);
                });
                result[name] = { version: version, stores: {} };
                for (const storeName of db.objectStoreNames) {
                    const transaction = db.transaction(storeName, 'readonly');
                    const store = transaction.objectStore(storeName);
                    const [keys, values] = await Promise.all([
                        new Promise((keyResolve, keyReject) => {
                            const req = store.getAllKeys();
                            req.onsuccess = () => keyResolve(req.result);
                            req.onerror = () => keyReject(req.error);
                        }),
                        new Promise((valResolve, valReject) => {
                            const req = store.getAll();
                            req.onsuccess = () => valResolve(req.result);
                            req.onerror = () => valReject(req.error);
                        })
                    ]);
                    result[name].stores[storeName] = keys.map((key, i) => ({
                        key: key,
                        value: values[i]
                    }));
                }
                db.close();
            }
            resolve(result);
        } catch (error) {
            resolve({ error: error.message, databases: {} });
        }
    });
}
"""


# ----------------------------- Eval helpers -----------------------------------
def eval_jmespath(
    eval_item: Dict[str, Any], deepdiff: Dict[str, Any]
) -> Tuple[bool, str]:
    query = eval_item.get("query", "")
    expected = eval_item.get("expected_value")
    try:
        actual = jmespath.search(query, deepdiff)
        ok = str(actual) == str(expected)
        return ok, (f"✓ {actual}" if ok else f"✗ expected={expected} got={actual}")
    except Exception as e:
        return False, f"✗ jmespath error: {e}"


async def eval_llm_yesno(prompt: str) -> str:
    """
    Call LLM; return "YES ..." or "NO ...".
    Simple direct call without retry wrapper.
    """
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI()
        resp = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"NO (LLM error: {e})"


async def eval_llm_response(
    eval_item: Dict[str, Any], agent_response: str
) -> Tuple[bool, str]:
    expected = eval_item.get("expected_value", "")
    if not agent_response:
        return False, "✗ no agent_response"
    prompt = f"""Does the actual answer approximately satisfy the expected criterion?

Be extremely lenient, say no only if the actual answer is clearly not related to the expected criterion.

Expected criterion: {expected}
Actual answer: {agent_response}

Respond with ONLY 'YES' or 'NO' followed by a brief explanation."""
    verdict = await eval_llm_yesno(prompt)
    passed = verdict.upper().startswith("YES")
    return passed, f"{'✓' if passed else '✗'} LLM: {verdict}"


async def eval_llm_diff(
    eval_item: Dict[str, Any], deepdiff: Dict[str, Any]
) -> Tuple[bool, str]:
    query = eval_item.get("query", "")
    expected = eval_item.get("expected_value", "")
    try:
        actual_value = jmespath.search(query, deepdiff)
    except Exception as e:
        return False, f"✗ jmespath error: {e}"
    if actual_value is None:
        return False, "✗ query returned None"
    prompt = f"""Does the actual value approximately satisfy the expected criterion?

Be extremely lenient, say no only if the actual value is clearly not related to the expected criterion.

Expected criterion: {expected}
Actual value: {json.dumps(actual_value, ensure_ascii=False)}

Respond with ONLY 'YES' or 'NO' followed by a brief explanation."""
    verdict = await eval_llm_yesno(prompt)
    passed = verdict.upper().startswith("YES")
    return passed, f"{'✓' if passed else '✗'} LLM: {verdict}"


async def run_evals(
    evals: list, deepdiff: Dict[str, Any], agent_response: str
) -> Tuple[int, int]:
    passed = failed = 0
    print("\n[bold]Running evals:[/bold]")
    for i, item in enumerate(evals or [], 1):
        etype = item.get("type")
        desc = item.get("description", f"eval {i}")
        print(f"{i}. {desc}   (type={etype})")
        if etype == "jmespath":
            ok, msg = eval_jmespath(item, deepdiff)
        elif etype == "llm_judge_response":
            ok, msg = await eval_llm_response(item, agent_response)
        elif etype == "llm_judge_diff":
            ok, msg = await eval_llm_diff(item, deepdiff)
        else:
            ok, msg = False, f"✗ unknown eval type: {etype}"
        print(f"   {msg}")
        passed += int(ok)
        failed += int(not ok)
    print(f"[bold]Summary:[/bold] {passed} passed, {failed} failed\n")
    return passed, failed

def compute_timetravel_time_taken(indexeddb_data: Dict[str, Any]) -> float:
    """
    Find *TimeTravelDB*, pull 'timetravel' store, locate metadata.snapshotIds,
    load first/last snapshot states, then calculate time taken.
    """
    if not indexeddb_data:
        raise ValueError("No indexeddb data provided")

    # Pick the DB whose name contains 'TimeTravelDB'
    db_name = next((k for k in indexeddb_data.keys() if "TimeTravelDB" in k), None)
    if not db_name:
        raise ValueError("No TimeTravelDB found")

    stores = indexeddb_data[db_name].get("stores", {})
    timetravel_store = stores.get("timetravel", [])
    if not isinstance(timetravel_store, list) or not timetravel_store:
        raise ValueError("No timetravel store found")

    # Find metadata entry with snapshotIds
    metadata_entry = next(
        (e for e in timetravel_store if "metadata" in str(e.get("key"))), None
    )
    if not metadata_entry:
        raise ValueError("No metadata entry found")

    try:
        metadata = json.loads(metadata_entry["value"])
        snapshot_ids = metadata["snapshotIds"]
    except Exception:
        raise ValueError("No snapshotIds found")

    if not snapshot_ids or len(snapshot_ids) < 2:
        raise ValueError("Not enough snapshotIds found")

    first_id, last_id = snapshot_ids[0], snapshot_ids[-1]

    def find_snapshot_entry(sid: str) -> Optional[Dict[str, Any]]:
        # try exact
        s = next((e for e in timetravel_store if e.get("key") == sid), None)
        if s:
            return s
        # try snapshot- prefix
        s = next(
            (e for e in timetravel_store if e.get("key") == f"snapshot-{sid}"), None
        )
        return s

    first_snapshot = find_snapshot_entry(first_id)
    last_snapshot = find_snapshot_entry(last_id)

    # fallback: positional first/last non-metadata
    if (not first_snapshot) or (not last_snapshot):
        snaps = [e for e in timetravel_store if "metadata" not in str(e.get("key"))]
        if len(snaps) >= 2:
            first_snapshot, last_snapshot = snaps[0], snaps[-1]
        else:
            raise ValueError("Not enough snapshots found")
        
    start_time = json.loads(first_snapshot["value"])['timestamp']
    end_time = json.loads(last_snapshot["value"])['timestamp']
    time_taken = end_time - start_time

    return time_taken/1000 # convert to seconds

def compute_timetravel_deepdiff(indexeddb_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find *TimeTravelDB*, pull 'timetravel' store, locate metadata.snapshotIds,
    load first/last snapshot states, then DeepDiff.
    """
    if not indexeddb_data:
        return {}

    # Pick the DB whose name contains 'TimeTravelDB'
    db_name = next((k for k in indexeddb_data.keys() if "TimeTravelDB" in k), None)
    if not db_name:
        return {}

    stores = indexeddb_data[db_name].get("stores", {})
    timetravel_store = stores.get("timetravel", [])
    if not isinstance(timetravel_store, list) or not timetravel_store:
        return {}

    # Find metadata entry with snapshotIds
    metadata_entry = next(
        (e for e in timetravel_store if "metadata" in str(e.get("key"))), None
    )
    if not metadata_entry:
        return {}

    try:
        metadata = json.loads(metadata_entry["value"])
        snapshot_ids = metadata["snapshotIds"]
    except Exception:
        return {}

    if not snapshot_ids or len(snapshot_ids) < 2:
        return {}

    first_id, last_id = snapshot_ids[0], snapshot_ids[-1]

    def find_snapshot_entry(sid: str) -> Optional[Dict[str, Any]]:
        # try exact
        s = next((e for e in timetravel_store if e.get("key") == sid), None)
        if s:
            return s
        # try snapshot- prefix
        s = next(
            (e for e in timetravel_store if e.get("key") == f"snapshot-{sid}"), None
        )
        return s

    first_snapshot = find_snapshot_entry(first_id)
    last_snapshot = find_snapshot_entry(last_id)

    # fallback: positional first/last non-metadata
    if (not first_snapshot) or (not last_snapshot):
        snaps = [e for e in timetravel_store if "metadata" not in str(e.get("key"))]
        if len(snaps) >= 2:
            first_snapshot, last_snapshot = snaps[0], snaps[-1]
        else:
            return {}

    try:
        first_state = json.loads(first_snapshot["value"])["state"]
        last_state = json.loads(last_snapshot["value"])["state"]
    except Exception:
        return {}
    
    diff = DeepDiff(first_state, last_state, ignore_order=True, verbose_level=2)
    diff_dict = diff.to_dict() if hasattr(diff, "to_dict") else dict(diff)

    # Clean non-JSON serializable objects from the diff
    def clean_dict(obj):
        if isinstance(obj, dict):
            return {k: clean_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_dict(item) for item in obj]
        elif isinstance(obj, type):
            return str(obj)
        else:
            return obj

    return clean_dict(diff_dict)


class HackathonEvaluator(BaseEvaluator):
    def __init__(
        self, browser: AgentBrowser, task_dict: Dict[str, Any], task_path: str = None
    ):
        self.browser = browser
        self.task_dict = task_dict
        self.task_path = task_path

    async def setup(self) -> Tuple[str, str]:
        # Get evals from task_dict directly (no need to read separate file)
        self.evals = self.task_dict.get("evals", [])

        # Get goal and URL from task_dict
        goal = self.task_dict.get("goal", "")
        url = self.task_dict.get("website", {}).get("url", "")

        if not url:
            raise ValueError("No URL found in task configuration")

        # Extract base URL and construct config URL
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        config_url = urljoin(
            base_url,
            f"/config?task_id={self.task_dict.get('id', 'unknown')}&latency=0&removePopup=true&hide_aria_labels=false",
        )
        # Navigate to config URL first, then to the actual task URL
        try:
            await self.browser.page.goto(config_url, wait_until="load")
        except Exception as e:
            print(f"Warning: Failed to navigate to config URL: {e}")

        await asyncio.sleep(2)

        try:
            await self.browser.page.goto(url, wait_until="load", timeout=20000)
        except Exception as e:
            print(f"Warning: Failed to navigate to task URL: {e}")

        await asyncio.sleep(1)

        # Replace the config URL in history to prevent go_back issues
        await self.browser.page.evaluate(
            "history.replaceState({}, '', window.location.href)"
        )

        return goal, url
    

    async def evaluate(self, state: AgentState) -> ExperimentResult:
        # Get the agent's final response from messages
        agent_response = self._extract_agent_response(state)

        indexeddb_data = await self.browser.page.evaluate(EXTRACT_SCRIPT)

        diff_dict = compute_timetravel_deepdiff(indexeddb_data)
        time_taken = compute_timetravel_time_taken(indexeddb_data)

        passed, failed = await run_evals(self.evals, diff_dict, agent_response)

        all_passed = failed == 0

        # Create enhanced result
        result = ExperimentResult(
            success=all_passed,
        )
        result.details = (
            {
                "task_id": self.task_dict.get("id", "unknown"),
                "goal": self.task_dict.get("goal", ""),
                "difficulty": self.task_dict.get("difficulty", "unknown"),
                "challenge_type": self.task_dict.get("challengeType", "unknown"),
                "total_criteria": len(self.evals),
                "passed_criteria": passed,
                "time_taken": time_taken,
            },
        )
        result.agent_response = agent_response

        console = Console()
        console.print(result)

        return result

    def _extract_agent_response(self, state: AgentState) -> str:
        """Extract the agent's final response from state messages"""
        if not state.messages:
            return ""

        # Look for the last agent response
        for msg in reversed(state.messages):
            if msg.get("role") in ["assistant", "agent"]:
                return str(msg.get("content", ""))

        return ""
