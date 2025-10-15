import json, sys, re

# Strategy in code:
# - Load final_state_diff.json and search specifically within 'differences.bookedFlights' and 'differences.purchaseDetails'.
# - For any nested objects in those sections, attempt to verify three constraints:
#   1) Route: Origin is Atlanta (ATL) and Destination is Houston (IAH or HOU)
#   2) Date: Outbound date is July 31 (any year)
#   3) Price: A parsable price <= 400 USD (accept various key names and formats)
# - Only print SUCCESS if all three constraints are met for at least one booked/confirmed flight; otherwise print FAILURE.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def strish(x):
    if isinstance(x, str):
        return x
    if isinstance(x, (int, float)):
        return str(x)
    return None


# Helpers for matching origin/destination, date, price
ATL_TOKENS = {"ATL", "ATLANTA"}
HOU_TOKENS = {"HOU", "IAH", "HOUSTON"}


def text_has_any_token(text, tokens):
    if not isinstance(text, str):
        return False
    t = text.upper()
    for tok in tokens:
        if tok in t:
            return True
    return False


def values_match_origin(values):
    for v in values:
        s = strish(v)
        if s and text_has_any_token(s, ATL_TOKENS):
            return True
    return False


def values_match_destination(values):
    for v in values:
        s = strish(v)
        if s and text_has_any_token(s, HOU_TOKENS):
            return True
    return False


# Date parsing: accept July 31 in many forms: "July 31", "Jul 31", "07/31", "7/31", "YYYY-07-31", "31 Jul", etc.
DATE_PATTERNS = [
    re.compile(r"\b(?:jul|july)\s*[-,/ ]?\s*31\b", re.I),
    re.compile(r"\b31\s*[-,/ ]?\s*(?:jul|july)\b", re.I),
    re.compile(r"\b0?7[\/-]31\b"),
    re.compile(r"\b\d{4}-07-31\b"),
    re.compile(r"\b07-31-\d{4}\b"),
    re.compile(r"\b07/31/\d{2,4}\b"),
]

def is_july_31_string(s):
    if not isinstance(s, str):
        return False
    for pat in DATE_PATTERNS:
        if pat.search(s):
            return True
    return False


def any_value_is_july_31(values):
    for v in values:
        if isinstance(v, (list, tuple)):
            if any(is_july_31_string(strish(x)) for x in v):
                return True
        s = strish(v)
        if s and is_july_31_string(s):
            return True
    return False


# Collect values for key names indicating origin/destination/date/price
ORIGIN_KEYS = {"from", "origin", "departure", "depart", "leavingfrom", "leaving", "fromairport", "departingcity", "originairport", "departairport", "outboundfrom"}
DEST_KEYS   = {"to", "destination", "arrival", "arrive", "goingto", "going", "toairport", "arrivingcity", "destinationairport", "arriveairport", "outboundto"}
DATE_KEYS   = {"date", "departdate", "departuredate", "outbounddate", "leavedate", "traveldate", "startdate", "flightdate", "dateoutbound", "dates"}
# Price keys ordered by likelihood; avoid generic 'total' unless nothing else found
PRICE_KEYS_PRIORITY = ["price","totalprice","amount","fare","cost","grandtotal","finalprice","total_amount","subtotal","total"]


def collect_values_for_keys(obj, keys_set):
    values = []
    def rec(o):
        if isinstance(o, dict):
            for k, v in o.items():
                kl = k.lower()
                if kl in keys_set:
                    values.append(v)
                # Recurse regardless to discover nested structures like {origin: {code:"ATL"}}
                rec(v)
        elif isinstance(o, list):
            for it in o:
                rec(it)
    rec(obj)
    return values


num_re = re.compile(r"(?<![A-Za-z])\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)")

def extract_best_price(obj):
    """Return the smallest plausible price found in the object based on prioritized price keys.
    Returns float or None if not found.
    """
    found_prices = []
    # First pass: by prioritized keys
    if isinstance(obj, dict):
        for key in PRICE_KEYS_PRIORITY:
            for k, v in obj.items():
                if k.lower() == key:
                    # Extract number from v (could be nested)
                    vals = []
                    if isinstance(v, (list, tuple)):
                        vals = v
                    else:
                        vals = [v]
                    for val in vals:
                        if isinstance(val, (int, float)):
                            found_prices.append(float(val))
                        else:
                            s = strish(val)
                            if s:
                                m = num_re.search(s)
                                if m:
                                    try:
                                        n = float(m.group(1).replace(',', ''))
                                        found_prices.append(n)
                                    except:
                                        pass
            # If we found any price for a high-priority key, continue to next key but keep all
    # Second pass: scan entire object strings as fallback (avoid too generic, but useful)
    def rec_scan(o):
        if isinstance(o, dict):
            for k, v in o.items():
                rec_scan(v)
        elif isinstance(o, list):
            for it in o:
                rec_scan(it)
        else:
            s = strish(o)
            if s:
                m = num_re.search(s)
                if m:
                    try:
                        n = float(m.group(1).replace(',', ''))
                        found_prices.append(n)
                    except:
                        pass
    # Do not perform broad fallback until needed
    if not found_prices:
        rec_scan(obj)
    if not found_prices:
        return None
    # Heuristic: filter out suspiciously tiny integers like 1,2,3 that are unlikely to be prices
    plausible = [p for p in found_prices if p >= 20.0]  # airline prices rarely < $20
    if not plausible:
        plausible = found_prices
    return min(plausible)


def object_matches_constraints(obj):
    # Gather origin/destination/date values by key hints
    origin_vals = collect_values_for_keys(obj, ORIGIN_KEYS)
    dest_vals   = collect_values_for_keys(obj, DEST_KEYS)
    date_vals   = collect_values_for_keys(obj, DATE_KEYS)

    # Check route
    origin_ok = values_match_origin(origin_vals)
    dest_ok   = values_match_destination(dest_vals)

    # If explicit keys didn't find, attempt a lenient fallback by scanning object sections
    if not origin_ok:
        # Search for any strings under fields likely about origin
        origin_ok = values_match_origin([obj])
    if not dest_ok:
        dest_ok = values_match_destination([obj])

    if not (origin_ok and dest_ok):
        return False

    # Check date
    date_ok = any_value_is_july_31(date_vals)
    if not date_ok:
        # fallback: scan any string in object
        date_ok = any_value_is_july_31([obj])
    if not date_ok:
        return False

    # Check price <= 400
    price = extract_best_price(obj)
    if price is None:
        return False
    if price <= 400.0 + 1e-6:  # allow tiny float tolerance
        return True
    return False


def traverse_candidates(obj, path=()):
    """Yield dict objects that are under bookedFlights or purchaseDetails contexts."""
    candidates = []
    def rec(o, pth):
        if isinstance(o, dict):
            # Determine if current path is within a relevant context
            path_str = "/".join(pth).lower()
            relevant = any(seg in path_str for seg in ["bookedflights", "purchasedetails", "confirmation", "bookingconfirmation"])
            if relevant:
                candidates.append(o)
            for k, v in o.items():
                rec(v, pth + (str(k),))
        elif isinstance(o, list):
            for idx, it in enumerate(o):
                rec(it, pth + (f"[{idx}]",))
    rec(obj, path)
    return candidates


def get_section(obj, keys):
    cur = obj
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def main():
    path = sys.argv[1]
    data = load_json(path)

    # Focus on 'differences' which should reflect final changes like booked flights and purchase details
    diffs = data.get("differences", {})

    # Build a composite object that includes potential sources: bookedFlights and purchaseDetails (added/updated)
    search_roots = []
    for key in ["bookedFlights", "purchaseDetails"]:
        section = diffs.get(key)
        if isinstance(section, dict):
            for sub in ["added", "updated"]:
                if sub in section and section[sub]:
                    search_roots.append(section[sub])

    # As a fallback, also consider initialfinaldiff for relevant sections (in case some systems record there)
    initialfinal = data.get("initialfinaldiff", {})
    if isinstance(initialfinal, dict):
        # Only include subtrees that contain relevant keywords to avoid overfitting
        added = initialfinal.get("added", {})
        updated = initialfinal.get("updated", {})
        for subtree in [added, updated]:
            # Filter subtree to only parts that mention bookedFlights or purchaseDetails
            # If not present, we ignore to avoid false positives from mere search forms
            s = json.dumps(subtree).lower() if subtree else ""
            if ("bookedflights" in s) or ("purchasedetails" in s) or ("confirmation" in s):
                search_roots.append(subtree)

    # Traverse candidates within relevant contexts
    any_success = False
    for root in search_roots:
        candidates = traverse_candidates(root)
        for obj in candidates:
            try:
                if object_matches_constraints(obj):
                    any_success = True
                    break
            except Exception:
                # Ignore malformed nodes and continue
                pass
        if any_success:
            break

    print("SUCCESS" if any_success else "FAILURE")

if __name__ == "__main__":
    main()
