import sys, json

# Verification script for: Go Calendar: Add an event for Wednesday evening: set my fantasy lineup before TNF
# Strategy:
# - Find newly added/updated events (events/joinedEvents) in final_state_diff.
# - Confirm an event has text containing both 'fantasy' and 'lineup' (case-insensitive).
# - Confirm scheduling is on Wednesday and in the evening (either tokens 'wednesday'/'wed' and 'evening',
#   or by computing weekday from a detected YYYY-MM-DD date and extracting an evening hour from time strings).
# - Output SUCCESS if any event satisfies all conditions; otherwise FAILURE.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def is_str(x):
    return isinstance(x, str)


def tokenize(text):
    # Lowercase, split on non-alphanumeric
    s = []
    for ch in text.lower():
        if ch.isalnum():
            s.append(ch)
        else:
            s.append(' ')
    return [t for t in ''.join(s).split() if t]


def gather_candidates(diffs):
    candidates = []
    if not isinstance(diffs, dict):
        return candidates
    for section in ('events', 'joinedEvents'):
        sec = diffs.get(section, {}) or {}
        if not isinstance(sec, dict):
            continue
        for change_type in ('added', 'updated'):
            ch = sec.get(change_type, {})
            if isinstance(ch, dict):
                # values are event objects
                for v in ch.values():
                    candidates.append(v)
            elif isinstance(ch, list):
                candidates.extend(ch)
            # else ignore
    return candidates


def deep_strings(obj):
    # Collect all strings from nested structures
    out = []
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for v in cur.values():
                stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)
        elif isinstance(cur, str):
            out.append(cur)
        # ignore other types
    return out


def get_text_fields(event):
    # Prefer title/summary/description-like fields, then fallback to all strings
    title_keys = {'title','name','summary','subject','eventTitle','heading'}
    desc_keys = {'description','notes','details','body','content'}
    texts = []
    if isinstance(event, dict):
        for k,v in event.items():
            if k in title_keys and isinstance(v, str):
                texts.append(v)
            if k in desc_keys and isinstance(v, str):
                texts.append(v)
    # Also dive into common containers
    if isinstance(event, dict):
        for k in ('title','summary','description','notes','details','body','content'):  # nested
            v = event.get(k)
            if isinstance(v, dict) or isinstance(v, list):
                texts.extend([s for s in deep_strings(v)])
    # Fallback to all strings if nothing gathered
    if not texts:
        texts = deep_strings(event)
    return ' \n '.join([t for t in texts if isinstance(t, str)])


def zeller_weekday(y, m, d):
    # Return 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday
    # Implement via Zeller (h: 0=Sat,1=Sun,2=Mon,3=Tue,4=Wed,5=Thu,6=Fri)
    if m < 3:
        m += 12
        y -= 1
    K = y % 100
    J = y // 100
    h = (d + (13 * (m + 1)) // 5 + K + (K // 4) + (J // 4) + 5 * J) % 7
    # Map h to 0..6 with Monday=0
    # h=2->Mon(0), 3->Tue(1), 4->Wed(2), 5->Thu(3), 6->Fri(4), 0->Sat(5), 1->Sun(6)
    mapping = {2:0, 3:1, 4:2, 5:3, 6:4, 0:5, 1:6}
    return mapping.get(h, None)


def parse_int(s):
    try:
        return int(s)
    except Exception:
        return None


def try_parse_date_tokens(token):
    # Try YYYY-MM-DD or YYYY/MM/DD
    if not isinstance(token, str):
        return None
    for sep in ('-', '/'):
        if token.count(sep) == 2:
            parts = token.split(sep)
            if len(parts) == 3:
                y = parse_int(parts[0])
                m = parse_int(parts[1])
                d = parse_int(parts[2][:2])  # strip time if attached like 2025-01-15T...
                if y and m and d and 1 <= m <= 12 and 1 <= d <= 31 and len(parts[0]) == 4:
                    return (y, m, d)
    return None


def extract_possible_dates(event):
    # Scan all strings for date-like tokens
    dates = []
    for s in deep_strings(event):
        if not isinstance(s, str):
            continue
        # If ISO datetime like YYYY-MM-DDTHH:MM...
        if 'T' in s and '-' in s:
            # Split at 'T' and parse date part
            idx = s.find('T')
            date_part = s[:idx]
            dt = try_parse_date_tokens(date_part)
            if dt:
                dates.append(dt)
        # Also try whole token as date
        for piece in s.replace('T', ' ').split():
            dt = try_parse_date_tokens(piece)
            if dt:
                dates.append(dt)
    return dates


def extract_hours_from_string(s):
    hours = []
    ls = s.lower()
    # ISO time after 'T'
    if 't' in ls:
        # Handle patterns like 2025-01-15T18:30:00Z or T18:00
        idx = ls.find('t')
        time_part = ls[idx+1:]
        # First 2 digits might be hour
        if len(time_part) >= 2 and time_part[0:2].isdigit():
            h = int(time_part[0:2])
            if 0 <= h <= 23:
                hours.append(h)
    # AM/PM pattern: find 'am' or 'pm'
    has_am = 'am' in ls
    has_pm = 'pm' in ls
    if has_am or has_pm:
        # find first number (1 or 2 digits) preceding am/pm
        num = ''
        for ch in ls:
            if ch.isdigit():
                num += ch
            elif num:
                break
        if num:
            h = int(num)
            if 1 <= h <= 12:
                if has_pm and h != 12:
                    h = h + 12
                if has_am and h == 12:
                    h = 0
                hours.append(h)
    # 24-hour with colon HH:MM
    if ':' in ls:
        # scan for colon with digits before
        parts = ls.split()
        for p in parts:
            if ':' in p:
                idx = p.find(':')
                left = p[:idx]
                if len(left) >= 1 and len(left) <= 2 and left.isdigit():
                    h = int(left)
                    if 0 <= h <= 23:
                        hours.append(h)
    return hours


def extract_possible_hours(event):
    hours = []
    for s in deep_strings(event):
        if not isinstance(s, str):
            continue
        hours.extend(extract_hours_from_string(s))
    return hours


def contains_keywords(text):
    t = text.lower()
    return ('fantasy' in t) and ('lineup' in t)


def indicates_wednesday(text):
    toks = tokenize(text)
    # Exact tokens to avoid matching 'wedding'
    for w in toks:
        if w == 'wednesday' or w == 'wed':
            return True
    return False


def indicates_evening(text):
    toks = tokenize(text)
    for w in toks:
        if w == 'evening':
            return True
    return False


def is_wednesday_by_date(event):
    dates = extract_possible_dates(event)
    for (y, m, d) in dates:
        wd = zeller_weekday(y, m, d)
        # Wednesday -> wd == 2 (with our mapping)
        if wd == 2:
            return True
    return False


def has_evening_hour(event):
    hours = extract_possible_hours(event)
    for h in hours:
        if 17 <= h <= 23:
            return True
    return False


def verify(d):
    diffs = d.get('differences', {}) or {}
    candidates = gather_candidates(diffs)
    if not candidates:
        return False
    for ev in candidates:
        text = get_text_fields(ev)
        if not text:
            continue
        if not contains_keywords(text):
            continue
        # Day checks
        day_ok = indicates_wednesday(text)
        if not day_ok:
            # Try date-derived
            day_ok = is_wednesday_by_date(ev)
        # Evening checks
        evening_ok = indicates_evening(text)
        if not evening_ok:
            evening_ok = has_evening_hour(ev)
        if day_ok and evening_ok:
            return True
    return False


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print('FAILURE')
        return
    try:
        data = load_json(path)
    except Exception:
        print('FAILURE')
        return
    result = verify(data)
    print('SUCCESS' if result else 'FAILURE')

if __name__ == '__main__':
    main()
