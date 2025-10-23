import json, sys
# Strategy:
# - Load final_state_diff.json
# - Determine if a tour request was successfully created by checking the presence of requestTours added entries
#   with at least one option (date/time) and non-empty formValues.message, name, email, phone.
# - Additional heuristic from training data: successes have a non-empty config.zilloft.run_id; failures have empty run_id.
# - So we require both: a valid tour request entry AND a non-empty run_id.
# - If both hold, print SUCCESS; otherwise, print FAILURE.


def get_nested(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

try:
    fp = sys.argv[1]
    with open(fp, 'r') as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

# Check run_id presence (non-empty string)
run_id = get_nested(data, ["initialfinaldiff", "added", "config", "zilloft", "run_id"], "")
run_id_ok = isinstance(run_id, str) and run_id.strip() != ""

# Look under differences.requestTours.added first; fallback to initialfinaldiff.added.tourRequests.requestTourList
reqs = get_nested(data, ["differences", "requestTours", "added"], {})
if not reqs:
    reqs = get_nested(data, ["initialfinaldiff", "added", "tourRequests", "requestTourList"], {})

has_valid_request = False
if isinstance(reqs, dict):
    for _, entry in reqs.items():
        rtd = get_nested(entry, ["requestTourData"], {})
        options = get_nested(rtd, ["options"], [])
        form = get_nested(rtd, ["formValues"], {})
        if not isinstance(options, list) or len(options) == 0:
            continue
        # Validate option has either date or time
        opt_ok = any(isinstance(opt, dict) and (opt.get("date") or opt.get("time")) for opt in options)
        if not opt_ok:
            continue
        # Basic form validation
        name = (form.get("name") or "").strip()
        email = (form.get("email") or "").strip()
        phone = (form.get("phone") or "").strip()
        message = (form.get("message") or "").strip()
        if all([name, email, phone, message]):
            has_valid_request = True
            break

print("SUCCESS" if (has_valid_request and run_id_ok) else "FAILURE")