import json
import sys


def load_json(path):
    with open(path) as f:
        return json.load(f)


def get_events(root):
    """Extract events from the differences section."""
    diffs = root.get("differences", {})
    if not isinstance(diffs, dict):
        return {}

    events_section = diffs.get("events", {})
    if not isinstance(events_section, dict):
        return {}

    added_events = events_section.get("added", {})
    updated_events = events_section.get("updated", {})

    # Combine added and updated events
    all_events = {}
    if isinstance(added_events, dict):
        all_events.update(added_events)
    if isinstance(updated_events, dict):
        all_events.update(updated_events)

    return all_events


def normalize_text(text):
    """Normalize text for comparison."""
    if not isinstance(text, str):
        return ""
    return "".join(ch for ch in text.lower() if ch.isalnum())


def check_gym_clothes_event(events):
    """Check if there's an event with 'gym' and 'clothes' in the title."""
    REQUIRED_KEYWORDS = ["gym", "clothes"]

    for _event_id, event in events.items():
        if not isinstance(event, dict):
            continue

        # Check title contains both "gym" and "clothes"
        title = event.get("title", "")
        normalized_title = normalize_text(title)

        if all(keyword in normalized_title for keyword in REQUIRED_KEYWORDS):
            return True

    return False


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

    # Extract events
    events = get_events(data)

    if not events:
        print("FAILURE")
        return

    # Check if gym clothes event exists
    if check_gym_clothes_event(events):
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
