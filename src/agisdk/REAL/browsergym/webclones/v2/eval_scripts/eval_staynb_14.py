import json
import sys
from datetime import date, datetime, timedelta

# Strategy:
# - Extract destination, dates, guests, filters, and UI state from initialfinaldiff.
# - Success if:
#   * destination is "Rome, Italy" (case-insensitive)
#   * total guests == 4
#   * removePopup is True
#   * dates match first Fri-Sun of January for the year OR match the alt 3->5 pattern
#   * appliedFilters contains bedrooms >= 2
#   * appliedFilters.amenities contains wifi (robust matching)
# - Resilient to missing fields and ISO date formats with 'Z'.


def get_in(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def parse_iso_date(s):
    if not s or not isinstance(s, str):
        return None
    try:
        # Accept strings ending with Z (UTC) or with timezone offset or naive ISO.
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
        return dt.date()
    except Exception:
        # As a fallback, try splitting date portion
        try:
            return datetime.fromisoformat(s.split("T")[0]).date()
        except Exception:
            return None


def first_jan_weekend(year):
    jan1 = date(year, 1, 1)
    # Monday=0 ... Sunday=6; Friday=4
    offset = (4 - jan1.weekday()) % 7
    first_friday = jan1 + timedelta(days=offset)
    first_sunday = first_friday + timedelta(days=2)
    return first_friday, first_sunday


def extract_total_guests(search):
    # Prefer appliedGuestCounts (Adults + Children). Fall back to recentSearches 'guests' string.
    guest_counts = get_in(search, ["appliedGuestCounts"], {}) or {}
    adults = guest_counts.get("Adults", 0) or 0
    children = guest_counts.get("Children", 0) or 0
    total = 0
    try:
        total = int(adults) + int(children)
    except Exception:
        total = 0

    if total == 0:
        # fallback to string like "4 Guests"
        gstr = get_in(search, ["recentSearches", "0", "guests"])
        if isinstance(gstr, str):
            try:
                total = int(gstr.strip().split()[0])
            except Exception:
                total = 0
    return total


def normalize_amenity_value(a):
    # Convert a single amenity entry into a lowercase string to match wifi variants.
    if a is None:
        return ""
    # If amenity is a dict with name/key fields, try to extract a human-readable value
    if isinstance(a, dict):
        for key in ("name", "title", "label"):
            if key in a and isinstance(a[key], str):
                return a[key].strip().lower()
        # Otherwise, stringify the dict
        return json.dumps(a).strip().lower()
    # If amenity is a list/tuple, join values
    if isinstance(a, (list, tuple, set)):
        return " ".join(map(str, a)).strip().lower()
    # Fallback: string conversion
    return str(a).strip().lower()


def has_wifi_in_amenities(amenities):
    # Accept multiple formats: list of strings, list of dicts, single string, etc.
    if not amenities:
        return False
    # If amenities is a single string, check it directly
    if isinstance(amenities, str):
        candidates = [amenities]
    else:
        # Otherwise, try to iterate
        try:
            candidates = list(amenities)
        except Exception:
            candidates = [amenities]
    for a in candidates:
        norm = normalize_amenity_value(a)
        # remove hyphens and spaces to match wifi/wi-fi/wi fi variants
        compact = norm.replace("-", "").replace(" ", "")
        if "wifi" in compact:
            return True
        # also accept common synonyms
        if "wirelessinternet" in compact or "wireless" == compact:
            return True
    return False


def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    fp = sys.argv[1]
    try:
        with open(fp) as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    root = data.get("initialfinaldiff", {})
    added = root.get("added", {}) if isinstance(root.get("added", {}), dict) else {}
    updated = root.get("updated", {}) if isinstance(root.get("updated", {}), dict) else {}

    search = added.get("search") or updated.get("search") or {}

    # Destination
    dest = get_in(search, ["appliedDestination"]) or get_in(
        search, ["recentSearches", "0", "destination"]
    )
    is_rome = isinstance(dest, str) and dest.strip().lower() == "rome, italy"

    # Dates
    start_iso = get_in(search, ["appliedDates", "startDate"]) or get_in(
        search, ["recentSearches", "0", "dates", "startDate"]
    )
    end_iso = get_in(search, ["appliedDates", "endDate"]) or get_in(
        search, ["recentSearches", "0", "dates", "endDate"]
    )
    start_date = parse_iso_date(start_iso)
    end_date = parse_iso_date(end_iso)

    is_first_weekend = False
    alt_three_to_five = False
    if start_date and end_date:
        try:
            ff, fsun = first_jan_weekend(start_date.year)
            is_first_weekend = start_date == ff and end_date == fsun
        except Exception:
            is_first_weekend = False
        alt_three_to_five = (
            (end_date - start_date).days == 2 and start_date.day == 3 and end_date.day == 5
        )

    # Guests
    total_guests = extract_total_guests(search)

    # UI state (used to ensure task not blocked)
    config = added.get("config") or updated.get("config") or {}
    remove_popup = get_in(config, ["staynb", "removePopup"], True)

    # Filters: bedrooms and amenities
    applied_filters = get_in(search, ["appliedFilters"]) or {}
    try:
        bedrooms = int(applied_filters.get("bedrooms", 0))
    except Exception:
        bedrooms = 0

    amenities = applied_filters.get("amenities", []) or []
    wifi_ok = has_wifi_in_amenities(amenities)
    bedrooms_ok = bedrooms >= 2

    # Final success logic:
    success = (
        is_rome
        and total_guests == 4
        and remove_popup
        and (is_first_weekend or alt_three_to_five)
        and bedrooms_ok
        and wifi_ok
    )

    print("SUCCESS" if success else "FAILURE")


if __name__ == "__main__":
    main()
