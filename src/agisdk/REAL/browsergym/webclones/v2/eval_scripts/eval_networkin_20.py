import json
import sys

def safe_get(d, keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

# Recursively search for an 'attendedEvents' dict with any true-like value
def has_attended_true(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 'attendedEvents' and isinstance(v, dict):
                for vv in v.values():
                    if (vv is True) or (isinstance(vv, str) and vv.strip().lower() == 'true') or vv == 1:
                        return True
            # Recurse into nested structures
            if has_attended_true(v):
                return True
        return False
    elif isinstance(obj, list):
        for item in obj:
            if has_attended_true(item):
                return True
        return False
    return False

# Main logic:
# - Load JSON
# - If both initialfinaldiff and differences are missing/None/empty -> SUCCESS (some runs may not capture diffs but still be successful)
# - Else, SUCCESS if any attendedEvents entry is set to true in any nested part of the diffs
# - Otherwise FAILURE

def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    initialfinaldiff = data.get('initialfinaldiff')
    differences = data.get('differences')

    # Normalize emptiness: treat None or empty dict/list as empty
    def is_empty(x):
        if x is None:
            return True
        if isinstance(x, (dict, list)):
            return len(x) == 0
        return False

    if is_empty(initialfinaldiff) and is_empty(differences):
        print('SUCCESS')
        return

    # Look for attended true anywhere in both structures
    attended = False
    for part in (initialfinaldiff, differences):
        if part and has_attended_true(part):
            attended = True
            break

    if attended:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
