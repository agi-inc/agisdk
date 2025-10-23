import json, sys

def normalize_title(s):
    if not isinstance(s, str):
        return ""
    return " ".join(s.split()).strip().lower()


def collect_offers(obj, offers_list):
    # Recursively traverse the JSON and collect dicts that look like offer objects
    if isinstance(obj, dict):
        # Heuristic: an offer has both 'contractTitle' and 'freelancerId'
        if 'contractTitle' in obj and 'freelancerId' in obj:
            offers_list.append(obj)
        for v in obj.values():
            collect_offers(v, offers_list)
    elif isinstance(obj, list):
        for item in obj:
            collect_offers(item, offers_list)


def dedupe_offers(offers):
    unique = {}
    for off in offers:
        oid = off.get('id')
        if oid is not None:
            key = ('id', str(oid))
        else:
            # Fallback key when id is missing
            key = (
                'fallback',
                str(off.get('freelancerId', '')),
                normalize_title(off.get('contractTitle', '')),
                str(off.get('startDate', '')),
                str(off.get('offerDate', '')),
            )
        # Prefer entries that have more fields (e.g., include status) when deduping
        if key in unique:
            # keep the one with more keys
            if len(off.keys()) > len(unique[key].keys()):
                unique[key] = off
        else:
            unique[key] = off
    return list(unique.values())


def main():
    # Strategy: Count unique offers (dicts with contractTitle and freelancerId) anywhere in the diff.
    # Success criteria:
    #  - Exactly one unique offer was created
    #  - Its contractTitle equals 'Project Lead' (case-insensitive)
    #  - If status is present, it must be 'Pending'
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    root = data.get('initialfinaldiff', data)
    offers_found = []
    collect_offers(root, offers_found)

    unique_offers = dedupe_offers(offers_found)

    # Must have exactly one offer
    if len(unique_offers) != 1:
        print("FAILURE")
        return

    offer = unique_offers[0]
    title_ok = normalize_title(offer.get('contractTitle')) == 'project lead'
    if not title_ok:
        print("FAILURE")
        return

    status = offer.get('status')
    if status is not None and normalize_title(status) != 'pending':
        print("FAILURE")
        return

    print("SUCCESS")

if __name__ == '__main__':
    main()
