import sys, json, re

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

# Normalize time strings and check if they represent 7:30 in the evening window
# Accept variants like "7:30 PM", "7:30PM", "730pm", "19:30", "19:30:00".
def is_time_730_evening(t):
    if t is None:
        return False
    s = str(t).strip().lower()
    # Remove all spaces for easier matching
    s = re.sub(r"\s+", "", s)
    # Common 24h forms
    if s.startswith('19:30') or '19:30' in s or s.startswith('1930') or '1930' in s:
        return True
    # Check 12h forms around 7:30; ensure not AM
    if ('7:30' in s or '730' in s) and 'am' not in s:
        # If no am/pm present, assume it's acceptable as evening time window
        return True
    return False

# Retrieve booking object from added or updated sections

def get_booking(data):
    if not isinstance(data, dict):
        return None
    init = data.get('initialfinaldiff') or {}
    for section_name in ['added', 'updated']:
        section = init.get(section_name)
        if isinstance(section, dict) and isinstance(section.get('booking'), dict):
            return section.get('booking')
    return None

# Extract list of booking detail entries from bookingDetails which may be a dict or list

def iter_booking_details(booking):
    bd = booking.get('bookingDetails')
    if not bd:
        return []
    if isinstance(bd, dict):
        return list(bd.values())
    if isinstance(bd, list):
        return bd
    return []


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    data = load_json(path)
    if not data:
        print('FAILURE')
        return

    booking = get_booking(data)
    if not isinstance(booking, dict):
        print('FAILURE')
        return

    # If still loading, treat as failure
    if booking.get('loading') is True:
        print('FAILURE')
        return

    details = iter_booking_details(booking)
    if not details:
        print('FAILURE')
        return

    success = False
    for entry in details:
        if not isinstance(entry, dict):
            continue
        t = entry.get('time')
        if is_time_730_evening(t):
            success = True
            break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
