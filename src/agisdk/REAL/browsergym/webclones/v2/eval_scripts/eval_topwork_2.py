import json
import sys


def is_backend_or_fullstack(job):
    if not job or not isinstance(job, str):
        return False
    s = job.strip().lower()
    # Match variations: Full-Stack, Full Stack, Backend, Back-End, Back end
    return (("full" in s and "stack" in s) or ("back" in s and "end" in s)) and (
        "developer" in s or "engineer" in s or True
    )


def collect_contacts(initialfinaldiff):
    contacts_by_id = {}

    # Helper to merge contacts from a container
    def add_from(container):
        messages = ((container or {}).get("messages") or {}).get("contactList")
        if not isinstance(messages, dict):
            return
        for _k, contact in messages.items():
            if not isinstance(contact, dict):
                continue
            cid = contact.get("id")
            if not cid:
                # skip contacts without explicit id (aggregate rows)
                continue
            # If already existing, prefer fields from the newer one (later call overwrites)
            prev = contacts_by_id.get(cid, {})
            merged = {}
            merged.update(prev)
            merged.update(contact)
            contacts_by_id[cid] = merged

    add_from((initialfinaldiff or {}).get("added"))
    add_from((initialfinaldiff or {}).get("updated"))
    return contacts_by_id


def iter_contact_messages(contact):
    # Yield all textual messages and offer descriptions inside a contact
    # messages can be dict of indices or a list
    msgs_container = contact.get("messages")
    if isinstance(msgs_container, list):
        items = msgs_container
    elif isinstance(msgs_container, dict):
        # convert to list of dicts
        items = [v for v in msgs_container.values() if isinstance(v, dict)]
    else:
        items = []
    for item in items:
        # normal text message
        msg = item.get("message")
        if isinstance(msg, str) and msg.strip():
            yield msg
        # offer nested object
        off = item.get("offer")
        if isinstance(off, dict):
            desc = off.get("description")
            if isinstance(desc, str) and desc.strip():
                yield desc
    # Also consider lastMessage as textual evidence
    last_msg = contact.get("lastMessage")
    if isinstance(last_msg, str) and last_msg.strip():
        yield last_msg


def collect_offers(initialfinaldiff):
    offers_list = []

    def add_offers(container):
        offers = ((container or {}).get("offers") or {}).get("offers")
        if isinstance(offers, dict):
            for _k, off in offers.items():
                if isinstance(off, dict):
                    offers_list.append(off)

    add_offers((initialfinaldiff or {}).get("added"))
    add_offers((initialfinaldiff or {}).get("updated"))
    return offers_list


def text_invites_fitness_app(text):
    if not text or not isinstance(text, str):
        return False
    s = text.lower()
    # Must clearly ask about a fitness app and interest
    # Require both keywords to avoid false positives
    has_fitness_app = ("fitness app" in s) or ("fitness" in s and "app" in s)
    asks_interest = "interested" in s
    return has_fitness_app and asks_interest


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    initialfinaldiff = (data or {}).get("initialfinaldiff") or {}

    # Strategy:
    # 1) Find contacts whose job indicates backend/full-stack developer.
    # 2) Check if any message/lastMessage to those contacts contains an invite mentioning a fitness app and interest.
    # 3) Also check any offers sent to such contacts with a description matching the invite criteria.

    contacts = collect_contacts(initialfinaldiff)

    # Fast path: scan messages for qualified contacts
    for _cid, contact in contacts.items():
        job = contact.get("job")
        if not is_backend_or_fullstack(job):
            continue
        for text in iter_contact_messages(contact):
            if text_invites_fitness_app(text):
                print("SUCCESS")
                return

    # Also check offers and map to contact job
    offers = collect_offers(initialfinaldiff)
    for off in offers:
        desc = off.get("description")
        if not text_invites_fitness_app(desc):
            continue
        fid = off.get("freelancerId")
        # map to contact job if available
        if fid and fid in contacts and is_backend_or_fullstack(contacts[fid].get("job")):
            print("SUCCESS")
            return

    # If nothing matched, it's a failure
    print("FAILURE")


if __name__ == "__main__":
    main()
