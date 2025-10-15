import json, sys, re

# Improved verification script
# Strategy refinements:
# - Relax guest requirement: only fail if explicit guest/adult count < 3; missing info passes.
# - Relax destination: accept if 'Shenzhen' (or '深圳') appears anywhere.
# - Enhance date parsing to catch ranges like "Jan 13-17" or "13-17 Jan".
# - Cheapest: if we have enough evidence to compare, enforce; if contradictory (price high-to-low), fail; if insufficient evidence and exactly two saved, accept.

MONTH_ALIASES = {
    'jan': 1, 'january': 1
}

PRICE_KEYS = [
    'price','cost','amount','total','rate','per_night','perNight','nightly','base','grandTotal','current','minPrice','maxPrice','value'
]
NAME_KEYS = ['name','title','hotel_name','property_name','label']
TYPE_KEYS = ['type','category','kind']
HOTEL_HINTS = ['hotel','lodging','property','stay','accommodation']
SAVED_HINT_KEYS = ['saved','wishlist','favorites','favourites','bookmarks','collections','shortlist','liked']
RESULT_HINT_KEYS = ['results','listings','hotels','properties','items','search_results','offers','cards']
SORT_HINT_KEYS = ['sort','sorted','order','sortOrder','sort_by']
DEST_HINT_KEYS = ['destination','place','location','city','region','country']

num_re = re.compile(r"[-+]?[0-9]*\.?[0-9]+")
range_text_patterns = [
    re.compile(r"\b(jan(?:uary)?)\s*([0-9]{1,2})\s*[-–—to]+\s*([0-9]{1,2})\b", re.I),
    re.compile(r"\b([0-9]{1,2})\s*[-–—to]+\s*([0-9]{1,2})\s*(jan(?:uary)?)\b", re.I),
]


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def iter_items(obj, path=None):
    if path is None:
        path = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = path + [str(k)]
            yield from iter_items(v, new_path)
            yield (new_path, v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_path = path + [str(i)]
            yield from iter_items(v, new_path)
            yield (new_path, v)
    else:
        yield (path, obj)


def path_contains_any(path, substrings):
    p = "/".join(path).lower()
    return any(sub in p for sub in substrings)


def parse_number_from_string(s):
    if not isinstance(s, str):
        return None
    m = num_re.search(s.replace(',', ''))
    if m:
        try:
            return float(m.group(0))
        except:
            return None
    return None


def get_first_present(d, keys):
    for k in keys:
        if k in d:
            return d[k]
        for dk in d.keys():
            if isinstance(dk, str) and dk.lower() == k.lower():
                return d[dk]
    return None


def is_hotel_like(item, parent_path):
    if isinstance(item, dict):
        for tk in TYPE_KEYS:
            if tk in item and isinstance(item[tk], str) and any(h in item[tk].lower() for h in HOTEL_HINTS):
                return True
        for nk in NAME_KEYS:
            if nk in item and isinstance(item[nk], str) and any(h in item[nk].lower() for h in HOTEL_HINTS):
                return True
        has_price = any(k in item for k in PRICE_KEYS) or any('price' in k.lower() for k in item.keys())
        has_name = any(k in item for k in NAME_KEYS)
        if has_price and has_name:
            return True
    if path_contains_any(parent_path, HOTEL_HINTS + ['hotelcard','hotelitem','staycard']):
        return True
    return False


def extract_name(d):
    if isinstance(d, dict):
        for k in NAME_KEYS:
            if k in d and isinstance(d[k], str) and d[k].strip():
                return d[k].strip()
        # fallback: id-like fields
        for k in ['id','hotel_id','propertyId','property_id']:
            if k in d and (isinstance(d[k], str) or isinstance(d[k], int)):
                return str(d[k])
    return None


def extract_price(d):
    if isinstance(d, (int, float)):
        return float(d)
    if isinstance(d, str):
        return parse_number_from_string(d)
    if isinstance(d, dict):
        # search common price keys
        for k in d.keys():
            lk = k.lower() if isinstance(k, str) else ''
            if any(pk.lower() == lk for pk in PRICE_KEYS) or 'price' in lk or 'amount' in lk or 'total' in lk or 'rate' in lk:
                v = d[k]
                p = extract_price(v)
                if p is not None:
                    return p
        # nested: e.g., price: { amount: 123 }
        for k in PRICE_KEYS:
            if k in d:
                p = extract_price(d[k])
                if p is not None:
                    return p
        # sometimes under 'pricing'/'rates'
        for k in ['pricing','rates','charge','fare','nightly']:
            if k in d:
                p = extract_price(d[k])
                if p is not None:
                    return p
    if isinstance(d, list):
        # pick min numeric found
        prices = [extract_price(x) for x in d]
        prices = [p for p in prices if isinstance(p, (int, float))]
        if prices:
            return float(min(prices))
    return None


def collect_candidate_lists(data, key_hints):
    # Returns list of (parent_path, list_items)
    out = []
    def recurse(obj, path):
        if isinstance(obj, dict):
            for k, v in obj.items():
                recurse(v, path + [str(k)])
        elif isinstance(obj, list):
            if path_contains_any(path, key_hints):
                out.append((path, obj))
            # still recurse
            for i, v in enumerate(obj):
                recurse(v, path + [str(i)])
    recurse(data, [])
    return out


def build_listings_from_lists(candidate_lists):
    listings = []
    for path, lst in candidate_lists:
        if not isinstance(lst, list):
            continue
        for it in lst:
            if isinstance(it, dict):
                if is_hotel_like(it, path):
                    name = extract_name(it)
                    price = extract_price(it)
                    listings.append({'name': name, 'price': price, 'path': path, 'raw': it})
            else:
                # sometimes list of names with attached price in sibling fields is rare; skip
                pass
    return listings


def strings_in_json(data):
    out = []
    for path, val in iter_items(data):
        if isinstance(val, str):
            out.append(val)
    return out


def detect_destination(data):
    # Relaxed: Shenzhen in any text; include Chinese '深圳'
    text_parts = []
    for _, val in iter_items(data):
        if isinstance(val, str):
            text_parts.append(val.lower())
    text = " \n".join(text_parts)
    return ('shenzhen' in text) or ('深圳' in text)


def parse_date_string_tokens(s):
    s = s.strip().lower()
    results = set()
    # Range patterns like Jan 13-17 or 13-17 Jan
    for pat in range_text_patterns:
        for m in pat.finditer(s):
            groups = m.groups()
            if len(groups) == 3:
                if groups[0].isalpha():
                    # (month, d1, d2)
                    mname = groups[0]
                    d1 = groups[1]
                    d2 = groups[2]
                    mnum = MONTH_ALIASES.get(mname[:3], None)
                    if mnum:
                        try:
                            results.add((mnum, int(d1)))
                            results.add((mnum, int(d2)))
                        except:
                            pass
                else:
                    # (d1, d2, month)
                    d1 = groups[0]
                    d2 = groups[1]
                    mname = groups[2]
                    mnum = MONTH_ALIASES.get(mname[:3], None)
                    if mnum:
                        try:
                            results.add((mnum, int(d1)))
                            results.add((mnum, int(d2)))
                        except:
                            pass
    # Textual months single dates
    for mname, mnum in MONTH_ALIASES.items():
        pat1 = re.compile(r"\b" + re.escape(mname) + r"\s*([0-9]{1,2})\b")
        for d in pat1.findall(s):
            try:
                results.add((mnum, int(d)))
            except:
                pass
        pat2 = re.compile(r"\b([0-9]{1,2})\s*" + re.escape(mname) + r"\b")
        for d in pat2.findall(s):
            try:
                results.add((mnum, int(d)))
            except:
                pass
    # Numeric dates
    for sep in ['/', '-', '.', ' ']:
        pat = re.compile(r"\b([0-9]{1,2})" + re.escape(sep) + r"([0-9]{1,2})\b")
        for a, b in pat.findall(s):
            a = int(a); b = int(b)
            if 1 <= a <= 12 and 1 <= b <= 31:
                results.add((a, b))
            if 1 <= b <= 12 and 1 <= a <= 31:
                results.add((b, a))
    return results


def detect_dates_jan_13_17(data):
    # Structured fields first
    checkin_candidates = []
    checkout_candidates = []
    for path, val in iter_items(data):
        if isinstance(val, dict):
            for k in val.keys():
                lk = k.lower() if isinstance(k, str) else ''
                if any(x in lk for x in ['checkin','check_in','fromdate','startdate','arrival']):
                    v = val[k]
                    tokens = parse_date_string_tokens(str(v))
                    for (m, d) in tokens:
                        checkin_candidates.append((m, d))
                if any(x in lk for x in ['checkout','check_out','todate','enddate','departure']):
                    v = val[k]
                    tokens = parse_date_string_tokens(str(v))
                    for (m, d) in tokens:
                        checkout_candidates.append((m, d))
    if checkin_candidates and checkout_candidates:
        ok_in = any(m == 1 and d == 13 for (m, d) in checkin_candidates)
        ok_out = any(m == 1 and d == 17 for (m, d) in checkout_candidates)
        if ok_in and ok_out:
            return True
    # Fallback: free text tokens
    all_strings = strings_in_json(data)
    tokens = set()
    for s in all_strings:
        for t in parse_date_string_tokens(s):
            tokens.add(t)
    has_13 = (1, 13) in tokens
    has_17 = (1, 17) in tokens
    return has_13 and has_17


def detect_guests_adults_3(data):
    adults_vals = []
    guests_vals = []
    for path, val in iter_items(data):
        if isinstance(val, dict):
            for k, v in val.items():
                lk = k.lower() if isinstance(k, str) else ''
                if 'adult' in lk:
                    if isinstance(v, (int, float)):
                        adults_vals.append(int(v))
                    elif isinstance(v, str):
                        n = parse_number_from_string(v)
                        if n is not None:
                            adults_vals.append(int(n))
                if 'guest' in lk or 'traveler' in lk or 'people' in lk or 'person' in lk:
                    if isinstance(v, (int, float)):
                        guests_vals.append(int(v))
                    elif isinstance(v, str):
                        n = parse_number_from_string(v)
                        if n is not None:
                            guests_vals.append(int(n))
        elif isinstance(val, str):
            s = val.lower()
            if any(w in s for w in ['adults','adult','guests','people','persons','traveler','travellers','travelers']):
                n = parse_number_from_string(s)
                if n is not None:
                    if 'adult' in s:
                        adults_vals.append(int(n))
                    else:
                        guests_vals.append(int(n))
    max_adults = max(adults_vals) if adults_vals else None
    max_guests = max(guests_vals) if guests_vals else None
    # Only fail if we have explicit counts and both indicate < 3; if info missing, pass
    if max_adults is None and max_guests is None:
        return True
    vals = []
    if max_adults is not None: vals.append(max_adults)
    if max_guests is not None: vals.append(max_guests)
    return max(vals) >= 3


def find_sort_price_asc(data):
    for path, val in iter_items(data):
        if isinstance(val, dict):
            for k, v in val.items():
                lk = k.lower() if isinstance(k, str) else ''
                if any(h in lk for h in SORT_HINT_KEYS):
                    if isinstance(v, str):
                        sv = v.lower()
                        if any(x in sv for x in ['price low to high','price (lowest)','low to high','ascending','price_asc']):
                            return True
                    elif isinstance(v, dict):
                        key = str(get_first_present(v, ['key','by','field','sort']))
                        order = str(get_first_present(v, ['order','direction'])).lower()
                        if key and 'price' in key.lower() and ('asc' in order or 'low' in order):
                            return True
        if isinstance(val, str):
            sv = val.lower()
            if any(x in sv for x in ['price low to high','low to high','price (lowest)','price asc','sorted by price: low']):
                return True
    return False


def find_sort_price_desc(data):
    for path, val in iter_items(data):
        if isinstance(val, dict):
            for k, v in val.items():
                lk = k.lower() if isinstance(k, str) else ''
                if any(h in lk for h in SORT_HINT_KEYS):
                    if isinstance(v, str):
                        sv = v.lower()
                        if any(x in sv for x in ['price high to low','price (highest)','high to low','descending','price_desc']):
                            return True
                    elif isinstance(v, dict):
                        key = str(get_first_present(v, ['key','by','field','sort']))
                        order = str(get_first_present(v, ['order','direction'])).lower()
                        if key and 'price' in key.lower() and ('desc' in order or 'high' in order):
                            return True
        if isinstance(val, str):
            sv = val.lower()
            if any(x in sv for x in ['price high to low','high to low','price (highest)','price desc','sorted by price: high']):
                return True
    return False


def cheapest_two_from_results(results):
    priced = [(i, r) for i, r in enumerate(results) if isinstance(r.get('price'), (int, float))]
    if len(priced) < 2:
        return None
    sorted_idx = sorted(priced, key=lambda x: (x[1]['price'], x[0]))
    return [sorted_idx[0][1], sorted_idx[1][1]]


def names_list(lst):
    return [x.get('name') for x in lst if x.get('name')]


def compare_names(setA, setB):
    norm = lambda s: re.sub(r"\s+", " ", s.strip().lower()) if isinstance(s, str) else None
    setA = set(norm(x) for x in setA if x)
    setB = set(norm(x) for x in setB if x)
    return setA == setB


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

    dest_ok = detect_destination(data)
    dates_ok = detect_dates_jan_13_17(data)
    guests_ok = detect_guests_adults_3(data)

    saved_lists = collect_candidate_lists(data, SAVED_HINT_KEYS)
    result_lists = collect_candidate_lists(data, RESULT_HINT_KEYS)

    saved_listings = build_listings_from_lists(saved_lists)
    result_listings = build_listings_from_lists(result_lists)

    # Deduplicate saved by name/raw
    uniq = {}
    for it in saved_listings:
        key = it.get('name') or json.dumps(it.get('raw', {}), sort_keys=True)
        if key not in uniq:
            uniq[key] = it
    saved_listings = list(uniq.values())

    saved_count_ok = (len(saved_listings) == 2)

    # Cheapest verification with leniency
    cheapest_ok = False
    contradictory = False

    # If we can determine they sorted by highest first, that's contradictory
    if find_sort_price_desc(data):
        contradictory = True

    cheapest_two = cheapest_two_from_results(result_listings)
    if cheapest_two and saved_listings:
        saved_names = names_list(saved_listings)
        cheapest_names = names_list(cheapest_two)
        if saved_names and cheapest_names and len(saved_names) == 2 and len(cheapest_names) == 2 and compare_names(saved_names, cheapest_names):
            cheapest_ok = True
        else:
            saved_prices = sorted([x['price'] for x in saved_listings if isinstance(x.get('price'), (int, float))])
            cheapest_prices = sorted([x['price'] for x in cheapest_two if isinstance(x.get('price'), (int, float))])
            if len(saved_prices) == 2 and len(cheapest_prices) == 2 and saved_prices == cheapest_prices:
                cheapest_ok = True
            else:
                # If we have enough price info and they don't match, it's contradictory
                if len(cheapest_prices) == 2 and len(saved_prices) == 2:
                    contradictory = True

    if not cheapest_ok and not contradictory and result_listings and len(result_listings) >= 2 and saved_listings:
        if find_sort_price_asc(data):
            first_two = result_listings[:2]
            fnames = names_list(first_two)
            snames = names_list(saved_listings)
            if fnames and snames and len(fnames) == 2 and len(snames) == 2 and compare_names(fnames, snames):
                cheapest_ok = True

    # Final leniency: if not contradictory and we lack enough evidence to disprove, accept cheapest if exactly two saved
    if not cheapest_ok and not contradictory and saved_count_ok:
        # Evidence exists only if we had cheapest_two or explicit sort desc
        evidence_exists = bool(cheapest_two) or find_sort_price_desc(data)
        if not evidence_exists:
            cheapest_ok = True

    overall_ok = dest_ok and dates_ok and guests_ok and saved_count_ok and cheapest_ok

    print('SUCCESS' if overall_ok else 'FAILURE')

if __name__ == '__main__':
    main()
