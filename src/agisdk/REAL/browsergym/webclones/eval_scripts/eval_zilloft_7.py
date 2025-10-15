import json, sys

# Verification script with pragmatic fallback
# Strategy:
# - Prefer verifying filters if we can detect them (location Charlotte NC, max price <= 900k, beds >=3, baths >=2)
# - If no filter evidence is detectable, fall back to checking that at least two homes were saved


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def find_nodes_by_key_substring(obj, substrings):
    results = []
    subs = [s.lower() for s in substrings]
    def rec(o):
        if isinstance(o, dict):
            for k, v in o.items():
                kl = str(k).lower()
                if any(s in kl for s in subs):
                    results.append(v)
                if isinstance(v, (dict, list)):
                    rec(v)
        elif isinstance(o, list):
            for it in o:
                rec(it)
    rec(obj)
    return results


def extract_saved_ids(data):
    ids = []
    root = data
    # Try multiple known places
    sh = root.get('initialfinaldiff', {}).get('added', {}).get('savedHomes', {})
    saved_map = sh.get('savedHomes')
    if isinstance(saved_map, dict):
        ids.extend([str(v) for v in saved_map.values() if v is not None])
    elif isinstance(saved_map, list):
        ids.extend([str(v) for v in saved_map if v is not None])
    diff_added = root.get('differences', {}).get('savedHomes', {}).get('added')
    if isinstance(diff_added, dict):
        ids.extend([str(v) for v in diff_added.values() if v is not None])
    elif isinstance(diff_added, list):
        ids.extend([str(v) for v in diff_added if v is not None])
    # unique
    seen = set()
    uniq = []
    for x in ids:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def parse_filters(data):
    # Try to parse filterState/searchQueryState like structures
    loc_ok = False
    price_ok = False
    beds_ok = False
    baths_ok = False

    # Collect candidate nodes
    candidates = []
    candidates += find_nodes_by_key_substring(data, ['filterstate', 'searchquerystate', 'searchstate', 'querystate', 'filters'])

    # Also scan entire JSON for location strings (sometimes stored outside filter nodes)
    def scan_strings(o):
        nonlocal loc_ok
        if isinstance(o, dict):
            for v in o.values():
                scan_strings(v)
        elif isinstance(o, list):
            for it in o:
                scan_strings(it)
        else:
            if isinstance(o, str):
                s = o.lower()
                if 'charlotte' in s and ('nc' in s or 'north carolina' in s):
                    loc_ok = True
    scan_strings(data)

    # Evaluate candidates for price/beds/baths and explicit location
    def eval_candidate(d):
        nonlocal loc_ok, price_ok, beds_ok, baths_ok
        if not isinstance(d, (dict, list)):
            return
        if isinstance(d, dict):
            # price structures
            for k, v in d.items():
                kl = str(k).lower()
                if kl == 'price' and isinstance(v, dict):
                    for kk, vv in v.items():
                        if str(kk).lower() in ('max', 'to', 'high') and is_number(vv) and 0 < vv <= 900000:
                            price_ok = True
                if is_number(v) and ('price' in kl and 'max' in kl) and 0 < float(v) <= 900000:
                    price_ok = True
                # beds/baths
                if is_number(v):
                    if (kl in ('beds', 'bedrooms', 'minbeds') or ('bed' in kl and 'min' in kl)) and float(v) >= 3:
                        beds_ok = True
                    if (kl in ('baths', 'bathrooms', 'minbaths') or ('bath' in kl and 'min' in kl)) and float(v) >= 2:
                        baths_ok = True
                if isinstance(v, (dict, list)):
                    eval_candidate(v)
        else:
            for it in d:
                eval_candidate(it)

    for d in candidates:
        eval_candidate(d)

    return loc_ok, price_ok, beds_ok, baths_ok


def main():
    data = load_json(sys.argv[1])
    saved_ids = extract_saved_ids(data)
    # success requires at least 2 saved homes
    saved_ok = len(saved_ids) >= 2

    # Attempt to validate via filters if present
    loc_ok, price_ok, beds_ok, baths_ok = parse_filters(data)

    # If any of the filter constraints are detectable, require all to be satisfied
    detected_any = loc_ok or price_ok or beds_ok or baths_ok

    if detected_any:
        if saved_ok and loc_ok and price_ok and beds_ok and baths_ok:
            print('SUCCESS')
        else:
            print('FAILURE')
    else:
        # No detectable filter info; classify based solely on saved homes count
        if saved_ok:
            print('SUCCESS')
        else:
            print('FAILURE')

if __name__ == '__main__':
    main()
