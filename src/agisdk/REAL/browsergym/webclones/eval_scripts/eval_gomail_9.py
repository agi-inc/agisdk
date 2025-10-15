import json, sys

# Verification script for GoMail task:
# Goal: Ensure an email was sent to Carol notifying a meeting time change to 8:30 AM.
# Strategy:
# 1) Find added emails (from differences and initialfinaldiff) that have sent == True and include Carol's email in the recipients.
# 2) In subject+content (HTML stripped), confirm mention of a meeting and the new time as 8:30 AM, plus an indicator of change (e.g., now/moved/changed/rescheduled).

TARGET_EMAIL = "carol.adams@example.com"

def strip_html(s):
    if not isinstance(s, str):
        s = str(s) if s is not None else ""
    out = []
    in_tag = False
    for ch in s:
        if ch == '<':
            in_tag = True
            continue
        if ch == '>':
            in_tag = False
            out.append(' ')
            continue
        if not in_tag:
            out.append(ch)
    # collapse spaces and lowercase
    text = ''.join(out).replace('\n', ' ').replace('\r', ' ')
    # normalize multiple spaces
    parts = [p for p in text.split(' ') if p != '']
    return (' '.join(parts)).lower()

def gather_added_emails(state):
    emails = []
    dif = state.get('differences', {}).get('emails', {})
    added = dif.get('added', [])
    if isinstance(added, list):
        emails.extend(added)
    # Also check initialfinaldiff added path if present
    if state.get('initialfinaldiff'):
        try:
            email_section = state['initialfinaldiff'].get('added', {})\
                                             .get('email', {})\
                                             .get('emails', {})
            if isinstance(email_section, dict):
                for v in email_section.values():
                    emails.append(v)
        except Exception:
            pass
    return emails

def contains_830_am(text):
    # Check for explicit 8:30 AM mention allowing optional space
    t = text
    if '8:30am' in t:
        return True
    if '8:30 am' in t:
        return True
    # Also accept variants with non-breaking space or multiple spaces collapsed by normalization above
    return False

def indicates_change(text):
    # Words indicating change or announcement
    keywords = [
        'change', 'changed', 'move', 'moved', 'reschedule', 'rescheduled', 'now', 'update', 'updated'
    ]
    return any(k in text for k in keywords)

def mentions_meeting(text):
    return 'meeting' in text

def email_to_includes_carol(to_list):
    if not isinstance(to_list, list):
        return False
    for addr in to_list:
        if isinstance(addr, str) and addr.strip().lower() == TARGET_EMAIL:
            return True
    return False

def verify(state):
    emails = gather_added_emails(state)
    for em in emails:
        # Must be sent
        if not em or not isinstance(em, dict):
            continue
        if not em.get('sent', False):
            continue
        if not email_to_includes_carol(em.get('to')):
            continue
        subj = strip_html(em.get('subject', ''))
        body = strip_html(em.get('content', ''))
        combined = (subj + ' ' + body).strip()
        if not mentions_meeting(combined):
            continue
        if not contains_830_am(combined):
            continue
        if not indicates_change(combined):
            continue
        return True
    return False

def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            state = json.load(f)
        result = verify(state)
        print('SUCCESS' if result else 'FAILURE')
    except Exception:
        # On any unexpected error, signal failure
        print('FAILURE')

if __name__ == '__main__':
    main()