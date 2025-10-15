import json
import sys

def get_nested(d, path, default=None):
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur

def has_nonempty(obj):
    if obj is None:
        return False
    if isinstance(obj, dict):
        return len(obj) > 0
    if isinstance(obj, list):
        return len(obj) > 0
    # Some structures might be nested under stringified indices; treat string/non-container as False
    return False

# Strategy in code:
# - Success is defined as the presence of at least one tour request created for a property.
# - Check multiple plausible locations and key variants for tour requests in the diff JSON.

def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    candidates = [
        get_nested(data, ["initialfinaldiff", "added", "tourRequests", "requestTourList"]),
        get_nested(data, ["initialfinaldiff", "added", "requestTours", "requestTourList"]),
        get_nested(data, ["differences", "tourRequests", "added"]),
        get_nested(data, ["differences", "requestTours", "added"]),
    ]

    success = any(has_nonempty(c) for c in candidates)

    print("SUCCESS" if success else "FAILURE")

if __name__ == "__main__":
    main()
