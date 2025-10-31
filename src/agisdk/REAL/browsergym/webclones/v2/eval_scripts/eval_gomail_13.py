import json, sys

# Verification script for GoMail task: Send email to Carol about meeting time change to 8:30 AM
# Strategy:
# 1) Gather all newly added emails from differences.emails.added and initialfinaldiff.added.email.emails
# 2) For each, verify: sent==True, recipient includes 'carol' (case-insensitive), and text mentions 'meeting' and a time '8:30' variant
# 3) If any email passes these checks, print SUCCESS; otherwise, FAILURE

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_added_emails(data):
    emails = []
    # From differences.emails.added
    try:
        added_list = data.get('differences', {}).get('emails', {}).get('added', [])
        if isinstance(added_list, list):
            for e in added_list:
                if isinstance(e, dict):
                    emails.append(e)
    except Exception:
        pass
    # From initialfinaldiff.added.email.emails (values of dict)
    try:
        emails_dict = data.get('initialfinaldiff', {}).get('added', {}).get('email', {}).get('emails', {})
        if isinstance(emails_dict, dict):
            for k, v in emails_dict.items():
                if isinstance(v, dict):
                    emails.append(v)
    except Exception:
        pass
    return emails

def strip_html(text):
    # Simple removal of tags without regex: iterate and drop content between '<' and '>'
    if not isinstance(text, str):
        return ''
    out = []
    inside = False
    for ch in text:
        if ch == '<':
            inside = True
            continue
        if ch == '>':
            inside = False
            continue
        if not inside:
            out.append(ch)
    return ''.join(out)

def contains_meeting_and_time(text):
    # Normalize and check for 'meeting' and an '8:30' variant
    if not text:
        return False
    norm = strip_html(text).lower()
    # Normalize separators to ':' to catch '8.30'
    norm = norm.replace('8.30', '8:30').replace('08.30', '08:30')
    # Collapse whitespace (basic)
    norm = ' '.join(norm.split())
    has_meeting = 'meeting' in norm
    # Check for 8:30 variants
    has_time = ('8:30' in norm) or ('08:30' in norm)
    return has_meeting and has_time

def is_to_carol(to_list):
    if not isinstance(to_list, list):
        return False
    for addr in to_list:
        if not isinstance(addr, str):
            continue
        low = addr.strip().lower()
        if 'carol' in low:
            return True
        # explicit known address
        if low == 'carol.adams@example.com':
            return True
    return False


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print('FAILURE')
        return
    try:
        data = load_json(path)
    except Exception:
        print('FAILURE')
        return

    emails = get_added_emails(data)
    success = False
    for e in emails:
        try:
            sent = e.get('sent', False)
            to_list = e.get('to', [])
            subject = e.get('subject', '') or ''
            content = e.get('content', '') or ''
            if not sent:
                continue
            if not is_to_carol(to_list):
                continue
            # Check content or subject for meeting + time
            if contains_meeting_and_time(content) or contains_meeting_and_time(subject):
                success = True
                break
        except Exception:
            continue

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()