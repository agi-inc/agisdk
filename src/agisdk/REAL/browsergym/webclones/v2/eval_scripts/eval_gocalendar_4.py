import json, sys

# Strategy:
# - Load final_state_diff.json and look for events added.
# - Succeed if there exists an added event starting at 2024-09-21T02:45:00Z and ending at 03:45:00Z
#   (allow presence/absence of millisecond precision), and whose location contains 'gym' (case-insensitive).
#   This corresponds to Sep 20, 7:45pm–8:45pm local. This also prevents empty events from passing.
# - Otherwise, fail.

def normalize_iso_z(ts):
    if not isinstance(ts, str):
        return ""
    # Remove milliseconds if present, ensure trailing 'Z'
    if ts.endswith('Z'):
        core = ts[:-1]
        if '.' in core:
            core = core.split('.')[0]
        return core + 'Z'
    # If no trailing Z, keep as-is (unlikely in provided data)
    if '.' in ts:
        return ts.split('.')[0]
    return ts

def main():
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    events_added = (
        data.get('differences', {})
            .get('events', {})
            .get('added', {})
    )

    target_start = '2024-09-21T02:45:00Z'
    target_end = '2024-09-21T03:45:00Z'

    success = False
    if isinstance(events_added, dict):
        for ev in events_added.values():
            start = normalize_iso_z(ev.get('start'))
            end = normalize_iso_z(ev.get('end'))
            location = ev.get('location') or ""

            # Require location to mention gym
            has_gym_location = 'gym' in location.lower()

            if start == target_start and end == target_end and has_gym_location:
                success = True
                break

    print("SUCCESS" if success else "FAILURE")

if __name__ == '__main__':
    main()
