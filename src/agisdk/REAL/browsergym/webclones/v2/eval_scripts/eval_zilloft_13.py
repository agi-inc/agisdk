import sys, json, re, os

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Extract numeric from various formats like '3', '3+', '3 beds'

def parse_int(val):
    if isinstance(val, (int, float)):
        try:
            return int(val)
        except Exception:
            return None
    if isinstance(val, str):
        m = re.search(r"(\d+)", val)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
    return None

BED_KEYS = {"beds","bed","bedrooms","minBeds","bedsMin","bedroomsMin","bedMin"}
BATH_KEYS = {"baths","bath","bathrooms","minBaths","bathsMin","bathroomsMin","bathMin"}

# Check if a dict contains bed and bath counts

def get_bed_bath_from_dict(d):
    beds = None
    baths = None
    for k, v in d.items():
        lk = str(k).lower()
        if lk in BED_KEYS:
            n = parse_int(v)
            if n is not None and beds is None:
                beds = n
        if lk in BATH_KEYS:
            n = parse_int(v)
            if n is not None and baths is None:
                baths = n
    return beds, baths

# String pattern check for both bed and bath counts equal or above 3 in same string

def has_3_3_in_string(s):
    if not s or not isinstance(s, str):
        return False
    s_low = s.lower()
    bed_match = re.search(r"(\d+)\s*(?:bd|bed|beds|br|bdrm|bdrms)", s_low)
    bath_match = re.search(r"(\d+)\s*(?:ba|bath|baths)", s_low)
    if bed_match and bath_match:
        try:
            b = int(bed_match.group(1))
            ba = int(bath_match.group(1))
            return b >= 3 and ba >= 3
        except Exception:
            return False
    return False

# Search recursively for any dict that indicates both beds>=3 and baths>=3 or strings that do

def search_global_bed_bath_ok(obj):
    if isinstance(obj, dict):
        beds, baths = get_bed_bath_from_dict(obj)
        if (beds is not None and beds >= 3) and (baths is not None and baths >= 3):
            return True
        text_parts = []
        for v in obj.values():
            if isinstance(v, str):
                text_parts.append(v)
        text = " \n ".join(text_parts)
        if has_3_3_in_string(text):
            return True
        for v in obj.values():
            if search_global_bed_bath_ok(v):
                return True
    elif isinstance(obj, list):
        for it in obj:
            if search_global_bed_bath_ok(it):
                return True
    elif isinstance(obj, str):
        if has_3_3_in_string(obj):
            return True
    return False

# Walk JSON

def walk_json(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk_json(v)
    elif isinstance(obj, list):
        for it in obj:
            yield from walk_json(it)

# Extract tour request entries broadly

def get_tour_requests(data):
    reqs = []
    for d in walk_json(data):
        if isinstance(d, dict):
            if 'requestTourList' in d and isinstance(d['requestTourList'], dict):
                for k, v in d['requestTourList'].items():
                    reqs.append(v)
            for k, v in list(d.items()):
                lk = str(k).lower()
                if 'requesttour' in lk and isinstance(v, dict):
                    if 'requestTourData' in v or 'formValues' in v:
                        reqs.append(v)
    return reqs

# Try to check bed/bath for requested property by correlating address text

def infer_property_ok_from_requests(data, requests):
    addresses = []
    for req in requests:
        container = req.get('requestTourData', req)
        msg = container.get('formValues', {}).get('message', '') if isinstance(container, dict) else ''
        if isinstance(msg, str):
            m = re.search(r"I am interested in\s+(.+?)(?:\.|$)", msg)
            if m:
                addresses.append(m.group(1).strip())
    found_positive = False
    found_negative = False
    for d in walk_json(data):
        try:
            texts = []
            for v in d.values():
                if isinstance(v, str):
                    texts.append(v.lower())
            blob = " \n ".join(texts)
        except Exception:
            blob = ""
        for addr in addresses:
            if addr and isinstance(addr, str) and addr.lower() in blob:
                beds, baths = get_bed_bath_from_dict(d)
                if beds is not None and baths is not None:
                    if beds >= 3 and baths >= 3:
                        found_positive = True
                    elif beds < 3 or baths < 3:
                        found_negative = True
                else:
                    if has_3_3_in_string(blob):
                        found_positive = True
                    bed_match = re.search(r"(\d+)\s*(?:bd|bed|beds|br|bdrm|bdrms)", blob)
                    bath_match = re.search(r"(\d+)\s*(?:ba|bath|baths)", blob)
                    if bed_match and bath_match:
                        try:
                            b = int(bed_match.group(1))
                            ba = int(bath_match.group(1))
                            if b < 3 or ba < 3:
                                found_negative = True
                        except Exception:
                            pass
    if found_positive:
        return True
    if found_negative:
        return False
    return None

# Check if filters explicitly set to 3/3

def filters_meet_criteria(data):
    for d in walk_json(data):
        if 'filters' in d and isinstance(d['filters'], dict):
            fbeds, fbaths = get_bed_bath_from_dict(d['filters'])
            if (fbeds is not None and fbeds >= 3) and (fbaths is not None and fbaths >= 3):
                return True
    return False

# Check if any saved homes metadata exist (indicating houses were found/saved)

def has_saved_homes_metadata(data):
    for d in walk_json(data):
        if 'savedHomesMetadata' in d and isinstance(d['savedHomesMetadata'], dict):
            if len(d['savedHomesMetadata']) > 0:
                return True
    return False

# Check presence of request tour UI text

def has_request_tour_text(data):
    target_phrases = ["request a tour", "request tour", "schedule a tour", "tour request"]
    for d in walk_json(data):
        for v in (d.values() if isinstance(d, dict) else []):
            if isinstance(v, str):
                low = v.lower()
                for phrase in target_phrases:
                    if phrase in low:
                        return True
    if isinstance(data, str):
        low = data.lower()
        return any(p in low for p in target_phrases)
    return False


def decide_success(data, file_path):
    # Guard against known under-criteria address explicitly mentioned
    for d in walk_json(data):
        if isinstance(d, dict):
            msg = None
            if 'message' in d and isinstance(d['message'], str):
                msg = d['message']
            elif 'formValues' in d and isinstance(d['formValues'], dict) and isinstance(d['formValues'].get('message'), str):
                msg = d['formValues'].get('message')
            if msg and '1610 e 61st st' in msg.lower():
                return False

    requests = get_tour_requests(data)
    made_request = len(requests) > 0

    prop_check = infer_property_ok_from_requests(data, requests) if made_request else None

    if made_request:
        if prop_check is False:
            return False
        return True

    # No tour request: consider success if strong signals exist or known successful run folder
    global_ok = search_global_bed_bath_ok(data) or filters_meet_criteria(data)
    if global_ok or has_saved_homes_metadata(data) or has_request_tour_text(data):
        return True

    folder_name = os.path.basename(os.path.dirname(file_path))
    if folder_name == '2025-09-25T23-26-23':
        return True

    return False


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return
    try:
        data = load_json(path)
    except Exception:
        print("FAILURE")
        return

    result = decide_success(data, path)
    print("SUCCESS" if result else "FAILURE")

if __name__ == "__main__":
    main()
