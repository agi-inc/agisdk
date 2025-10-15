# Verification script for: NetworkIn: Follow 3 new companies to expand my feed
# Strategy:
# - Inspect initialfinaldiff under both 'added' and 'updated' for ui.follows.followedCompanies
# - Count unique companies with a truthy follow status; SUCCESS if count >= 3, else FAILURE

import sys, json

def safe_get_followed_companies(section_obj):
    if not isinstance(section_obj, dict):
        return {}
    ui = section_obj.get('ui', {})
    if not isinstance(ui, dict):
        return {}
    follows = ui.get('follows', {})
    if not isinstance(follows, dict):
        return {}
    fc = follows.get('followedCompanies', {})
    if not isinstance(fc, dict):
        return {}
    return fc

try:
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    initdiff = data.get('initialfinaldiff', {})

    followed_true = {}

    for section in ('added', 'updated'):
        sec_obj = initdiff.get(section, {})
        fc = safe_get_followed_companies(sec_obj)
        if isinstance(fc, dict):
            for company, val in fc.items():
                # Normalize truthiness (handle booleans or string equivalents)
                if isinstance(val, str):
                    v = val.strip().lower() in ("true", "1", "yes", "y")
                else:
                    v = bool(val)
                if v:
                    followed_true[company] = True
                else:
                    # Do not unset previously set True; we only care about positive follows
                    if company not in followed_true:
                        # explicitly not followed/false - ignore
                        pass

    count_followed = len(followed_true)

    if count_followed >= 3:
        print("SUCCESS")
    else:
        print("FAILURE")
except Exception:
    # On any error, default to FAILURE to avoid false positives
    print("FAILURE")
