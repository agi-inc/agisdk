import sys, json

# Verification script for: GoCalendar - Add a task to send an email to Ashley for Monday Morning
# Strategy:
# - Parse final_state_diff.json and inspect differences.events and differences.joinedEvents for added/updated items.
# - Identify any event whose text mentions (email + Ashley), and whose timing indicates Monday AND Morning ("morning" or AM time).
# - Be robust to varying shapes (dict/list; updated entries with 'after' snapshots) and missing fields.


def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def collect_event_objs(dif_section):
    events = []
    if not isinstance(dif_section, dict):
        return events
    for bucket_name in ('added', 'updated'):
        bucket = dif_section.get(bucket_name)
        if isinstance(bucket, dict):
            for _, v in bucket.items():
                # updated may have {'before':..., 'after':...}
                if isinstance(v, dict) and 'after' in v and isinstance(v.get('after'), dict):
                    events.append(v['after'])
                elif isinstance(v, dict):
                    events.append(v)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict) and 'after' in item and isinstance(item.get('after'), dict):
                            events.append(item['after'])
                        elif isinstance(item, dict):
                            events.append(item)
        elif isinstance(bucket, list):
            for v in bucket:
                if isinstance(v, dict) and 'after' in v and isinstance(v.get('after'), dict):
                    events.append(v['after'])
                elif isinstance(v, dict):
                    events.append(v)
    return events


def flatten_strings(obj):
    strings = []
    def _rec(x):
        if isinstance(x, str):
            strings.append(x)
        elif isinstance(x, dict):
            for k, v in x.items():
                _rec(v)
        elif isinstance(x, list):
            for it in x:
                _rec(it)
    _rec(obj)
    return strings


def iter_key_str_pairs(obj, parent_key=""):
    # Yields (key_path, string_value) for all string fields
    pairs = []
    def _rec(x, kpath):
        if isinstance(x, str):
            pairs.append((kpath, x))
        elif isinstance(x, dict):
            for k, v in x.items():
                nk = (kpath + "." if kpath else "") + str(k)
                _rec(v, nk)
        elif isinstance(x, list):
            for idx, it in enumerate(x):
                nk = (kpath + "." if kpath else "") + str(idx)
                _rec(it, nk)
    _rec(obj, parent_key)
    return pairs


def tokenized_contains_mon(text):
    t = text.lower()
    # replace common separators with spaces
    seps = [',', '.', '(', ')', '-', '_', '/', '\\', '|', ':', ';', '\n', '\t']
    for s in seps:
        t = t.replace(s, ' ')
    t = ' ' + t + ' '
    if ' monday ' in t:
        return True
    # Look for standalone 'mon' token (avoid matching 'month')
    # After separator normalization, ' month ' won't match ' mon '
    if ' mon ' in t:
        return True
    return False


def is_day_key(key_lower):
    hints = ['day', 'weekday', 'dayofweek', 'dow', 'date_label', 'date_text', 'day_name']
    return any(h in key_lower for h in hints)


def is_time_key(key_lower):
    hints = ['time', 'start', 'when', 'slot', 'hour']
    return any(h in key_lower for h in hints)


def contains_am_time(text_lower):
    t = text_lower
    n = len(t)
    i = 0
    while i < n - 1:
        if t[i] == 'a' and t[i+1] == 'm':
            # Check for a digit immediately before 'am' (e.g., '10am', '9am', '9:30am')
            prev_is_digit = (i-1) >= 0 and t[i-1].isdigit()
            prev_colon_digit = (i-2) >= 0 and t[i-1] == ':' and t[i-2].isdigit()
            prev_space_digit = (i-2) >= 0 and t[i-1] == ' ' and t[i-2].isdigit()
            if prev_is_digit or prev_colon_digit or prev_space_digit:
                return True
        i += 1
    return False


def matches_email_ashley(text_lower):
    return ('ashley' in text_lower) and (('email' in text_lower) or ('e-mail' in text_lower))


def event_matches(event_obj):
    # Evaluate conditions on a per-event basis
    key_strs = iter_key_str_pairs(event_obj)
    all_text = ' '.join([s for _, s in key_strs]).lower()

    email_match = matches_email_ashley(all_text)

    monday_match = False
    morning_match = False

    for key, s in key_strs:
        kl = str(key).lower()
        sl = s.lower()
        # Monday detection
        if not monday_match:
            if 'monday' in sl:
                monday_match = True
            elif is_day_key(kl) and ('mon' in sl or 'monday' in sl or tokenized_contains_mon(sl)):
                monday_match = True
        # Morning detection
        if not morning_match:
            if 'morning' in sl:
                morning_match = True
            elif is_time_key(kl) and contains_am_time(sl):
                morning_match = True

        if email_match and monday_match and morning_match:
            break

    # As a fallback for Monday detection, if not found in targeted fields, accept generic tokenized 'monday' in any text
    if not monday_match and tokenized_contains_mon(all_text):
        # Only promote if it contains full 'monday' token or ' mon ' token distinctly
        monday_match = True

    return email_match and monday_match and morning_match


def main():
    if len(sys.argv) < 2:
        print('FAILURE')
        return
    data = load_json(sys.argv[1])
    diffs = data.get('differences') or {}

    # Collect candidate events from events and joinedEvents
    events = []
    events += collect_event_objs(diffs.get('events', {}))
    events += collect_event_objs(diffs.get('joinedEvents', {}))

    # If nothing was added/updated, it's a failure
    if not events:
        print('FAILURE')
        return

    # Check if any event satisfies the task conditions
    for ev in events:
        if isinstance(ev, dict) and event_matches(ev):
            print('SUCCESS')
            return

    print('FAILURE')


if __name__ == '__main__':
    main()
