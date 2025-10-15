import sys, json
from datetime import datetime, date

def parse_dt(val):
    if not isinstance(val, str):
        return None
    try:
        # Ensure ISO 8601 compatibility by handling trailing 'Z'
        val2 = val.replace('Z', '+00:00')
        return datetime.fromisoformat(val2)
    except Exception:
        return None

def has_30min_notification(calendar_options):
    if not isinstance(calendar_options, dict):
        return False
    notif = calendar_options.get('notification')
    def match_str(s):
        s2 = str(s).lower()
        return ('30' in s2) and ('minute' in s2)
    if isinstance(notif, list):
        return any(match_str(n) for n in notif)
    elif isinstance(notif, str):
        return match_str(notif)
    else:
        return False

def event_matches(e):
    if not isinstance(e, dict):
        return False

    title = str(e.get('title', '') or '').strip()
    description = str(e.get('description', '') or '')
    location = str(e.get('location', '') or '')

    # Title should be present and include 'orientation'
    if not title or title.lower() == '(no title)':
        return False
    if 'orientation' not in title.lower():
        return False

    # Location context should include 'Santa Cruz' in title/description/location
    combined_text = ' '.join([title, description, location]).lower()
    if 'santa cruz' not in combined_text:
        return False

    # All-day should not be true
    if e.get('allDay') is True:
        return False

    start_raw = e.get('start')
    end_raw = e.get('end')
    sdt = parse_dt(start_raw)
    edt = parse_dt(end_raw)
    if not sdt or not edt:
        return False

    # Date must be September 24, 2024 (UTC date)
    target_date = date(2024, 9, 24)
    if sdt.date() != target_date:
        return False

    # Duration must be exactly 1 hour (tolerance of 1 second)
    dur_seconds = (edt - sdt).total_seconds()
    if abs(dur_seconds - 3600) > 1:
        return False

    # Must have a 30-minute-before notification
    calendar_options = e.get('calendarOptions', {})
    if not has_30min_notification(calendar_options):
        return False

    return True


def main():
    try:
        path = sys.argv[1]
    except IndexError:
        print('FAILURE')
        return

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    differences = (data or {}).get('differences', {})
    events_diff = differences.get('events', {})
    candidates = []
    for k in ['added', 'updated']:
        d = events_diff.get(k) or {}
        if isinstance(d, dict):
            for _id, ev in d.items():
                candidates.append(ev)

    success = any(event_matches(ev) for ev in candidates)
    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
