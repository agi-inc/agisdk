import json, sys

def main():
    # Strategy: Confirm an added calendar event matches the user's request:
    # - Title indicates "Math Camp"
    # - All-day event
    # - Location includes "Sunnyvale"
    # - Start date 2024-07-21 and end date 2024-07-27
    # If any added event satisfies all conditions, print SUCCESS; otherwise, FAILURE.

    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    diffs = data.get('differences', {})
    events = diffs.get('events', {})
    added = events.get('added', {})
    if not isinstance(added, dict):
        added = {}

    target_start = "2024-07-21"
    target_end = "2024-07-27"

    def norm(s):
        return (s or '').strip().lower()

    success = False

    for _id, e in added.items():
        if not isinstance(e, dict):
            continue
        title = norm(e.get('title'))
        start = e.get('start') or ''
        end = e.get('end') or ''
        start_date = start[:10]
        end_date = end[:10]
        all_day = e.get('allDay') is True
        location = norm(e.get('location'))

        # Title must clearly indicate Math Camp
        title_ok = (title == 'math camp') or ('math' in title and 'camp' in title)
        # Location must include Sunnyvale
        location_ok = 'sunnyvale' in location
        # Dates must match the requested span
        dates_ok = (start_date == target_start and end_date == target_end)

        if title_ok and location_ok and all_day and dates_ok:
            success = True
            break

    print("SUCCESS" if success else "FAILURE")

if __name__ == '__main__':
    main()