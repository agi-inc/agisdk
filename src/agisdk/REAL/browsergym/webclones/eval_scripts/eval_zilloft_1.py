import json, sys, re

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

# Parse time strings like "1 PM", "1:00 PM", "13:00" and determine if it's around 1 PM (i.e., within the 1 PM hour)
# Strategy: accept 12-hour format where hour == 1 and "PM"; also accept 24-hour times where hour == 13
# This aligns with "around 1pmish" while avoiding overfitting to exact minute values.
def is_time_around_1pm(tstr):
    if not isinstance(tstr, str):
        return False
    s = tstr.strip().upper()
    # 12-hour format
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(AM|PM)$", s)
    if m:
        hh = int(m.group(1))
        mm = int(m.group(2) or 0)
        ap = m.group(3)
        return ap == 'PM' and hh == 1
    # 24-hour format
    m2 = re.match(r"^(\d{1,2})(?::(\d{2}))$", s)
    if m2:
        hh = int(m2.group(1))
        # mm = int(m2.group(2) or 0)
        return hh == 13
    # Fallback: exact string match common variant
    return s == '1:00 PM' or s == '1 PM'


def collect_contact_entries(data):
    entries = []
    # Path 1: differences.contactAgents.added
    added = data.get('differences', {}).get('contactAgents', {}).get('added', {})
    if isinstance(added, dict):
        for _, v in added.items():
            if isinstance(v, dict):
                entries.append(v)
    # Path 2: initialfinaldiff.added.tourRequests.contactAgentList
    cl = data.get('initialfinaldiff', {}).get('added', {}).get('tourRequests', {}).get('contactAgentList', {})
    if isinstance(cl, dict):
        for _, v in cl.items():
            if isinstance(v, dict):
                entries.append(v)
    return entries


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

    entries = collect_contact_entries(data)

    # We require: a contact agent entry exists with a selected date of 2024-07-19 and time around 1 PM,
    # and formValues present to indicate an actual contact attempt.
    target_date_prefix = '2024-07-19'
    success = False
    for e in entries:
        cad = e.get('contactAgentData', {}) if isinstance(e, dict) else {}
        form_values = cad.get('formValues', {}) if isinstance(cad, dict) else {}
        selected = cad.get('selectedDate', {}) if isinstance(cad, dict) else {}
        date_str = selected.get('date') if isinstance(selected, dict) else None
        time_str = selected.get('time') if isinstance(selected, dict) else None

        if not isinstance(form_values, dict) or not form_values:
            continue
        if not isinstance(date_str, str) or not isinstance(time_str, str):
            continue

        date_ok = date_str.startswith(target_date_prefix)
        time_ok = is_time_around_1pm(time_str)
        if date_ok and time_ok:
            success = True
            break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
