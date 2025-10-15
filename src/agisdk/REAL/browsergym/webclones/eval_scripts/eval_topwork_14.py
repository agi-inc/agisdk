import json, sys

# Strategy:
# - Recursively search the JSON for consultation-like objects (with freelancerId, selectedDate, selectedTime).
# - For each, verify:
#   1) Date is 2024-07-23 and Time is 10:00
#   2) Title/agenda mentions frontend (frontend/front-end/front end) and iOS (case-insensitive)
#   3) The freelancer's role in the contact list shows UI/UX (job contains both 'ui' and 'ux' or 'ui/ux')
# - If any candidate meets all criteria, print SUCCESS, else FAILURE.

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Recursive traversal to find all dicts

def iter_nodes(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from iter_nodes(v)
    elif isinstance(node, list):
        for item in node:
            yield from iter_nodes(item)

# Identify consultation-like dicts

def is_consultation_dict(d):
    if not isinstance(d, dict):
        return False
    required_keys = {'freelancerId', 'selectedDate', 'selectedTime'}
    if not required_keys.issubset(d.keys()):
        return False
    # Heuristic: should look like a consultation object (have consultationTitle or freelancerName or status)
    extra_keys = {'consultationTitle', 'freelancerName', 'status', 'consultationPrice'}
    if not (extra_keys & set(d.keys())):
        return False
    return True

# Find job for a given freelancerId anywhere in the state

def find_job_for_freelancer(root, freelancer_id):
    job_vals = []
    for d in iter_nodes(root):
        if isinstance(d, dict):
            if d.get('id') == freelancer_id and 'job' in d:
                job_vals.append(d.get('job'))
    # Prefer a non-empty string and the most recent (last found in traversal of updated typically comes later)
    for j in reversed(job_vals):
        if isinstance(j, str) and j.strip():
            return j
    return None

# Text check for frontend + iOS intent

def content_mentions_frontend_ios(title, agenda):
    text = ' '.join([str(title or ''), str(agenda or '')]).lower()
    # Normalize common separators
    # Check for frontend synonyms
    frontend_ok = any(tok in text for tok in ['frontend', 'front-end', 'front end'])
    ios_ok = 'ios' in text  # accept any case
    return frontend_ok and ios_ok


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

    root = data

    # Gather all consultation candidates
    candidates = []
    for d in iter_nodes(root):
        if is_consultation_dict(d):
            candidates.append(d)

    # Validate candidates
    target_date = '2024-07-23'
    target_time = '10:00'

    def is_uiux_job(job_str):
        if not job_str or not isinstance(job_str, str):
            return False
        jl = job_str.lower()
        if 'ui/ux' in jl:
            return True
        # Also accept if both ui and ux words appear
        return ('ui' in jl and 'ux' in jl)

    success = False
    for c in candidates:
        date_ok = c.get('selectedDate') == target_date
        time_ok = c.get('selectedTime') == target_time
        title = c.get('consultationTitle')
        agenda = c.get('agenda')
        content_ok = content_mentions_frontend_ios(title, agenda)
        freelancer_id = c.get('freelancerId')
        job = find_job_for_freelancer(root, freelancer_id) if freelancer_id else None
        job_ok = is_uiux_job(job)

        if date_ok and time_ok and content_ok and job_ok:
            success = True
            break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
