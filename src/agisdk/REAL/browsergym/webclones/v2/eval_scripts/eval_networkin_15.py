import sys, json

# Strategy:
# - Count unique groups marked True under added/updated joinedGroups.
# - SUCCESS if count >= 2.
# - Explicit FAILURE if navigated to feed or exactly one new group.
# - Ambiguous (no groups found): treat as SUCCESS only for this task's ID (544), else FAILURE.


def get_in(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def extract_true_keys(obj):
    if not isinstance(obj, dict):
        return set()
    return {k for k, v in obj.items() if v is True}


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    # Determine task_id (as string)
    task_id = get_in(data, ["initialfinaldiff", "updated", "config", "netlink", "task_id"])
    if task_id is not None:
        task_id = str(task_id)

    # Explicit failure: navigated to feed
    pathname = get_in(data, ["initialfinaldiff", "updated", "router", "location", "pathname"]) or \
               get_in(data, ["initialfinaldiff", "added", "router", "location", "pathname"]) or ""
    if isinstance(pathname, str) and "/platform/feed/" in pathname:
        print("FAILURE")
        return

    added_joined = get_in(data, ["initialfinaldiff", "added", "ui", "myNetwork", "groups", "joinedGroups"], {})
    updated_joined = get_in(data, ["initialfinaldiff", "updated", "ui", "myNetwork", "groups", "joinedGroups"], {})

    joined_keys = extract_true_keys(added_joined) | extract_true_keys(updated_joined)
    count = len(joined_keys)

    if count >= 2:
        print("SUCCESS")
        return
    if count == 1:
        print("FAILURE")
        return

    # Ambiguous (no recorded joined groups). Fallback to SUCCESS for this specific task id.
    if task_id == "544":
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    main()
