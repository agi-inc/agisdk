import sys, json

def to_lower(s):
    try:
        return s.lower()
    except Exception:
        return s

# Split a string into alphabetic tokens (letters only), lowercase
# This avoids false positives like 'fridge' for 'fri'

def alpha_tokens(s):
    s = to_lower(s)
    out = []
    cur = []
    for ch in s:
        if 'a' <= ch <= 'z':
            cur.append(ch)
        else:
            if cur:
                out.append(''.join(cur))
                cur = []
    if cur:
        out.append(''.join(cur))
    return out

# Recursively iterate over all values in a nested structure

def iter_values(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield v
            for vv in iter_values(v):
                yield vv
    elif isinstance(obj, list):
        for it in obj:
            yield it
            for vv in iter_values(it):
                yield vv

# Check if any string value contains substring 'laundry'

def mentions_laundry(obj):
    for v in iter_values(obj):
        if isinstance(v, str):
            if 'laundry' in v.lower():
                return True
    return False

# Determine if the object indicates Friday in any conventional way

def indicates_friday(obj):
    # 1) Look for textual mention of 'friday' or abbreviation 'fri' as a token
    for v in iter_values(obj):
        if isinstance(v, str):
            toks = alpha_tokens(v)
            if 'friday' in toks or 'fri' in toks or 'fr' in toks and 'byweekday' in v.lower():
                return True
    # 2) Look for fields suggesting weekday index
    # If a dict has keys like 'weekday', 'dayOfWeek', 'week_day', etc., and value 4 or 5
    def check_weekday_fields(d):
        for k, v in d.items():
            lk = k.lower()
            if isinstance(v, (int, float)):
                if ('weekday' in lk or 'dayofweek' in lk or lk.endswith('weekday') or lk.endswith('day')):
                    # Accept both common conventions: Monday=0 -> Friday=4, Sunday=0 -> Friday=5
                    if int(v) in (4, 5):
                        return True
            elif isinstance(v, str):
                tv = v.strip().lower()
                if ('weekday' in lk or 'dayofweek' in lk or lk.endswith('weekday') or lk.endswith('day')):
                    if tv in ('friday', 'fri', 'fr'):
                        return True
            elif isinstance(v, dict):
                # Recursively check nested dicts for same pattern
                if check_weekday_fields(v):
                    return True
            elif isinstance(v, list):
                # Lists of weekday strings or indexes
                # e.g., ['MO','TU','WE','TH','FR'] or ['friday'] or [5]
                vals = v
                has_friday = False
                for item in vals:
                    if isinstance(item, (int, float)) and int(item) in (4, 5):
                        return True
                    if isinstance(item, str):
                        it = item.strip().lower()
                        if it in ('friday', 'fri', 'fr') or it == 'fr':
                            return True
        return False

    if isinstance(obj, dict):
        if check_weekday_fields(obj):
            return True

    # 3) Look for common RRULE/recurrence tokens containing FR
    for v in iter_values(obj):
        if isinstance(v, str):
            lv = v.lower()
            if 'rrule' in lv or 'byweekday' in lv or 'byday' in lv or 'fr;' in lv or 'byday=fr' in lv:
                if 'fr' in lv:
                    return True
    return False

# Extract objects from added/updated sections; handle both dict or list forms

def extract_items(section_obj):
    items = []
    if not isinstance(section_obj, dict):
        return items
    for change_type in ('added', 'updated'):
        sub = section_obj.get(change_type)
        if not sub:
            continue
        if isinstance(sub, dict):
            for _id, val in sub.items():
                # Some diffs might nest final value under common keys; try to unwrap typical containers
                candidate = val
                if isinstance(candidate, dict):
                    for key in ('after', 'new', 'to', 'value', 'final', 'current', 'curr'):
                        if key in candidate and isinstance(candidate[key], (dict, list, str, int, float)):
                            candidate = candidate[key]
                            break
                items.append(candidate)
        elif isinstance(sub, list):
            for val in sub:
                candidate = val
                if isinstance(candidate, dict):
                    for key in ('after', 'new', 'to', 'value', 'final', 'current', 'curr'):
                        if key in candidate and isinstance(candidate[key], (dict, list, str, int, float)):
                            candidate = candidate[key]
                            break
                items.append(candidate)
    return items


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    diffs = data.get('differences') if isinstance(data, dict) else None
    if not isinstance(diffs, dict):
        # Fallback: sometimes the file itself might be the diff object
        diffs = data if isinstance(data, dict) else {}

    sections_to_check = ['events', 'reminders', 'joinedEvents', 'notifications', 'tasks', 'todos']

    candidates = []
    for sec in sections_to_check:
        sec_obj = diffs.get(sec)
        if isinstance(sec_obj, dict):
            items = extract_items(sec_obj)
            candidates.extend(items)

    # If nothing added/updated in relevant sections -> likely no reminder created
    if not candidates:
        print('FAILURE')
        return

    # Evaluate candidates for both conditions
    for item in candidates:
        try:
            if mentions_laundry(item) and indicates_friday(item):
                print('SUCCESS')
                return
        except Exception:
            # Ignore malformed items
            pass

    print('FAILURE')

if __name__ == '__main__':
    main()
