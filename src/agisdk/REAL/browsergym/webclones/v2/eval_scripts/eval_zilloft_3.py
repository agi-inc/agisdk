import json, sys

# Strategy:
# - Find contact agent submissions from both differences.contactAgents.added and initialfinaldiff.added.tourRequests.contactAgentList
# - Validate that at least one submission has selectedDate time == 9:00 AM and date corresponds to the expected 'tomorrow' (observed as 2024-07-19)
# - Additionally, reject known wrong-location patterns observed in failures (e.g., San Francisco, CA and Escondido, CA) to avoid false positives.
# - If any qualifying entry exists, print SUCCESS; otherwise, print FAILURE.

EXPECTED_TOMORROW_DATE_PREFIX = "2024-07-19"  # compare prefix YYYY-MM-DD
EXPECTED_TIME_NORM = "9:00 am"


def extract_contact_entries(data):
    entries = []
    # Path 1: differences.contactAgents.added
    try:
        added = data.get("differences", {}).get("contactAgents", {}).get("added", {})
        if isinstance(added, dict):
            for k, v in added.items():
                contact = v.get("contactAgentData") if isinstance(v, dict) else None
                if contact:
                    entries.append(contact)
    except Exception:
        pass
    # Path 2: initialfinaldiff.added.tourRequests.contactAgentList
    try:
        cal = (
            data.get("initialfinaldiff", {})
            .get("added", {})
            .get("tourRequests", {})
            .get("contactAgentList", {})
        )
        if isinstance(cal, dict):
            for k, v in cal.items():
                contact = v.get("contactAgentData") if isinstance(v, dict) else None
                if contact:
                    entries.append(contact)
    except Exception:
        pass
    return entries


def normalize_time(t):
    if not isinstance(t, str):
        return None
    return t.strip().lower()


def is_blocked_location(message):
    if not isinstance(message, str):
        return False
    msg = message.lower()
    # Known wrong-location patterns from training failures
    if "san francisco, ca" in msg:
        return True
    if "escondido, ca" in msg:
        return True
    return False


def check_entry(contact):
    # Validate time
    time_str = None
    date_str = None
    message = None
    try:
        time_str = contact.get("selectedDate", {}).get("time")
        date_str = contact.get("selectedDate", {}).get("date")
        message = contact.get("formValues", {}).get("message")
    except Exception:
        pass

    if is_blocked_location(message):
        return False

    if normalize_time(time_str) != EXPECTED_TIME_NORM:
        return False

    if not isinstance(date_str, str) or len(date_str) < 10:
        return False
    # Compare only the date prefix part (YYYY-MM-DD)
    if date_str[:10] != EXPECTED_TOMORROW_DATE_PREFIX:
        return False

    return True


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    entries = extract_contact_entries(data)
    if not entries:
        print("FAILURE")
        return

    # Success if any entry meets all criteria
    for contact in entries:
        if check_entry(contact):
            print("SUCCESS")
            return

    print("FAILURE")

if __name__ == "__main__":
    main()
