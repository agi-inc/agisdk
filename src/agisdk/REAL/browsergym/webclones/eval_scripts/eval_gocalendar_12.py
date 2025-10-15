import sys, json, re

# Verification script for: "Remind me to pick up my sister on Wednesday at 11 am"
# Strategy:
# 1) Look for newly added/updated calendar events.
# 2) Validate event text mentions picking up sister and the scheduled time is Wednesday at 11:00 AM.
#    Robustly parse common date/time fields and strings. Only declare SUCCESS when all conditions match.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_dict(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def to_text(val):
    try:
        if val is None:
            return ''
        if isinstance(val, (dict, list)):
            return json.dumps(val, ensure_ascii=False)
        return str(val)
    except Exception:
        return ''


def collect_events(diff):
    events = []
    diffs = diff.get('differences') or {}
    for section in ['events']:
        sec = diffs.get(section) or {}
        for change in ['added', 'updated']:
            chg = sec.get(change) or {}
            if isinstance(chg, dict):
                for _id, ev in chg.items():
                    if isinstance(ev, dict):
                        events.append(ev)
    return events


def text_mentions_pickup_sister(text):
    t = (text or '').lower()
    # Require sister present
    if 'sister' not in t:
        return False
    # Pickup patterns
    pickup_patterns = [
        r'\bpick\s*up\b',
        r'\bpick-up\b',
        r'\bpickup\b',
        r'\bcollect\b',
        r'\bdrive\b.*\bsister\b',
    ]
    for pat in pickup_patterns:
        if re.search(pat, t):
            return True
    return False


def flatten_strings_for_time_search(data, parent_key=''):
    strings = []
    if isinstance(data, dict):
        for k, v in data.items():
            key_l = str(k).lower()
            # Only collect strings from likely time/date related fields for time/day checks
            if any(term in key_l for term in ['start', 'time', 'date', 'when', 'begin', 'at']):
                strings.extend(flatten_strings_for_time_search(v, key_l))
    elif isinstance(data, list):
        for v in data:
            strings.extend(flatten_strings_for_time_search(v, parent_key))
    else:
        s = to_text(data).strip()
        if s:
            strings.append(s)
    return strings


def parse_iso_date(date_str):
    # Expect YYYY-MM-DD
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return y, mo, d


def is_wednesday_from_date_ymd(y, m, d):
    # Zeller's Congruence to compute weekday without datetime module
    # h = 0: Saturday, 1: Sunday, 2: Monday, 3: Tuesday, 4: Wednesday, 5: Thursday, 6: Friday
    Y = y
    M = m
    D = d
    if M < 3:
        M += 12
        Y -= 1
    K = Y % 100
    J = Y // 100
    h = (D + (13 * (M + 1)) // 5 + K + (K // 4) + (J // 4) + (5 * J)) % 7
    return h == 4


def contains_wednesday_word(s):
    t = s.lower()
    return re.search(r'\bwed(?:nesday)?\b', t) is not None


def time_is_11_am_from_string(s):
    t = s.lower()
    # ISO datetime e.g., 2025-01-08T11:00:00Z or 2025-01-08 11:00
    m_iso = re.search(r't(\d{2}):(\d{2})', t)
    if m_iso:
        hh = int(m_iso.group(1))
        mm = int(m_iso.group(2))
        if hh == 11 and mm == 0:
            return True
    # 24-hour time HH:MM
    for m in re.finditer(r'\b([01]?\d|2[0-3]):([0-5]\d)\b', t):
        hh = int(m.group(1))
        mm = int(m.group(2))
        if hh == 11 and mm == 0:
            return True
    # 12-hour with am/pm
    m_ampm = re.search(r'\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*([ap])\.?m\.?\b', t)
    if m_ampm:
        hh = int(m_ampm.group(1))
        mm = m_ampm.group(2)
        mm = int(mm) if mm is not None else 0
        ap = m_ampm.group(3)
        if ap == 'a' and hh == 11 and mm == 0:
            return True
        # If explicitly pm and hour 11, it's 11 pm -> not ok
    # Edge case: textual '11 am' without colon already covered above
    return False


def extract_event_text(ev):
    # Aggregate human-readable textual fields for intent matching
    fields = ['title', 'name', 'summary', 'description', 'notes', 'text', 'content', 'details', 'subject']
    texts = []
    for k in fields:
        if k in ev:
            texts.append(to_text(ev.get(k)))
    # Also consider top-level string values if keys indicate event label
    for k, v in ev.items():
        if isinstance(v, str) and any(tok in k.lower() for tok in ['title', 'name', 'summary', 'desc', 'subject']):
            texts.append(v)
    return ' \n '.join([t for t in texts if t])


def event_matches(ev):
    # 1) Intent text check
    ev_text = extract_event_text(ev)
    if not text_mentions_pickup_sister(ev_text):
        return False

    # 2) Time and weekday checks from typical date/time fields
    time_related_strings = flatten_strings_for_time_search(ev)

    # Determine time==11:00 AM
    time_ok = False
    for s in time_related_strings:
        if time_is_11_am_from_string(s):
            time_ok = True
            break

    if not time_ok:
        return False

    # Determine Wednesday either via weekday word or date->weekday
    day_ok = False
    for s in time_related_strings:
        if contains_wednesday_word(s):
            day_ok = True
            break
    if not day_ok:
        # Try to find explicit date and compute weekday
        for s in time_related_strings:
            parsed = parse_iso_date(s)
            if parsed:
                if is_wednesday_from_date_ymd(*parsed):
                    day_ok = True
                    break

    return time_ok and day_ok


def main():
    path = sys.argv[1]
    data = load_json(path)
    events = collect_events(data if isinstance(data, dict) else {})

    success = False
    for ev in events:
        try:
            if event_matches(ev):
                success = True
                break
        except Exception:
            # Ignore malformed events, continue scanning others
            continue

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
