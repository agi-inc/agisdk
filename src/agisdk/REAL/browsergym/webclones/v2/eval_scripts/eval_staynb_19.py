import json
import sys


def load_json(path):
    with open(path) as f:
        return json.load(f)


def get_from_sections(root, key):
    """Extract data from various sections of the state diff."""
    initial = root.get("initialfinaldiff", {})
    for section in ("added", "updated"):
        sec = initial.get(section)
        if isinstance(sec, dict) and key in sec:
            return sec.get(key)
    if key in root:
        return root.get(key)
    diffs = root.get("differences", {})
    if isinstance(diffs, dict) and key in diffs:
        return diffs.get(key)
    return None


def normalize_text(text):
    """Normalize text for comparison."""
    if not isinstance(text, str):
        return ""
    return "".join(ch for ch in text.lower() if ch.isalnum())


def parse_date(date_str):
    """Extract date portion from ISO datetime string."""
    if not isinstance(date_str, str):
        return None
    return date_str.split("T")[0] if "T" in date_str else date_str.split(" ")[0]


def check_search_criteria(search):
    """Check if search matches Vancouver Canada, dates Nov 15-18, and 5 guests."""
    if not isinstance(search, dict):
        return False

    # Check destination is Vancouver, Canada
    destination = search.get("appliedDestination", "")
    normalized_dest = normalize_text(destination)

    # Check for both "vancouver" and "canada" in the destination
    if "vancouver" not in normalized_dest or "canada" not in normalized_dest:
        return False

    # Check dates
    applied_dates = search.get("appliedDates", {})
    if not isinstance(applied_dates, dict):
        return False

    start_date = parse_date(applied_dates.get("startDate"))
    end_date = parse_date(applied_dates.get("endDate"))

    if start_date != "2024-11-15" or end_date != "2024-11-18":
        return False

    # Check guest count totals 5
    guest_counts = search.get("appliedGuestCounts", {})
    if not isinstance(guest_counts, dict):
        return False

    total_guests = (
        guest_counts.get("Adults", 0)
        + guest_counts.get("Children", 0)
        + guest_counts.get("Infants", 0)
        + guest_counts.get("Pets", 0)
    )

    if total_guests != 5:
        return False

    return True


def main():
    try:
        path = sys.argv[1]
    except IndexError:
        print("FAILURE")
        return

    try:
        data = load_json(path)
    except Exception:
        print("FAILURE")
        return

    # Extract search data
    search = get_from_sections(data, "search")

    if not search:
        print("FAILURE")
        return

    # Check if search criteria matches
    if check_search_criteria(search):
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
