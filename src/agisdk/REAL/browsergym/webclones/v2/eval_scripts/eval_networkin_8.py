import sys, json

def get_nested(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur

# Strategy in code comments:
# - Load final_state_diff.json and locate ui.follows.followedCompanies.
# - Confirm 'microsoft' is followed (case-insensitive) and that total followed companies >= 2.
# - Print SUCCESS if both conditions hold; otherwise print FAILURE. Handle missing/invalid structures robustly.

def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # The structure typically keeps the diffs under 'initialfinaldiff' -> 'added' or 'updated'
        root = data.get('initialfinaldiff', data)
        # followedCompanies may appear under 'added' or 'updated' (prefer 'added' then fallback to 'updated')
        followed = None
        for top in ('added', 'updated'):
            container = root.get(top) if isinstance(root, dict) else None
            if isinstance(container, dict):
                fc = get_nested(container, ['ui', 'follows', 'followedCompanies'])
                if isinstance(fc, dict):
                    followed = fc
                    break
        if not isinstance(followed, dict):
            print("FAILURE")
            return
        # Normalize keys to lowercase and count only truthy values
        norm_items = [(str(k).lower(), bool(v)) for k, v in followed.items()]
        total_followed = sum(1 for k, v in norm_items if v)
        ms_followed = any((k == 'microsoft') and v for k, v in norm_items)
        if ms_followed and total_followed >= 2:
            print("SUCCESS")
        else:
            print("FAILURE")
    except Exception:
        # Any parsing/runtime issue -> treat as failure
        print("FAILURE")

if __name__ == '__main__':
    main()
