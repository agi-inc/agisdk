import json
import sys

# Verification script for Topwork task:
# Goal: Ensure both Ashley and Brandon were saved/favorited.
# Strategy:
# 1) Extract saved freelancer IDs from initialfinaldiff.added/updated.saved.savedFreelancerIds (support dict/list/string).
# 2) Derive target freelancer IDs by scanning jobs -> applications for freelancerId containing 'ashley' and 'brandon' (case-insensitive).
#    If not found, fallback to expected canonical IDs {'ashleycampbell', 'brandonmartinez'} based on platform conventions.
# 3) SUCCESS if at least one Ashley-ID and one Brandon-ID are present in the saved set; otherwise FAILURE.


def get(data, *keys, default=None):
    cur = data
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def collect_saved_ids(data):
    saved_ids = set()
    if not isinstance(data, dict):
        return saved_ids
    initialfinaldiff = data.get("initialfinaldiff", {})
    for section in ("added", "updated"):
        saved = get(initialfinaldiff, section, "saved", default={})
        saved_freelancers = None
        if isinstance(saved, dict):
            saved_freelancers = saved.get("savedFreelancerIds")
        # Process the saved_freelancers in different possible formats
        if isinstance(saved_freelancers, list):
            for v in saved_freelancers:
                if isinstance(v, str) and v.strip():
                    saved_ids.add(v.strip())
        elif isinstance(saved_freelancers, dict):
            for v in saved_freelancers.values():
                if isinstance(v, str) and v.strip():
                    saved_ids.add(v.strip())
        elif isinstance(saved_freelancers, str):
            if saved_freelancers.strip():
                saved_ids.add(saved_freelancers.strip())
    return saved_ids


def collect_target_ids(data):
    # Find freelancerIds containing 'ashley' and 'brandon' in applications
    initialfinaldiff = data.get("initialfinaldiff", {})
    added_jobs = get(initialfinaldiff, "added", "jobs", "jobs", default={}) or {}
    updated_jobs = get(initialfinaldiff, "updated", "jobs", "jobs", default={}) or {}

    def iter_jobs(jobs_obj):
        # jobs_obj can be a list-like dict with numeric keys
        if isinstance(jobs_obj, dict):
            for v in jobs_obj.values():
                if isinstance(v, dict):
                    yield v
        elif isinstance(jobs_obj, list):
            for v in jobs_obj:
                if isinstance(v, dict):
                    yield v

    ashley_ids = set()
    brandon_ids = set()

    for job in list(iter_jobs(added_jobs)) + list(iter_jobs(updated_jobs)):
        applications = job.get("applications", [])
        if isinstance(applications, dict):
            apps_iter = applications.values()
        else:
            apps_iter = applications
        for app in apps_iter:
            if not isinstance(app, dict):
                continue
            fid = app.get("freelancerId")
            if isinstance(fid, str) and fid:
                low = fid.lower()
                if "ashley" in low:
                    ashley_ids.add(fid)
                if "brandon" in low:
                    brandon_ids.add(fid)

    # Fallback to canonical IDs if none discovered from the page state
    if not ashley_ids:
        ashley_ids = {"ashleycampbell"}
    if not brandon_ids:
        brandon_ids = {"brandonmartinez"}
    return ashley_ids, brandon_ids


def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    saved_ids = collect_saved_ids(data)
    # If there are no saved IDs at all, it's a failure
    if not saved_ids:
        print("FAILURE")
        return

    ashley_ids, brandon_ids = collect_target_ids(data)

    saved_lower = {s.lower() for s in saved_ids}
    cond_ashley = any(a.lower() in saved_lower for a in ashley_ids)
    cond_brandon = any(b.lower() in saved_lower for b in brandon_ids)

    if cond_ashley and cond_brandon:
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
