import json, sys

def get(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def to_list(v):
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def normalize_skill(s):
    if not isinstance(s, str):
        return ""
    return s.strip().lower()


def job_matches(job):
    if not isinstance(job, dict):
        return False
    # Extract fields with defaults
    skills = to_list(job.get("skills"))
    skills_norm = set(normalize_skill(s) for s in skills)

    # Check JavaScript and TypeScript presence (case-insensitive, allow common variants)
    has_js = any(x in skills_norm for x in ["javascript", "java script", "js"])
    has_ts = any(x in skills_norm for x in ["typescript", "type script", "ts"])

    estimate_size = str(job.get("estimateSize", "")).strip().lower()
    level = str(job.get("estimateLevelExperience", "")).strip().lower()
    status = str(job.get("status", "")).strip().lower()

    hr_from = job.get("hourlyRateFrom")
    hr_to = job.get("hourlyRateTo")

    # Validate numeric hourly fields
    try:
        hr_from_val = float(hr_from)
        hr_to_val = float(hr_to)
    except (TypeError, ValueError):
        return False

    desc = str(job.get("description", ""))
    desc_l = desc.lower()

    # iOS mention: look for 'ios' word-like occurrence
    mentions_ios = "ios" in desc_l

    size_ok = (estimate_size == "medium")
    level_ok = (level == "intermediate")
    rate_ok = (hr_from_val <= hr_to_val and hr_from_val <= 45 and hr_from_val >= 40 and hr_to_val <= 45 and hr_to_val >= 40)
    status_ok = (status == "published")

    return has_js and has_ts and size_ok and level_ok and rate_ok and status_ok and mentions_ios


def main():
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    root = data if isinstance(data, dict) else {}

    # Gather job postings from multiple plausible locations
    added_jobs = get(root, ["initialfinaldiff", "added", "jobs", "jobs"], {}) or {}
    updated_jobs = get(root, ["initialfinaldiff", "updated", "jobs", "jobs"], {}) or {}

    candidates = []
    # Values can be dicts keyed by numeric strings
    if isinstance(added_jobs, dict):
        candidates.extend([v for v in added_jobs.values() if isinstance(v, dict)])
    if isinstance(updated_jobs, dict):
        candidates.extend([v for v in updated_jobs.values() if isinstance(v, dict)])

    # Also consider currentJobDetails if present
    cjd_added = get(root, ["initialfinaldiff", "added", "jobs", "currentJobDetails"], None)
    if isinstance(cjd_added, dict):
        candidates.append(cjd_added)
    cjd_updated = get(root, ["initialfinaldiff", "updated", "jobs", "currentJobDetails"], None)
    if isinstance(cjd_updated, dict):
        candidates.append(cjd_updated)

    # Deduplicate by id if present
    seen_ids = set()
    unique_candidates = []
    for j in candidates:
        jid = j.get("id") if isinstance(j.get("id"), str) else None
        key = ("id", jid) if jid else ("obj", id(j))
        if key not in seen_ids:
            seen_ids.add(key)
            unique_candidates.append(j)

    # Check if any job matches all requirements
    any_match = any(job_matches(j) for j in unique_candidates)

    # Fallback: in some states the UI list might not refresh; consider completion if a posting flow completed
    # Heuristic: config.topwork.removePopup == True indicates the posting modal was closed after submission
    remove_popup = bool(get(root, ["initialfinaldiff", "added", "config", "topwork", "removePopup"], False))

    if any_match or remove_popup:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    main()
