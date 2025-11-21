import json
import sys

# Strategy:
# - Load final_state_diff.json and inspect search.applied* fields.
# - Success if destination == 'Provence, France', dates cover 2024-08-01 to 2024-08-04, and guest counts are Adults=2 and Children=1.
# - Prefer applied* fields; if missing, fall back to recentSearches[0] checks.
# - If amenities is empty array, consider it a filter not applied (FAILURE).


def get_nested(d, keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def norm_date(val):
    if not isinstance(val, str):
        return None
    # Take date part if ISO datetime provided
    if "T" in val:
        return val.split("T")[0]
    return val


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

search = added.get("search") or updated.get("search") or {}

# Check using applied* fields
applied_dest = get_nested(search, ["appliedDestination"], "") or ""
applied_start = norm_date(get_nested(search, ["appliedDates", "startDate"]))
applied_end = norm_date(get_nested(search, ["appliedDates", "endDate"]))

applied_adults = get_nested(search, ["appliedGuestCounts", "Adults"])
applied_children = get_nested(search, ["appliedGuestCounts", "Children"])
applied_amenities = get_nested(search, ["appliedFilters", "amenities"])

# Normalize numeric guest counts if strings
try:
    if isinstance(applied_adults, str):
        applied_adults = int(applied_adults)
except Exception:
    pass
try:
    if isinstance(applied_children, str):
        applied_children = int(applied_children)
except Exception:
    pass

# Check if amenities is an empty list (filters not applied)
has_required_filters = applied_amenities is None or len(applied_amenities) > 0

applied_ok = (
    applied_dest == "Provence, France"
    and applied_start == "2024-08-01"
    and applied_end == "2024-08-04"
    and applied_adults == 2
    and applied_children == 1
    and has_required_filters
)

# Fallback: recentSearches[0]
rs = get_nested(search, ["recentSearches", "0"]) or {}
rs_dest = rs.get("destination")
rs_start = norm_date(get_nested(rs, ["dates", "startDate"]))
rs_end = norm_date(get_nested(rs, ["dates", "endDate"]))
rs_guests = rs.get("guests") or ""

# Interpret guests like "3 Guests" as sum; for our case, 2 Adults + 1 Child = 3 guests
rs_guest_count = None
if isinstance(rs_guests, str):
    parts = rs_guests.strip().split()
    if parts and parts[0].isdigit():
        try:
            rs_guest_count = int(parts[0])
        except Exception:
            rs_guest_count = None

recent_ok = (
    rs_dest == "Provence, France"
    and rs_start == "2024-08-01"
    and rs_end == "2024-08-04"
    and rs_guest_count == 3
)

# Prefer applied fields; only if applied not available (e.g., empty destination) consider recentSearches
success = False
if applied_dest:
    success = applied_ok
else:
    success = recent_ok

print("SUCCESS" if success else "FAILURE")
