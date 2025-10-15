import json, sys

def get_path(d, path):
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur

# Extract potential application objects from a node that could be dict/list/mixed
# We only collect dict leaf nodes; non-dict entries are ignored.
def extract_candidate_dicts(node):
    candidates = []
    if node is None:
        return candidates
    if isinstance(node, dict):
        # If dict values are dicts, collect them
        for v in node.values():
            if isinstance(v, dict):
                candidates.append(v)
            elif isinstance(v, list):
                for e in v:
                    if isinstance(e, dict):
                        candidates.append(e)
    elif isinstance(node, list):
        for e in node:
            if isinstance(e, dict):
                candidates.append(e)
    return candidates

# Strategy in code:
# - Load final_state_diff.json and look under initialfinaldiff.added.ui.jobs for evidence of a new application.
# - Treat success only if we find at least one application object with applicantId == 'current-user' and with both 'id' and 'jobId' fields.
# - This avoids false positives from unrelated UI changes like likes, navigation, or filtered lists.

def is_success(data):
    root = data.get('initialfinaldiff', {})
    added = root.get('added', {}) if isinstance(root.get('added', {}), dict) else {}

    # Collect potential applications from both containers commonly used
    apps_node = get_path(added, ['ui', 'jobs', 'applications'])
    user_apps_node = get_path(added, ['ui', 'jobs', 'userApplications'])

    candidates = []
    candidates.extend(extract_candidate_dicts(apps_node))
    candidates.extend(extract_candidate_dicts(user_apps_node))

    # Validate candidates as real applications for the current user
    valid = []
    for app in candidates:
        if not isinstance(app, dict):
            continue
        applicant_id = app.get('applicantId')
        job_id = app.get('jobId')
        app_id = app.get('id')
        if applicant_id == 'current-user' and isinstance(job_id, (str, int)) and app_id:
            valid.append(app)

    return len(valid) > 0


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    if is_success(data):
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
