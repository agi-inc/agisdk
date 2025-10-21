import sys, json

def extract(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

# Strategy in code:
# The task appears successful when a tour request is created for a property.
# We check two canonical locations in the final_state_diff: 
# 1) differences.requestTours.added (normalized diff)
# 2) initialfinaldiff.added.tourRequests.requestTourList (full snapshot)
# We validate entries by ensuring they contain an 'id' and 'requestTourData'.

def has_valid_tour_entry(entry):
    if not isinstance(entry, dict):
        return False
    # Require an id and requestTourData with at least formValues or options for robustness
    if not entry.get('id'):
        return False
    rtd = entry.get('requestTourData')
    if not isinstance(rtd, dict):
        return False
    if not (isinstance(rtd.get('formValues'), dict) or isinstance(rtd.get('options'), list)):
        return False
    return True


def detect_tour_request(data):
    # Check differences.requestTours.added
    added = extract(data, ["differences", "requestTours", "added"], {})
    if isinstance(added, dict) and added:
        for k, v in added.items():
            if has_valid_tour_entry(v):
                return True
    # Check initialfinaldiff.added.tourRequests.requestTourList
    req_list = extract(data, ["initialfinaldiff", "added", "tourRequests", "requestTourList"], {})
    if isinstance(req_list, dict) and req_list:
        for k, v in req_list.items():
            # Sometimes the value may be nested directly as entry
            if has_valid_tour_entry(v):
                return True
    return False


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    success = detect_tour_request(data)
    print("SUCCESS" if success else "FAILURE")

if __name__ == "__main__":
    main()
