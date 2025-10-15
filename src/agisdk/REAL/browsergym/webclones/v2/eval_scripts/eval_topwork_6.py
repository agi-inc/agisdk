import json, sys

def safe_get(d, *keys):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur

# Analyze a single contact for presence of exactly one invite indicator (boolean) and full-stack role

def analyze_contact_for_invite_flag(contact):
    found_invite = False
    is_fullstack = False

    # Determine if contact role/job matches full-stack developer (case-insensitive, robust to hyphen)
    job = contact.get('job') if isinstance(contact, dict) else None
    if isinstance(job, str):
        jl = job.strip().lower()
        if ('full' in jl and 'stack' in jl):
            is_fullstack = True

    # Helper to check if a text looks like an invite
    def is_invite_text(txt):
        if not isinstance(txt, str):
            return False
        t = txt.lower()
        return ('invite' in t and 'job' in t)

    # Check lastMessage
    last_author = contact.get('lastMessageAuthor') if isinstance(contact, dict) else None
    last_msg = contact.get('lastMessage') if isinstance(contact, dict) else None
    if isinstance(last_author, str) and last_author == 'Client' and is_invite_text(last_msg):
        found_invite = True

    # Check detailed messages list/dict for client invite text and ensure not an offer type
    msgs = contact.get('messages') if isinstance(contact, dict) else None
    if not found_invite:
        if isinstance(msgs, dict):
            for mv in msgs.values():
                if not isinstance(mv, dict):
                    continue
                # If it's an offer type, skip counting as invite (and will be flagged elsewhere)
                if mv.get('type') == 'offer' or 'offer' in mv:
                    continue
                author = mv.get('author')
                message = mv.get('message')
                if isinstance(author, str) and author == 'Client' and is_invite_text(message):
                    found_invite = True
                    break
        elif isinstance(msgs, list):
            for mv in msgs:
                if not isinstance(mv, dict):
                    continue
                if mv.get('type') == 'offer' or 'offer' in mv:
                    continue
                author = mv.get('author')
                message = mv.get('message')
                if isinstance(author, str) and author == 'Client' and is_invite_text(message):
                    found_invite = True
                    break

    return found_invite, is_fullstack

# Detect if any offers were sent (rehire), by scanning both offers buckets and message entries with type offer or offer object.

def detect_offers(patch):
    # Check top-level offers collections in both added and updated
    for section in ('added', 'updated'):
        offers = safe_get(patch, section, 'offers', 'offers')
        if isinstance(offers, dict) and len(offers) > 0:
            return True

    # Scan messages for any offer-type entries
    for section in ('added', 'updated'):
        cl = safe_get(patch, section, 'messages', 'contactList')
        if isinstance(cl, dict):
            for c in cl.values():
                if not isinstance(c, dict):
                    continue
                msgs = c.get('messages')
                if isinstance(msgs, dict):
                    for mv in msgs.values():
                        if isinstance(mv, dict) and (mv.get('type') == 'offer' or 'offer' in mv):
                            return True
                elif isinstance(msgs, list):
                    for mv in msgs:
                        if isinstance(mv, dict) and (mv.get('type') == 'offer' or 'offer' in mv):
                            return True
    return False


def main():
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    patch = data.get('initialfinaldiff') or {}

    # First, detect any offers (should be failure for this task)
    if detect_offers(patch):
        print('FAILURE')
        return

    total_invites_contacts = 0
    fullstack_invites_contacts = 0

    # Track contacts we've already evaluated to avoid double counting across sections
    seen_contact_ids = set()

    # Scan both updated and added sections for invites
    for section in ('updated', 'added'):
        cl = safe_get(patch, section, 'messages', 'contactList')
        if not isinstance(cl, dict):
            continue
        for contact in cl.values():
            if not isinstance(contact, dict):
                continue
            cid = contact.get('id')
            # Only consider identifiable contacts once
            if cid and cid in seen_contact_ids:
                continue
            found_invite, is_fullstack = analyze_contact_for_invite_flag(contact)
            if found_invite:
                total_invites_contacts += 1
                if is_fullstack:
                    fullstack_invites_contacts += 1
            if cid:
                seen_contact_ids.add(cid)

    # Success criteria:
    # - Exactly one invite sent in total (to exactly one contact)
    # - That single invite must be to a full-stack developer
    if total_invites_contacts == 1 and fullstack_invites_contacts == 1:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
