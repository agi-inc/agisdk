import json
import sys


def get_nested(d, keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


# Strategy in code:
# - Consider the task successful if at least one tour request was added.
# - Verify presence in either differences.requestTours.added or initialfinaldiff.added.tourRequests.requestTourList with reasonable structure (requestTourData).


def has_valid_request(entry):
    if not isinstance(entry, dict):
        return False
    # Check for id and requestTourData presence
    rtd = entry.get("requestTourData")
    if isinstance(rtd, dict):
        # At least one of formValues/options/message typically exists
        fv = rtd.get("formValues")
        opts = rtd.get("options")
        if isinstance(fv, dict) or isinstance(opts, list):
            return True
    return False


try:
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)

    found_ids = set()
    success = False

    # Check differences.requestTours.added
    diff_added = get_nested(data, ["differences", "requestTours", "added"], {})
    if isinstance(diff_added, dict):
        for _key, entry in diff_added.items():
            if has_valid_request(entry):
                eid = entry.get("id")
                if eid:
                    found_ids.add(eid)
                success = True
                break  # At least one is enough

    # If not found yet, check initialfinaldiff.added.tourRequests.requestTourList
    if not success:
        req_list = get_nested(
            data, ["initialfinaldiff", "added", "tourRequests", "requestTourList"], {}
        )
        if isinstance(req_list, dict):
            for _key, entry in req_list.items():
                if has_valid_request(entry):
                    eid = entry.get("id")
                    if eid and eid not in found_ids:
                        success = True
                        break

    print("SUCCESS" if success else "FAILURE")
except Exception:
    # On any parsing or runtime error, default to FAILURE
    print("FAILURE")
