import json, sys

# Verification script for Topwork: Ensure a proper offer was sent and a valid offer message exists
# Strategy:
# 1) Confirm at least one structured offer exists in the state (offers.offers entries with id, contractTitle, freelancerId)
# 2) Confirm the conversation contains an offer message (message type == 'offer' or message contains an 'offer' object)
# SUCCESS only if both conditions are satisfied; otherwise FAILURE.

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Recursively traverse nested structures
def traverse(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            if isinstance(v, (dict, list)):
                for kv in traverse(v):
                    yield kv
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                for kv in traverse(item):
                    yield kv

# Detect offers in the global offers section (offers.offers)

def find_structured_offers(data):
    offers_found = []
    # Look for any dict whose values look like offer objects (id, contractTitle, freelancerId)
    def is_offer_obj(d):
        return (
            isinstance(d, dict)
            and 'id' in d
            and 'contractTitle' in d
            and 'freelancerId' in d
        )
    for (k, v) in traverse(data):
        # We specifically look for containers that are dicts with numeric/string keys mapping to offer dicts
        if isinstance(v, dict):
            # Heuristic: at least one child looks like an offer object
            candidate_offers = [vv for vv in v.values() if is_offer_obj(vv)]
            if candidate_offers:
                # Avoid counting unrelated structures by preferring likely paths (under a key named 'offers')
                # But still accept if structure matches strong offer signature
                parent_key = k
                # Accept regardless of parent key name since signature is strong
                offers_found.extend(candidate_offers)
    return offers_found

# Detect if an offer message exists in messages

def has_offer_message(data):
    offer_msg = False
    embedded_offer = False
    for (k, v) in traverse(data):
        if isinstance(v, dict):
            # type == 'offer' indicates a message record representing an offer
            if v.get('type') == 'offer':
                offer_msg = True
            # embedded offer object inside a message
            if 'offer' in v and isinstance(v['offer'], dict):
                # validate embedded offer has required keys
                o = v['offer']
                if all(x in o for x in ('id', 'contractTitle', 'freelancerId')):
                    embedded_offer = True
    return offer_msg or embedded_offer


def main():
    path = sys.argv[1]
    data = load_json(path)

    # Some states wrap content under different roots; unify by scanning full JSON
    offers_list = find_structured_offers(data)
    # Filter to ensure these are truly offers and not empty placeholders
    offers_list = [o for o in offers_list if isinstance(o.get('id'), str) and isinstance(o.get('contractTitle'), str) and isinstance(o.get('freelancerId'), str)]

    offer_exists = len(offers_list) > 0
    offer_message_exists = has_offer_message(data)

    if offer_exists and offer_message_exists:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == '__main__':
    main()
