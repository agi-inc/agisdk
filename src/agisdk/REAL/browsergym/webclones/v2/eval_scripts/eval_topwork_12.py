import json, sys

# Strategy:
# - Task is successful if a proper offer was sent AND a message containing the offer exists.
# - Verify by:
#   1) Finding any message with type == 'offer' OR containing an 'offer' object with key fields.
#   2) Confirming there is at least one offer record under offers.offers with id and valid status.
# - Search both 'added' and 'updated' sections and handle dict/list variations gracefully.


def iter_messages(container):
    """Yield individual message dicts from a messages container which could be a list or dict."""
    if container is None:
        return
    # messages can be a list or dict with numeric keys
    if isinstance(container, list):
        for m in container:
            if isinstance(m, dict):
                yield m
    elif isinstance(container, dict):
        for m in container.values():
            if isinstance(m, dict):
                yield m


def find_offer_message(sections):
    """Return True if any message indicates an offer was sent (type=='offer' or embedded 'offer' object with basic fields)."""
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        messages_root = sec.get('messages') or {}
        contact_list = messages_root.get('contactList')
        if not isinstance(contact_list, dict):
            continue
        for contact in contact_list.values():
            if not isinstance(contact, dict):
                continue
            msgs = contact.get('messages')
            for msg in iter_messages(msgs):
                # Case A: explicit type marking
                if isinstance(msg.get('type'), str) and msg.get('type').lower() == 'offer':
                    return True
                # Case B: embedded offer object
                off = msg.get('offer')
                if isinstance(off, dict):
                    # minimal validity: has id and contractTitle and status
                    oid = off.get('id')
                    title = off.get('contractTitle')
                    status = off.get('status')
                    if isinstance(oid, str) and oid.strip() and isinstance(title, str) and title.strip() and isinstance(status, str) and status.strip():
                        return True
    return False


def collect_offers(sections):
    """Collect offer records from offers.offers in given sections. Returns list of offer dicts."""
    offers = []
    for sec in sections:
        if not isinstance(sec, dict):
            continue
        offers_root = sec.get('offers') or {}
        offers_map = offers_root.get('offers')
        if isinstance(offers_map, dict):
            for off in offers_map.values():
                if isinstance(off, dict):
                    offers.append(off)
    return offers


def has_valid_offer_record(offers_list):
    valid_statuses = {"pending", "accepted"}  # treat pending/accepted as valid sent offers
    for off in offers_list:
        oid = off.get('id')
        title = off.get('contractTitle')
        status = off.get('status')
        if isinstance(oid, str) and oid.strip() and isinstance(title, str) and title.strip() and isinstance(status, str) and status.lower() in valid_statuses:
            return True
    return False


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    root = data.get('initialfinaldiff', data)
    if not isinstance(root, dict):
        print("FAILURE")
        return

    added = root.get('added') or {}
    updated = root.get('updated') or {}

    sections = [added, updated]

    # Check for offer message existence
    offer_msg = find_offer_message(sections)

    # Check for at least one valid offer record
    offer_records = collect_offers(sections)
    has_offer = has_valid_offer_record(offer_records)

    if offer_msg and has_offer:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    main()
