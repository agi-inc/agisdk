import sys, json

# Strategy in code:
# - Load final_state_diff JSON and aggregate deleted/updated events from both 'events' and 'joinedEvents'.
# - Identify success if any event that (appears to be) a dinner plan on Wednesday was deleted or marked cancelled.
# - Detect 'Wednesday' via ISO date strings and textual weekday hints without external libraries; detect 'dinner' via keywords.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_diffs(data):
    # Support structures where 'differences' is root or nested
    diffs = data.get('differences', data)
    if not isinstance(diffs, dict):
        return {}
    return diffs


def collect_entries(diffs, section_name):
    sec = diffs.get(section_name, {}) or {}
    deleted = sec.get('deleted', {}) or {}
    updated = sec.get('updated', {}) or {}
    # deleted/updated may be lists or dicts keyed by ids; normalize to list of event dicts
    def normalize(x):
        if isinstance(x, dict):
            return list(x.values())
        if isinstance(x, list):
            return [i for i in x if isinstance(i, dict)]
        return []
    return normalize(deleted), normalize(updated)


def text_contains_dinner(text):
    if not text:
        return False
    t = str(text).lower()
    keywords = ['dinner', 'supper']
    return any(k in t for k in keywords)


def extract_title_like(evt):
    for k in ['title','summary','name','eventName','subject','text','label']:
        v = evt.get(k)
        if isinstance(v, str) and v.strip():
            return v
    # Sometimes nested under 'details' or similar
    details = evt.get('details') or evt.get('meta') or {}
    if isinstance(details, dict):
        for k in ['title','summary','name','subject']:
            v = details.get(k)
            if isinstance(v, str) and v.strip():
                return v
    return ''


def extract_description_like(evt):
    for k in ['description','notes','body','comment']:
        v = evt.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ''


def parse_iso_date_parts(s):
    # Extract YYYY-MM-DD at the beginning of the string
    if not isinstance(s, str):
        return None
    # Accept formats like YYYY-MM-DD or YYYY/MM/DD
    part = None
    if len(s) >= 10 and s[4] in '-/' and s[7] in '-/':
        y = s[0:4]
        m = s[5:7]
        d = s[8:10]
        if y.isdigit() and m.isdigit() and d.isdigit():
            return int(y), int(m), int(d)
    # Also try to locate the first occurrence of YYYY-MM-DD inside the string
    for sep in ['-', '/']:
        try:
            idx = s.index(sep)
        except ValueError:
            continue
    return None


def zellers_weekday(y, m, d):
    # Zeller's Congruence for Gregorian calendar
    # Return 0=Sunday, 1=Monday, ..., 6=Saturday
    if m < 3:
        m += 12
        y -= 1
    K = y % 100
    J = y // 100
    h = (d + (13*(m + 1))//5 + K + (K//4) + (J//4) + 5*J) % 7
    # h: 0=Saturday, 1=Sunday, 2=Monday, ..., 6=Friday
    # Convert to 0=Monday style? We'll map to 0=Sunday
    # Map h to weekday_0_sun
    weekday_0_sun = (h + 6) % 7
    return weekday_0_sun


def is_wednesday_from_parts(parts):
    try:
        y, m, d = parts
    except Exception:
        return False
    wd = zellers_weekday(y, m, d)  # 0=Sunday, 3=Wednesday
    return wd == 3


def string_mentions_wednesday(s):
    if not isinstance(s, str):
        return False
    s_low = s.lower()
    return ('wednesday' in s_low) or (' wed ' in (' ' + s_low + ' ')) or s_low.strip().startswith('wed')


def extract_start_candidates(evt):
    # Return a list of strings that may contain date/time
    cans = []
    # Common nested structures
    start = evt.get('start')
    if isinstance(start, dict):
        for k in ['dateTime','date','datetime','time','iso','value','start','startTime']:
            v = start.get(k)
            if isinstance(v, str):
                cans.append(v)
    elif isinstance(start, str):
        cans.append(start)
    # Root-level possibilities
    for k in ['startDate','start_date','startDateTime','start_datetime','start_at','date','dateTime','datetime','when','from']:
        v = evt.get(k)
        if isinstance(v, str):
            cans.append(v)
    # Sometimes the weekday is stored separately
    for k in ['day','weekday','dayOfWeek','dow']:
        v = evt.get(k)
        if isinstance(v, str):
            cans.append(v)
    return cans


def is_event_on_wednesday(evt):
    cans = extract_start_candidates(evt)
    # First, textual weekday hints
    if any(string_mentions_wednesday(s) for s in cans):
        return True
    # Next, try ISO date parsing
    for s in cans:
        parts = parse_iso_date_parts(s)
        if parts and is_wednesday_from_parts(parts):
            return True
    return False


def is_event_dinner(evt):
    title = extract_title_like(evt)
    desc = extract_description_like(evt)
    return text_contains_dinner(title) or text_contains_dinner(desc)


def is_event_cancelled_status(evt):
    # Look for status fields indicating cancellation
    # Accept values containing 'cancel'
    cancel_keys = ['status','eventStatus','state']
    for k in cancel_keys:
        v = evt.get(k)
        if isinstance(v, str) and ('cancel' in v.lower()):
            return True
    # Boolean flags
    for k in ['cancelled','canceled','isCancelled','isCanceled','is_deleted','deleted','isDeleted']:
        v = evt.get(k)
        if isinstance(v, bool) and v is True:
            return True
        if isinstance(v, str) and v.lower() in ['true','yes','1']:
            return True
    # Sometimes nested under 'status' object
    st = evt.get('status')
    if isinstance(st, dict):
        for k in ['code','value','text']:
            v = st.get(k)
            if isinstance(v, str) and ('cancel' in v.lower()):
                return True
    return False


def main():
    path = sys.argv[1]
    data = load_json(path)
    diffs = get_diffs(data)

    # Gather deleted and updated from both events and joinedEvents
    deleted_events = []
    updated_events = []
    for section in ['events', 'joinedEvents']:
        d, u = collect_entries(diffs, section)
        deleted_events.extend(d)
        updated_events.extend(u)

    success = False

    # Primary condition: a dinner event on Wednesday was deleted
    for evt in deleted_events:
        if is_event_on_wednesday(evt) and is_event_dinner(evt):
            success = True
            break

    # Secondary: a dinner event was marked cancelled via update (and Wednesday if detectable)
    if not success:
        for evt in updated_events:
            if is_event_cancelled_status(evt) and (is_event_dinner(evt) or is_event_on_wednesday(evt)):
                success = True
                break

    # Fallback: if no explicit dinner match, accept deletion of any Wednesday event
    if not success:
        for evt in deleted_events:
            if is_event_on_wednesday(evt):
                success = True
                break

    # Another fallback: if exactly one event was deleted and it's clearly a dinner (even if day unknown)
    if not success and len(deleted_events) == 1:
        if is_event_dinner(deleted_events[0]):
            success = True

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
