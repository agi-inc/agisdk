import json, sys

def get_nested(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

# Determine if an entry looks like a real tour request
# We require: an id string and requestTourData containing either non-empty options list or non-empty formValues dict
# Strategy: Check both potential locations observed in training data:
# 1) differences.requestTours.added
# 2) initialfinaldiff.added.tourRequests.requestTourList

def is_valid_tour_request(entry):
    if not isinstance(entry, dict):
        return False
    entry_id = entry.get("id")
    if not isinstance(entry_id, str) or not entry_id.strip():
        return False
    rtd = entry.get("requestTourData")
    if not isinstance(rtd, dict):
        return False
    options = rtd.get("options")
    has_options = isinstance(options, list) and len(options) > 0
    form_vals = rtd.get("formValues")
    has_form = isinstance(form_vals, dict) and len(form_vals) > 0
    share = rtd.get("shareInfoDetails")
    has_share = isinstance(share, dict) and len(share) > 0
    return has_options or has_form or has_share


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    # Collect potential tour requests from both observed locations
    candidates = []

    added_req_tours = get_nested(data, ["differences", "requestTours", "added"], {})
    if isinstance(added_req_tours, dict):
        candidates.extend(list(added_req_tours.values()))

    initial_req_list = get_nested(data, ["initialfinaldiff", "added", "tourRequests", "requestTourList"], {})
    if isinstance(initial_req_list, dict):
        candidates.extend(list(initial_req_list.values()))

    # Validate any candidate
    success = any(is_valid_tour_request(c) for c in candidates)

    print("SUCCESS" if success else "FAILURE")

if __name__ == "__main__":
    main()
