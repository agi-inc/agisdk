import json
import sys

# Strategy:
# - Load final_state_diff.json and inspect search.appliedDestination to ensure it targets "San Jose, Costa Rica" (case-insensitive, trimmed).
# - Confirm no booking attempt occurred: isBooking should be False, currentBooking should be None, and booking.errors should not contain any non-empty strings.
# - SUCCESS only if correct destination and no booking action; otherwise FAILURE.


def safe_get(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def normalize_str(s):
    if s is None:
        return None
    if not isinstance(s, str):
        s = str(s)
    return s.strip().lower()


try:
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

root = data.get("initialfinaldiff", {})
added = root.get("added", {}) or {}
updated = root.get("updated", {}) or {}

# Merge added and updated (updated wins)
merged = {}
for src in (added, updated):
    for k, v in src.items():
        merged[k] = v

search = merged.get("search", {}) if isinstance(merged.get("search", {}), dict) else {}
booking = merged.get("booking", {}) if isinstance(merged.get("booking", {}), dict) else {}

applied_dest = safe_get(search, "appliedDestination")

# Check destination matches San Jose, Costa Rica
dest_ok = normalize_str(applied_dest) == normalize_str("San Jose, Costa Rica")

# Detect booking attempts
is_booking = bool(safe_get(booking, "isBooking"))
current_booking = safe_get(booking, "currentBooking")
errors = safe_get(booking, "errors")

errors_nonempty = False
if isinstance(errors, dict):
    for val in errors.values():
        if isinstance(val, str):
            if val.strip() != "":
                errors_nonempty = True
                break
        elif val not in (None, ""):
            # any non-empty non-string indicates an error state
            errors_nonempty = True
            break

booking_attempted = is_booking or (current_booking is not None) or errors_nonempty

# Final decision
if dest_ok and not booking_attempted:
    print("SUCCESS")
else:
    print("FAILURE")
