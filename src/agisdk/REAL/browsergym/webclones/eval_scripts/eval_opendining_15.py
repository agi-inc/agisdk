import sys, json, re

def parse_time_to_minutes(tstr):
    if not isinstance(tstr, str):
        return None
    s = tstr.strip()
    # Pattern with optional minutes and AM/PM (e.g., "9 PM", "9:30 PM")
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*([APap][Mm])$", s)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) is not None else 0
        ampm = m.group(3).upper()
        if hour == 12:
            hour = 0 if ampm == 'AM' else 12
        else:
            if ampm == 'PM':
                hour += 12
        return hour * 60 + minute
    # 24-hour format fallback, e.g., "21:00"
    m2 = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if m2:
        hour = int(m2.group(1))
        minute = int(m2.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour * 60 + minute
    return None

def extract_booking(data):
    if not isinstance(data, dict):
        return None
    diff = data.get('initialfinaldiff', {})
    for section in ['added', 'updated']:
        sec = diff.get(section, {})
        if isinstance(sec, dict) and 'booking' in sec and isinstance(sec['booking'], dict):
            return sec['booking']
    # Fallback if stored elsewhere (unlikely)
    return None


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    booking = extract_booking(data)
    if not isinstance(booking, dict):
        print('FAILURE')
        return

    booking_details = booking.get('bookingDetails')
    has_details = isinstance(booking_details, dict) and len(booking_details) > 0
    if not has_details:
        # No concrete reserved place captured
        print('FAILURE')
        return

    # Gather candidate times from bookingDetails
    times = []
    for v in booking_details.values():
        if isinstance(v, dict):
            t = v.get('time')
            if t is not None:
                times.append(t)
    # As a cautious fallback, include top-level time only if details exist
    top_time = booking.get('time')
    if top_time is not None:
        times.append(top_time)

    # Parse and validate closeness to 9:00 PM (21:00)
    target = 21 * 60
    ok = False
    for t in times:
        mins = parse_time_to_minutes(t)
        if mins is None:
            continue
        if abs(mins - target) <= 30:
            ok = True
            break

    print('SUCCESS' if ok else 'FAILURE')

if __name__ == '__main__':
    # Strategy in code comments:
    # 1) Confirm a concrete reservation by requiring non-empty bookingDetails.
    # 2) Validate booked time within ±30 minutes of 9:00 PM using robust time parsing.
    main()
