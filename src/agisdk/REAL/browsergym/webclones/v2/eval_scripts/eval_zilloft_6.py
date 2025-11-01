import sys, json

# Verification logic:
# - Find any contact/tour request entries containing selectedDate with date and time
# - Success if any entry has date on July 19 and time around 1 PM (12:00 PM to 2:00 PM inclusive)
# - Otherwise Failure
# Rationale: Training successes show contact agent with selectedDate 2024-07-19 and time 1:00 PM; failures lack contact or have wrong date/time.


def parse_time_to_minutes(t):
    if not isinstance(t, str):
        return None
    s = t.strip()
    if not s:
        return None
    # Normalize spacing before AM/PM
    s_up = s.upper().replace('.', '')
    ampm = None
    # Ensure there's a space before AM/PM if missing (e.g., 1:00PM)
    if s_up.endswith('AM'):
        ampm = 'AM'
        core = s_up[:-2].strip()
    elif s_up.endswith('PM'):
        ampm = 'PM'
        core = s_up[:-2].strip()
    else:
        # If no AM/PM marker, cannot confidently parse in this context
        return None
    # Split hours and minutes
    if ':' in core:
        hh_str, mm_str = core.split(':', 1)
        # If minutes include extra, trim non-digits
        mm = ''
        for ch in mm_str:
            if ch.isdigit():
                mm += ch
            else:
                break
        if mm == '':
            mm = '0'
        try:
            hh = int(hh_str.strip())
            mi = int(mm)
        except:
            return None
    else:
        try:
            hh = int(core)
            mi = 0
        except:
            return None
    if not (1 <= hh <= 12) or not (0 <= mi < 60):
        return None
    # Convert to 24h minutes
    if ampm == 'AM':
        if hh == 12:
            hh = 0
    else:  # PM
        if hh != 12:
            hh += 12
    return hh * 60 + mi


def is_july_19(date_str):
    if not isinstance(date_str, str):
        return False
    ds = date_str.strip()
    if not ds:
        return False
    # Prefer ISO-like: YYYY-MM-DD[...]
    # Extract date part before 'T' if present
    if 'T' in ds:
        ds_part = ds.split('T', 1)[0]
    else:
        ds_part = ds
    # Try YYYY-MM-DD
    if '-' in ds_part:
        parts = ds_part.split('-')
        if len(parts) >= 3:
            y, m, d = parts[0], parts[1], parts[2]
            try:
                m_i = int(m)
                d_i = int(d)
                return (m_i == 7 and d_i == 19)
            except:
                pass
    # Try MM/DD/YYYY
    if '/' in ds_part:
        parts = ds_part.split('/')
        if len(parts) >= 3:
            try:
                m_i = int(parts[0])
                d_i = int(parts[1])
                return (m_i == 7 and d_i == 19)
            except:
                pass
    # Fallback: substring heuristics
    if '07-19' in ds_part or '7-19' in ds_part or '07/19' in ds_part or '7/19' in ds_part:
        return True
    # Could be named month
    ds_upper = ds_part.upper()
    if 'JUL' in ds_upper and '19' in ds_upper:
        return True
    return False


def iter_dicts(obj):
    # Recursively yield all dicts within obj
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            for d in iter_dicts(v):
                yield d
    elif isinstance(obj, list):
        for item in obj:
            for d in iter_dicts(item):
                yield d


def find_selected_date_entries(data):
    entries = []
    # Look for structures with 'selectedDate' nested or as field
    for d in iter_dicts(data):
        # Case 1: contactAgentData contains selectedDate
        if 'contactAgentData' in d and isinstance(d['contactAgentData'], dict):
            cad = d['contactAgentData']
            if isinstance(cad.get('selectedDate'), dict):
                entries.append(cad['selectedDate'])
        # Case 2: selectedDate directly in dict
        if isinstance(d.get('selectedDate'), dict):
            entries.append(d['selectedDate'])
    return entries


def main():
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    # Collect all selectedDate dicts
    selected_dates = find_selected_date_entries(data)

    success_found = False
    for sd in selected_dates:
        date_val = sd.get('date')
        time_val = sd.get('time')
        if not date_val or not time_val:
            continue
        if not is_july_19(date_val):
            continue
        mins = parse_time_to_minutes(time_val)
        if mins is None:
            continue
        # Around 1 PM: accept 12:00 PM (720) to 2:00 PM (840) inclusive
        if 720 <= mins <= 840:
            success_found = True
            break

    print('SUCCESS' if success_found else 'FAILURE')

if __name__ == '__main__':
    main()
