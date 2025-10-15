import sys, json

def safe_lower(s):
    try:
        return s.lower()
    except Exception:
        return s

# Extract all candidate items from differences across sections

def collect_items(differences):
    items = []
    if not isinstance(differences, dict):
        return items
    for section, sec_val in differences.items():
        if not isinstance(sec_val, dict):
            continue
        for change_type in ("added", "updated"):
            change_dict = sec_val.get(change_type)
            if isinstance(change_dict, dict):
                for _k, v in change_dict.items():
                    # If v is a dict, that's likely the item
                    if isinstance(v, dict):
                        items.append(v)
                    # Sometimes the structure might be {'item': {...}}
                    elif isinstance(v, list):
                        for it in v:
                            if isinstance(it, dict):
                                items.append(it)
    return items

# Gather textual content that describes the task/event purpose

def extract_content_text(item):
    keys = [
        'title','name','summary','subject','caption','text','content','description','notes','note','message'
    ]
    parts = []
    for k in keys:
        val = item.get(k)
        if isinstance(val, str) and val.strip():
            parts.append(val)
    # Some systems nest content under fields
    for k in ['task','event','details']:
        sub = item.get(k)
        if isinstance(sub, dict):
            for kk in ['title','name','summary','description','notes','text','content']:
                val = sub.get(kk)
                if isinstance(val, str) and val.strip():
                    parts.append(val)
    return " \n ".join(parts).strip()

# Build date/time related text by scanning likely fields

def extract_datetime_text(item):
    dt_keys = [
        'start','startTime','start_time','startDate','start_date','startDateTime','start_datetime','from','when',
        'due','dueDate','dueTime','date','time','datetime','dateTime','schedule','scheduled','begin'
    ]
    texts = []
    for k in dt_keys:
        val = item.get(k)
        if isinstance(val, str) and val.strip():
            texts.append(val)
        elif isinstance(val, dict):
            # common subkeys
            for kk in ['date','time','dateTime','datetime','start','startTime','startDate','due','dueDate','dueTime']:
                v2 = val.get(kk)
                if isinstance(v2, str) and v2.strip():
                    texts.append(v2)
        elif isinstance(val, list):
            for v in val:
                if isinstance(v, str) and v.strip():
                    texts.append(v)
                elif isinstance(v, dict):
                    for kk in ['date','time','dateTime','datetime']:
                        v2 = v.get(kk)
                        if isinstance(v2, str) and v2.strip():
                            texts.append(v2)
    # Also check potential end fields in case systems only set a range
    for k in ['end','to','endTime','endDate','endDateTime']:
        val = item.get(k)
        if isinstance(val, str) and val.strip():
            texts.append(val)
        elif isinstance(val, dict):
            for kk in ['date','time','dateTime','datetime']:
                v2 = val.get(kk)
                if isinstance(v2, str) and v2.strip():
                    texts.append(v2)
    return " | ".join(texts)

# Evaluate if content mentions fixing sink pipes

def content_matches(text):
    if not text:
        return False
    t = text.lower()
    # require sink and pipe* presence
    has_sink = 'sink' in t
    has_pipe = 'pipe' in t  # matches pipe/pipes/piping
    # accept fix/repair/replace words
    action = any(w in t for w in ['fix','repair','replace'])
    return has_sink and has_pipe and action

# Determine date and time match: September 12 at 10:45 am

def date_time_matches(dt_text):
    if not dt_text:
        return False
    t = dt_text.lower()
    # Date check: any representation of September 12
    month_ok = False
    # ISO or numeric forms
    if '-09-12' in t or '/09/12' in t or '/9/12' in t or ' 9/12' in t or ' 09/12' in t or ' 9-12' in t or ' 09-12' in t:
        month_ok = True
    # Month name forms
    if ('september' in t or 'sept' in t or 'sep ' in t or ' sep' in t) and '12' in t:
        month_ok = True
    # Time check: look for 10:45 occurrences not marked as pm
    time_ok = False
    idx = 0
    while True:
        i = t.find('10:45', idx)
        if i == -1:
            break
        # Check for pm nearby (within +5 chars), e.g., '10:45pm' or '10:45 pm'
        after = t[i:i+10]
        if 'pm' in after:
            idx = i + 5
            continue
        # If explicitly mentions am near, good; if not, still acceptable (assume 24h 10:45)
        time_ok = True
        break
    # Also accept explicit ISO format like T10:45:..
    if not time_ok and 't10:45' in t:
        # check pm similarly
        pos = t.find('t10:45')
        after = t[pos:pos+12]
        if 'pm' not in after:
            time_ok = True
    return month_ok and time_ok

# Check if item is marked as all-day

def is_all_day(item):
    for k in ['allDay','allday','all_day']:
        v = item.get(k)
        if isinstance(v, bool) and v:
            return True
        if isinstance(v, str) and v.strip().lower() in ['true','yes','1']:
            return True
        if isinstance(v, dict):
            # some systems nest flags
            inner = v.get('value')
            if isinstance(inner, bool) and inner:
                return True
            if isinstance(inner, str) and inner.strip().lower() in ['true','yes','1']:
                return True
    return False


def main():
    if len(sys.argv) < 2:
        print('FAILURE')
        return
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    differences = data.get('differences') or {}
    items = collect_items(differences)

    found_match = False
    for it in items:
        content_text = extract_content_text(it)
        dt_text = extract_datetime_text(it)
        if is_all_day(it):
            # Must be time-specific at 10:45 AM, so all-day should not qualify
            continue
        if content_matches(content_text) and date_time_matches(dt_text):
            found_match = True
            break

    print('SUCCESS' if found_match else 'FAILURE')

if __name__ == '__main__':
    main()
