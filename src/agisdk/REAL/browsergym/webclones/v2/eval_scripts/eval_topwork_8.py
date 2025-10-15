import json, sys

def get_path(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


def gather_offers(data):
    # Collect offers from offers.offers in both added and updated, deduplicated by id
    offer_map = {}
    paths = [
        ["initialfinaldiff", "updated", "offers", "offers"],
        ["initialfinaldiff", "added", "offers", "offers"],
    ]
    for path in paths:
        offers_dict = get_path(data, path, {})
        if isinstance(offers_dict, dict):
            for _, v in offers_dict.items():
                if isinstance(v, dict):
                    oid = v.get("id")
                    # If id missing, synthesize a stable key to avoid double counting within same state
                    if not oid:
                        oid = f"{v.get('freelancerId','')}_{v.get('contractTitle','')}_{v.get('startDate','') }"
                    if oid not in offer_map:
                        offer_map[oid] = v
    # Fallback: check message-level embedded offers if none found above
    if not offer_map:
        # scan both added and updated contactList for message-level offers
        for base in ("added", "updated"):
            contact_list = get_path(data, ["initialfinaldiff", base, "messages", "contactList"], {})
            if isinstance(contact_list, dict):
                for _, contact in contact_list.items():
                    if not isinstance(contact, dict):
                        continue
                    msgs = contact.get("messages")
                    # messages can be dict or list
                    iterable = []
                    if isinstance(msgs, dict):
                        iterable = list(msgs.values())
                    elif isinstance(msgs, list):
                        iterable = msgs
                    for msg in iterable:
                        if not isinstance(msg, dict):
                            continue
                        offer_obj = msg.get("offer")
                        if isinstance(offer_obj, dict):
                            oid = offer_obj.get("id") or f"{offer_obj.get('freelancerId','')}_{offer_obj.get('contractTitle','')}_{offer_obj.get('startDate','')}"
                            if oid not in offer_map:
                                offer_map[oid] = offer_obj
    return list(offer_map.values())


def is_success(data):
    # Strategy: exactly one offer with contractTitle "Project Lead" should exist; more or zero => failure.
    # If status field is present, it must be "Pending" to indicate offer sent (rehire flow), not accepted or something else.
    offers = gather_offers(data)
    project_lead_offers = []
    for o in offers:
        if not isinstance(o, dict):
            continue
        title = o.get("contractTitle")
        if isinstance(title, str) and title.strip().lower() == "project lead":
            project_lead_offers.append(o)
    # Exactly one project lead offer must be present
    if len(project_lead_offers) != 1:
        return False
    # Validate status if present
    status = project_lead_offers[0].get("status")
    if status is not None and str(status).strip().lower() != "pending":
        return False
    # Optional sanity: ensure this is an offer (has freelancerId and startDate or similar)
    # Not strictly required but avoids counting malformed entries
    o = project_lead_offers[0]
    if not o.get("freelancerId"):
        return False
    return True


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        # If JSON can't be read, fail
        print("FAILURE")
        return
    result = is_success(data)
    print("SUCCESS" if result else "FAILURE")

if __name__ == "__main__":
    main()
