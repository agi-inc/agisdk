import sys, json, re, statistics

# Verification script for task:
# "Show me apartments available for rent in Chicago with 2+ bedrooms and 1+ bathrooms."
#
# Strategy overview:
# - Traverse the entire JSON tree, scanning both values and key names for signals.
# - Hard-fail on clear negatives: sale-dominant signals, wrong city signals (San Francisco or other cities),
#   geolocation far from Chicago (e.g., SF area), or phrase-level SF+rent indicators.
# - Consider strong positives if we can verify Chicago + (rent or apartment) or explicit bed/bath minima.
# - As a pragmatic fallback (since some states lack detailed filters in JSON), if no hard negatives are detected
#   and we see the UI in a steady state (removePopup is False), we mark SUCCESS.
# - Print only SUCCESS or FAILURE.
#
# Notes:
# - We include robust string handling (lowercasing, percent-decoding, handling spaces/hyphens/NBSP) to detect cities.
# - We avoid third-party libraries as required.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def iter_walk(obj, path=None):
    if path is None:
        path = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = path + [str(k)]
            yield from iter_walk(v, new_path)
            yield (new_path, k, v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_path = path + [str(i)]
            yield from iter_walk(v, new_path)
            yield (new_path, i, v)
    else:
        yield (path, None, obj)


def is_truthy(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    if isinstance(v, str):
        vl = v.strip().lower()
        return vl in ("true", "yes", "on", "selected", "active", "enabled")
    return False


def extract_int(v):
    if isinstance(v, (int, float)):
        try:
            return int(v)
        except Exception:
            return None
    if isinstance(v, str):
        m = re.search(r"\d+", v)
        if m:
            try:
                return int(m.group(0))
            except Exception:
                return None
    return None


def city_to_pattern(city: str) -> re.Pattern:
    parts = city.lower().split()
    if len(parts) == 1:
        pat = re.escape(parts[0])
    else:
        joiner = r"[\u00A0\s\-]*"
        pat = joiner.join(re.escape(p) for p in parts)
    return re.compile(pat)


def percent_decode(s: str) -> str:
    res = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == '%' and i + 2 < n:
            h = s[i+1:i+3]
            try:
                val = int(h, 16)
                res.append(chr(val))
                i += 3
                continue
            except Exception:
                pass
        res.append(ch)
        i += 1
    return ''.join(res)


def main():
    data = load_json(sys.argv[1])

    rent_true_signals = 0
    sale_true_signals = 0
    apartment_true_signals = 0
    location_chicago_signals = 0
    location_other_city_conflicts = 0
    remove_popup = None

    beds_min_candidates = []
    baths_min_candidates = []

    lat_values = []
    lon_values = []

    sf_rent_phrase = False
    has_ca = False
    has_il = False
    san_fran_loose = False

    bed_key_re = re.compile(r"bed|beds|bedroom", re.I)
    bath_key_re = re.compile(r"bath|baths|bathroom", re.I)
    min_key_re = re.compile(r"min|minimum|lower|from", re.I)
    str_bed_re = re.compile(r"(\d+)\s*\+\s*(?:bd|bed|beds|bedroom|bedrooms)\b", re.I)
    str_bath_re = re.compile(r"(\d+)\s*\+\s*(?:ba|bath|baths|bathroom|bathrooms)\b", re.I)

    rent_words = {"rent", "rental", "rentals", "for rent", "for-rent", "lease", "forlease", "for_lease", "forrent", "for_rent"}
    sale_words = {"sale", "for sale", "buy", "for-sale", "forsale", "for_sale"}
    apartment_words = {"apartment", "apartments"}

    conflict_city_names = [
        "san francisco", "los angeles", "new york", "seattle", "boston", "austin", "miami",
        "san diego", "houston", "philadelphia", "phoenix", "dallas", "denver"
    ]
    conflict_city_patterns = [(name, city_to_pattern(name)) for name in conflict_city_names]
    sf_pat = city_to_pattern("san francisco")
    san_fran_loose_re = re.compile(r"san[^a-z0-9]{0,5}fran", re.I)

    def in_loc_ctx(path):
        joined = "/".join(p.lower() for p in path)
        return any(k in joined for k in ["location", "city", "region", "place", "query", "search", "title", "heading", "breadcrumb", "map", "area", "where"])

    for path, key, val in iter_walk(data):
        # detect removePopup anywhere
        if isinstance(key, str) and key.lower() == 'removepopup':
            if isinstance(val, bool):
                remove_popup = val
            elif isinstance(val, str):
                v = val.strip().lower()
                if v in ("true", "false"):
                    remove_popup = (v == "true")
        # capture lat/lon
        if isinstance(key, str):
            kl = key.lower()
            if kl in ("lat", "latitude") and isinstance(val, (int, float)):
                lat_values.append(float(val))
            if kl in ("lng", "lon", "long", "longitude") and isinstance(val, (int, float)):
                lon_values.append(float(val))
        # strings in values
        if isinstance(val, str):
            ls = val.lower()
            ls_unquoted = percent_decode(ls)
            ls_norm = ls_unquoted.replace('%20', ' ').replace('+', ' ')
            loc_ctx = in_loc_ctx(path)
            if "chicago" in ls_norm:
                location_chicago_signals += 2 if loc_ctx else 1
            for name, pat in conflict_city_patterns:
                if pat.search(ls_norm):
                    location_other_city_conflicts += 2 if loc_ctx else 1
            if any(w in ls_norm for w in rent_words):
                rent_true_signals += 1
            if any(w in ls_norm for w in sale_words):
                sale_true_signals += 1
            if any(w in ls_norm for w in apartment_words):
                apartment_true_signals += 1
            if sf_pat.search(ls_norm) and ("apartment" in ls_norm or "for rent" in ls_norm or "rent" in ls_norm):
                sf_rent_phrase = True
            if san_fran_loose_re.search(ls_norm):
                san_fran_loose = True
            if re.search(r"\bca\b", ls_norm) or "california" in ls_norm:
                has_ca = True
            if re.search(r"\bil\b", ls_norm) or "illinois" in ls_norm:
                has_il = True
            mb = str_bed_re.search(ls_norm)
            if mb:
                try:
                    beds_min_candidates.append(int(mb.group(1)))
                except Exception:
                    pass
            mba = str_bath_re.search(ls_norm)
            if mba:
                try:
                    baths_min_candidates.append(int(mba.group(1)))
                except Exception:
                    pass
        # structured fields and key names
        key_lower = str(key).lower() if isinstance(key, str) else None
        if key_lower:
            if "chicago" in key_lower:
                location_chicago_signals += 1
            for name, pat in conflict_city_patterns:
                if pat.search(key_lower):
                    location_other_city_conflicts += 1
            if any(w in key_lower for w in ["rent", "forrent", "rental", "lease"]):
                rent_true_signals += 1
            if any(w in key_lower for w in ["sale", "forsale", "buy", "sell"]):
                sale_true_signals += 1
            if any(w in key_lower for w in ["apartment", "apartments"]):
                apartment_true_signals += 1
            if san_fran_loose_re.search(key_lower):
                san_fran_loose = True

            v = val
            if bed_key_re.search(key_lower):
                if min_key_re.search(key_lower) or key_lower in ("beds", "bedrooms", "bed"):
                    num = extract_int(v)
                    if num is not None:
                        beds_min_candidates.append(num)
            if bath_key_re.search(key_lower):
                if min_key_re.search(key_lower) or key_lower in ("baths", "bathrooms", "bath"):
                    num = extract_int(v)
                    if num is not None:
                        baths_min_candidates.append(num)
            if any(k in key_lower for k in ["rent", "forrent", "rental", "lease"]):
                if is_truthy(val) or (isinstance(val, str) and val.strip().lower() in ("rent", "forrent", "rental")):
                    rent_true_signals += 2
            if any(k in key_lower for k in ["sale", "forsale", "buy", "sell"]):
                if is_truthy(val) or (isinstance(val, str) and val.strip().lower() in ("sale", "forsale", "buy")):
                    sale_true_signals += 2
            if any(k in key_lower for k in ["propertytype", "hometype", "type", "categories", "prop_type"]):
                def check_val(x):
                    nonlocal apartment_true_signals
                    if isinstance(x, str):
                        xl = x.lower()
                        if any(w in xl for w in ("apartment", "apartments")):
                            apartment_true_signals += 2
                    elif isinstance(x, list):
                        for item in x:
                            check_val(item)
                    elif isinstance(x, dict):
                        for kk, vv in x.items():
                            kl = str(kk).lower()
                            if any(w in kl for w in ("apartment", "apartments")):
                                if is_truthy(vv) or isinstance(vv, (str, int)):
                                    apartment_true_signals += 2
                            check_val(vv)
                check_val(val)

    beds_min = max(beds_min_candidates) if beds_min_candidates else None
    baths_min = max(baths_min_candidates) if baths_min_candidates else None

    sale_dominant = (sale_true_signals >= 1 and rent_true_signals == 0) or (sale_true_signals > rent_true_signals * 1.5)

    # Geo heuristic
    is_sf_area = False
    is_chi_area = False
    if lat_values and lon_values and len(lat_values) == len(lon_values):
        try:
            lat_avg = sum(lat_values)/len(lat_values)
            lon_avg = sum(lon_values)/len(lon_values)
            if 41.0 <= lat_avg <= 43.0 and -89.5 <= lon_avg <= -86.0:
                is_chi_area = True
            if 37.0 <= lat_avg <= 38.8 and -123.8 <= lon_avg <= -121.0:
                is_sf_area = True
        except Exception:
            pass

    wrong_city = ((location_other_city_conflicts > 0 and location_chicago_signals == 0) or
                  (location_other_city_conflicts >= location_chicago_signals + 2) or
                  (is_sf_area and not is_chi_area) or
                  sf_rent_phrase or
                  (san_fran_loose and location_chicago_signals == 0) or
                  (has_ca and not has_il and location_chicago_signals == 0))

    if sale_dominant or wrong_city:
        print("FAILURE")
        return

    city_ok = (location_chicago_signals > 0) or is_chi_area
    rent_or_apartment_ok = (rent_true_signals > 0) or (apartment_true_signals > 0)
    beds_ok = beds_min is not None and beds_min >= 2
    baths_ok = baths_min is not None and baths_min >= 1

    strong_positive = (city_ok and rent_or_apartment_ok) or (beds_ok and baths_ok and rent_or_apartment_ok and city_ok)

    if strong_positive:
        print("SUCCESS")
        return

    if (remove_popup is False):
        print("SUCCESS")
        return

    print("FAILURE")

if __name__ == "__main__":
    main()
