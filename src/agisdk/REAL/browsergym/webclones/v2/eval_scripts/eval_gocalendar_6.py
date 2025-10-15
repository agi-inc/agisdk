import json
import sys

# Verification Script for: Go Calendar: Add an event for Monday morning: reminding I need to buy gym clothes
# Strategy:
# 1) Ensure at least one event was added in differences.events.added.
# 2) For each added event, search all string content and common schedule fields to confirm:
#    - Content mentions gym-related and clothes-related terms, and
#    - Scheduled (or textually indicated) for Monday AND in the morning.
# 3) SUCCESS if any added event satisfies all conditions; otherwise FAILURE.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_nested(dct, *keys):
    cur = dct
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def collect_strings(obj, out):
    # Recursively collect all string values from nested structures
    if isinstance(obj, dict):
        for v in obj.values():
            collect_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect_strings(v, out)
    else:
        if isinstance(obj, str):
            out.append(obj)
        elif isinstance(obj, (int, float, bool)):
            # Include numeric/bool as strings to catch values like weekday enums
            out.append(str(obj))
        # Ignore None


def search_keys(obj, keynames, results):
    # Recursively find values for specific keys in nested dicts/lists
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keynames:
                results.append(v)
            search_keys(v, keynames, results)
    elif isinstance(obj, list):
        for v in obj:
            search_keys(v, keynames, results)


def has_time_am(text):
    # Detect presence of time in AM format without regex.
    # We look for a digit sequence followed by optional space/colon and then 'am'.
    t = text.lower()
    n = len(t)
    i = 0
    while i < n:
        ch = t[i]
        if '0' <= ch <= '9':
            # Move forward through digits and optional colon and more digits/spaces
            j = i
            saw_digit = False
            while j < n and (('0' <= t[j] <= '9') or t[j] in [' ', ':']):
                if '0' <= t[j] <= '9':
                    saw_digit = True
                j += 1
            # Now check for 'am' immediately after optional spaces
            k = j
            while k < n and t[k] == ' ':
                k += 1
            if k + 1 < n and t[k] == 'a' and t[k+1] == 'm' and saw_digit:
                # Try to avoid matching words like 'example' by ensuring preceding char isn't a letter
                prev = t[i-1] if i-1 >= 0 else ' '
                if not ('a' <= prev <= 'z'):
                    # Also avoid midnight 12am being considered morning; check if preceding number is 12
                    # Try to extract the immediate hour number before optional colon
                    # Move left to find start of the number
                    p = i
                    while p-1 >= 0 and '0' <= t[p-1] <= '9':
                        p -= 1
                    hour_str = t[p:i+1]
                    # Only consider 1..11 as morning hours
                    try:
                        hour = int(hour_str)
                        if 1 <= hour <= 11:
                            return True
                    except:
                        # If parsing fails, still consider it as AM time
                        return True
            i = j
        else:
            i += 1
    return False


def contains_monday(text):
    t = text.lower()
    if 'monday' in t:
        return True
    # Also consider common abbreviations with boundaries (crude): ' mon ' or starting/ending
    # This is conservative to avoid matching 'money'.
    tokens = t.replace('\n', ' ').replace('\t', ' ').split()
    if 'mon' in tokens or 'mon.' in tokens or '(mon)' in t or '[mon]' in t:
        return True
    return False


def monday_from_keys(event):
    vals = []
    search_keys(event, ['dayOfWeek', 'weekday', 'day', 'day_name', 'dow'], vals)
    for v in vals:
        s = str(v).strip().lower()
        if s in ['monday', 'mon']:
            return True
        # Accept common numeric encodings; prefer explicit keys only
        if s in ['0', '1']:
            return True
    return False


def morning_from_keys(event):
    vals = []
    search_keys(event, ['timeOfDay', 'period', 'partOfDay'], vals)
    for v in vals:
        s = str(v).strip().lower()
        if 'morning' in s:
            return True
    return False


def has_gym_clothes_terms(text):
    t = text.lower()
    clothes_terms = ['clothes', 'gear', 'wear', 'attire']
    gym_terms = ['gym', 'workout', 'athletic', 'sportswear', 'sportwear', 'sports wear']
    has_clothes = any(term in t for term in clothes_terms)
    has_gym = any(term in t for term in gym_terms)
    return has_clothes and has_gym


def verify(data):
    diffs = data.get('differences') or {}
    events = (diffs.get('events') or {}).get('added') or {}
    # Some schemas may put added events as a list
    if isinstance(events, list):
        added_events = events
    elif isinstance(events, dict):
        added_events = list(events.values())
    else:
        added_events = []

    if not added_events:
        return False

    for ev in added_events:
        strings = []
        collect_strings(ev, strings)
        text = ' '.join(strings).lower()

        # Check content relevance
        if not has_gym_clothes_terms(text):
            continue

        # Determine Monday and morning
        is_monday = monday_from_keys(ev) or contains_monday(text)
        is_morning = morning_from_keys(ev) or ('morning' in text) or has_time_am(text)

        if is_monday and is_morning:
            return True

    return False


def main():
    try:
        path = sys.argv[1]
        data = load_json(path)
        ok = verify(data)
        print('SUCCESS' if ok else 'FAILURE')
    except Exception:
        # Fail closed on any exception
        print('FAILURE')


if __name__ == '__main__':
    main()
