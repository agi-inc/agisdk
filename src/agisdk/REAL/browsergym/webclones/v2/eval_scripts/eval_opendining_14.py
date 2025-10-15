import sys, json, re

# Strategy in code:
# - Parse the entire final_state_diff JSON and recursively scan all keys/values.
# - SUCCESS requires all: location contains 'Embarcadero'; party size indicates 3 people;
#   date corresponds to September 17 (any year, various formats); and a menu view is detected (e.g., viewFullMenu == True).
# - Otherwise, print FAILURE. Robust against missing fields and different placements in the JSON.

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def iter_items(obj):
    stack = [obj]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for k, v in current.items():
                yield (k, v)
                stack.append(v)
        elif isinstance(current, list):
            for v in current:
                yield (None, v)
                stack.append(v)
        else:
            # primitive
            yield (None, current)


def collect_values(obj):
    strings = []
    numbers = []
    booleans = []
    # for targeted key checks
    key_values = []  # list of (key, value)

    for k, v in iter_items(obj):
        if isinstance(v, str):
            strings.append(v)
        elif isinstance(v, (int, float)):
            numbers.append(v)
        elif isinstance(v, bool):
            booleans.append(v)
        # track key-values for logic on specific keys
        if k is not None:
            key_values.append((str(k), v))
    return strings, numbers, booleans, key_values


def has_location_Embarcadero(strings, key_values):
    # Search for 'Embarcadero' in any string value or in key-associated strings
    for s in strings:
        if isinstance(s, str) and 'embarcadero' in s.lower():
            return True
    for k, v in key_values:
        if isinstance(v, str) and 'embarcadero' in v.lower():
            return True
    return False


def has_party_size_3(strings, key_values, numbers):
    # Check targeted keys like 'guests', 'party', 'people', 'diners'
    key_patterns = ('guest', 'guests', 'party', 'people', 'diners', 'covers', 'size')
    for k, v in key_values:
        kl = k.lower()
        if any(p in kl for p in key_patterns):
            if isinstance(v, (int, float)) and int(v) == 3:
                return True
            if isinstance(v, str):
                vs = v.strip().lower()
                if re.search(r"\b3\s*(people|persons|guests|diners|covers|pax)\b", vs):
                    return True
                # common UI strings like "for 3"
                if re.search(r"\bfor\s*3\b", vs):
                    return True
                # exact '3' in a guest string
                if vs == '3' or vs == '3 people':
                    return True
    # Fallback: look across any string
    for s in strings:
        sl = s.lower()
        if re.search(r"\b3\s*(people|persons|guests|diners|covers|pax)\b", sl):
            return True
        if re.search(r"\bparty\s*of\s*3\b", sl):
            return True
        if re.search(r"\bfor\s*3\b", sl):
            return True
    # Numeric fallback if explicitly present with nearby hint (less reliable, so ignore to reduce false positives)
    return False


def is_sep_17_in_string(s: str) -> bool:
    sl = s.lower()
    # Month name variants
    if re.search(r"\b(sep|sept|september)\s*17\b", sl):
        return True
    if re.search(r"\b17\s*(sep|sept|september)\b", sl):
        return True
    # Numeric date patterns MM/DD or MM-DD
    if re.search(r"\b(9|09)[/\-]17\b", sl):
        return True
    # ISO-like YYYY-MM-DD (optionally with time)
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", s)
    if m:
        month = m.group(2)
        day = m.group(3)
        if month == '09' and day == '17':
            return True
    m2 = re.search(r"\b(\d{4})-(\d{2})-(\d{2})T", s)
    if m2:
        month = m2.group(2)
        day = m2.group(3)
        if month == '09' and day == '17':
            return True
    return False


def has_date_sep_17(strings, key_values):
    for s in strings:
        if isinstance(s, str) and is_sep_17_in_string(s):
            return True
    for k, v in key_values:
        if isinstance(v, str) and is_sep_17_in_string(v):
            return True
    return False


def count_view_full_menu_true(key_values):
    cnt = 0
    for k, v in key_values:
        kl = k.lower().replace('_', '')
        if kl == 'viewfullmenu' and v is True:
            cnt += 1
    return cnt


def detect_menu_presence(strings, key_values):
    # Primary: explicit flag(s)
    cnt = count_view_full_menu_true(key_values)
    if cnt >= 1:
        return True, cnt
    # Secondary heuristic: strings containing phrases indicating menu view
    menu_hits = 0
    for s in strings:
        sl = s.lower()
        # avoid generic 'menu' that could be navigation; look for 'full menu' or 'view menu'
        if 'full menu' in sl or 'view menu' in sl or 'menus' in sl:
            menu_hits += 1
    return (menu_hits >= 1), menu_hits


def main():
    path = sys.argv[1]
    try:
        data = load_json(path)
    except Exception:
        print('FAILURE')
        return

    # Work across the whole document (not just a single node)
    strings, numbers, booleans, key_values = collect_values(data)

    has_loc = has_location_Embarcadero(strings, key_values)
    has_party3 = has_party_size_3(strings, key_values, numbers)
    has_date = has_date_sep_17(strings, key_values)
    menu_present, menu_count = detect_menu_presence(strings, key_values)

    # Strict success criteria
    if has_loc and has_party3 and has_date and menu_present:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
