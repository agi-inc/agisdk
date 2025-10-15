import sys, json

# Verification script for calendar task
# Strategy:
# - Look for an added event matching: title/description indicates workout/gym, start date is Sept 20, time 19:45-20:45, and recurrence set to weekdays (Mon-Fri).
# - Robustly detect recurrence across common fields (recurrence/rrule/daysOfWeek/repeat strings). Require M-F present and no weekends if days are known.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_in(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def norm_str(s):
    return s.strip().lower() if isinstance(s, str) else ''


def parse_iso_parts(dt_str):
    # Parse YYYY-MM-DDTHH:MM:SS(.sss)?(Z|+hh:mm)? without datetime module
    # Return (year, month, day, hour, minute)
    if not isinstance(dt_str, str) or 'T' not in dt_str:
        return None
    date_part, time_part = dt_str.split('T', 1)
    # Remove timezone suffix if present (Z or +hh:mm or -hh:mm)
    # Find first character of timezone marker: 'Z' or '+' or '-'
    tz_pos = None
    for i, ch in enumerate(time_part):
        if ch in 'Zz+-':
            tz_pos = i
            break
    if tz_pos is not None:
        time_core = time_part[:tz_pos]
    else:
        time_core = time_part
    date_bits = date_part.split('-')
    time_bits = time_core.split(':')
    try:
        y = int(date_bits[0]); m = int(date_bits[1]); d = int(date_bits[2])
        hh = int(time_bits[0]); mm = int(time_bits[1])
        return (y, m, d, hh, mm)
    except Exception:
        return None


WEEKDAY_ABBR = {
    'MO': 'MO', 'MON': 'MO', 'MONDAY': 'MO',
    'TU': 'TU', 'TUE': 'TU', 'TUES': 'TU', 'TUESDAY': 'TU',
    'WE': 'WE', 'WED': 'WE', 'WEDNESDAY': 'WE',
    'TH': 'TH', 'THU': 'TH', 'THUR': 'TH', 'THURS': 'TH', 'THURSDAY': 'TH',
    'FR': 'FR', 'FRI': 'FR', 'FRIDAY': 'FR',
    'SA': 'SA', 'SAT': 'SA', 'SATURDAY': 'SA',
    'SU': 'SU', 'SUN': 'SU', 'SUNDAY': 'SU'
}

REQUIRED_DAYS = {'MO', 'TU', 'WE', 'TH', 'FR'}
WEEKEND_DAYS = {'SA', 'SU'}


def normalize_days(value):
    """Extract a set of day abbreviations from various representations.
    value can be list/str/dict.
    """
    days = set()
    if value is None:
        return days
    if isinstance(value, list):
        for v in value:
            days |= normalize_days(v)
        return days
    if isinstance(value, dict):
        # common keys
        for key in ['daysOfWeek', 'byDay', 'days', 'weekDays', 'repeatDays']:
            if key in value:
                days |= normalize_days(value[key])
        # Sometimes dicts may hold an rrule
        if 'rrule' in value and isinstance(value['rrule'], str):
            days |= normalize_days(value['rrule'])
        if 'recurrence' in value:
            days |= normalize_days(value['recurrence'])
        return days
    if isinstance(value, str):
        s = value.strip()
        u = s.upper()
        # If RRULE-like, parse BYDAY
        if 'BYDAY=' in u:
            idx = u.find('BYDAY=') + len('BYDAY=')
            tail = u[idx:]
            # End at next ';' if present
            end = tail.find(';')
            if end != -1:
                day_part = tail[:end]
            else:
                day_part = tail
            for token in day_part.split(','):
                token = token.strip().upper()
                # Token may include numeric prefixes like 1MO for monthly rules
                # Strip leading digits and signs
                while token and (token[0] in '+-' or token[0].isdigit()):
                    token = token[1:]
                if token in WEEKDAY_ABBR:
                    days.add(WEEKDAY_ABBR[token])
        else:
            # Split on non-letters to find possible day names
            buf = ''
            for ch in u:
                if ch.isalpha():
                    buf += ch
                else:
                    if buf:
                        if buf in WEEKDAY_ABBR:
                            days.add(WEEKDAY_ABBR[buf])
                        buf = ''
            if buf and buf in WEEKDAY_ABBR:
                days.add(WEEKDAY_ABBR[buf])
        return days
    return days


def has_weekday_recurrence(ev):
    # Check explicit recurrence fields
    days = set()
    # 1) Google-like recurrence list
    rec = ev.get('recurrence')
    days |= normalize_days(rec)

    # 2) rrule string
    if isinstance(ev.get('rrule'), str):
        days |= normalize_days(ev['rrule'])

    # 3) nested recurrence dicts
    for key in ['repeat', 'repeatOption', 'repeatRule', 'repeatOn', 'schedule']:
        val = ev.get(key)
        days |= normalize_days(val)
        # Also handle strings like "Every weekday"
        if isinstance(val, str):
            u = val.strip().lower()
            if 'weekday' in u or 'weekdays' in u:
                # treat as Mon-Fri
                days |= REQUIRED_DAYS

    # 4) direct day lists
    for key in ['daysOfWeek', 'byDay', 'days', 'weekDays', 'repeatDays']:
        if key in ev:
            days |= normalize_days(ev[key])

    # Some systems put info in description/title; catch common phrases cautiously
    text_blob = ' '.join([
        norm_str(ev.get('title', '')),
        norm_str(ev.get('description', ''))
    ])
    if 'every weekday' in text_blob or 'weekdays' in text_blob:
        days |= REQUIRED_DAYS

    if not days:
        return False
    # Require presence of all weekdays
    if not REQUIRED_DAYS.issubset(days):
        return False
    # If weekends explicitly present, reject
    if days & WEEKEND_DAYS:
        return False
    return True


def get_dt_strings(ev):
    # Try common keys
    for sk in ['start', 'startTime', 'startDate', 'from']:
        start = ev.get(sk)
        if isinstance(start, str) and 'T' in start:
            break
    else:
        start = ev.get('start')
    for ek in ['end', 'endTime', 'endDate', 'to']:
        end = ev.get(ek)
        if isinstance(end, str) and 'T' in end:
            break
    else:
        end = ev.get('end')
    return start, end


def is_correct_event(ev):
    # Not all-day
    if ev.get('allDay') is True:
        return False

    title = norm_str(ev.get('title', ''))
    desc = norm_str(ev.get('description', ''))
    location = norm_str(ev.get('location', ''))

    keywords = ['workout', 'work out', 'gym', 'exercise']
    text_ok = any(k in title for k in keywords) or any(k in desc for k in keywords) or ('gym' in location)
    if not text_ok:
        return False

    start_str, end_str = get_dt_strings(ev)
    pstart = parse_iso_parts(start_str)
    pend = parse_iso_parts(end_str)
    if not pstart or not pend:
        return False

    _, mo, day, sh, sm = pstart
    _, mo2, day2, eh, em = pend

    # Start date exactly September 20th
    date_ok = (mo == 9 and day == 20)

    # Same-day event preferred but not strictly necessary; ignore mo2/day2
    time_ok = (sh == 19 and sm == 45 and eh == 20 and em == 45)

    recur_ok = has_weekday_recurrence(ev)

    return date_ok and time_ok and recur_ok


def main():
    path = sys.argv[1]
    data = load_json(path)
    events_added = get_in(data, ['differences', 'events', 'added'], {}) or {}

    success = False
    if isinstance(events_added, dict) and events_added:
        for ev in events_added.values():
            if isinstance(ev, dict) and is_correct_event(ev):
                success = True
                break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
