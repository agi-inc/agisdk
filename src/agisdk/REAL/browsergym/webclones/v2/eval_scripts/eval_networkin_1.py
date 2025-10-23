import json, sys

def find_followed_companies(node, found):
    # Recursively find any 'followedCompanies' dicts
    if isinstance(node, dict):
        for k, v in node.items():
            if k == 'followedCompanies' and isinstance(v, dict):
                found.append(v)
            else:
                find_followed_companies(v, found)
    elif isinstance(node, list):
        for item in node:
            find_followed_companies(item, found)


def find_search_history_terms(node, terms):
    # Recursively find 'searchHistory' containers and extract 'searchTerm' values from them
    if isinstance(node, dict):
        for k, v in node.items():
            if k == 'searchHistory' and isinstance(v, (dict, list)):
                # v might be dict with numeric keys or a list
                if isinstance(v, dict):
                    iterable = v.values()
                else:
                    iterable = v
                for entry in iterable:
                    if isinstance(entry, dict):
                        st = entry.get('searchTerm')
                        if isinstance(st, str):
                            terms.append(st)
                # continue recursion as well in case nested
                find_search_history_terms(v, terms)
            else:
                find_search_history_terms(v, terms)
    elif isinstance(node, list):
        for item in node:
            find_search_history_terms(item, terms)


def main():
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Strategy:
    # 1) If any followedCompanies are present anywhere, require microsoft:true and at least one other company:true.
    # 2) If no followedCompanies present, accept success only if searchHistory includes a term containing 'microsoft'.

    fc_dicts = []
    find_followed_companies(data, fc_dicts)

    combined = {}
    for d in fc_dicts:
        for comp, val in d.items():
            # Normalize company key to lower for comparison/storage
            key = comp.lower() if isinstance(comp, str) else comp
            # Only consider explicit True values as followed
            if val is True:
                combined[key] = True
            else:
                # If previously marked True, keep it; else ignore non-True
                combined.setdefault(key, False)

    if combined:  # Explicit follow data present, treat as authoritative
        ms_followed = combined.get('microsoft', False) is True
        other_followed_count = sum(1 for k, v in combined.items() if v is True and k != 'microsoft')
        if ms_followed and other_followed_count >= 1:
            print('SUCCESS')
            return
        else:
            print('FAILURE')
            return

    # No explicit follows found; fall back to search history evidence for microsoft
    terms = []
    find_search_history_terms(data, terms)
    has_ms_search = any('microsoft' in t.lower() for t in terms if isinstance(t, str))

    if has_ms_search:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
