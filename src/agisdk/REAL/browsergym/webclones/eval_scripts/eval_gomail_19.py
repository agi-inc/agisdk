import json, sys, re

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Simple HTML tag stripper to analyze textual content
TAG_RE = re.compile(r'<[^>]+>')

def strip_tags(text):
    if not isinstance(text, str):
        return ''
    return TAG_RE.sub(' ', text).lower()

def get_added_emails(data):
    emails = []
    # From differences.emails.added (common path)
    try:
        added = data.get('differences', {}).get('emails', {}).get('added', [])
        if isinstance(added, list):
            emails.extend([e for e in added if isinstance(e, dict)])
    except Exception:
        pass
    # Also handle initialfinaldiff.added.email.emails which may be a dict of emails
    try:
        init_added_emails = data.get('initialfinaldiff', {}).get('added', {}).get('email', {}).get('emails', {})
        if isinstance(init_added_emails, dict):
            for _, v in init_added_emails.items():
                if isinstance(v, dict):
                    emails.append(v)
    except Exception:
        pass
    return emails

# Determine if the email talks about meeting date/time
TIME_WORDS = [
    'date', 'when', 'schedule', 'scheduled', 'time', 'day'
]

def mentions_meeting_date(subject, content):
    subj = strip_tags(subject)
    body = strip_tags(content)
    combined = subj + ' ' + body
    has_meeting = 'meeting' in combined
    has_time_intent = any(w in combined for w in TIME_WORDS)
    return has_meeting and has_time_intent


def to_includes_thompson(to_list):
    if not isinstance(to_list, list):
        return False
    for addr in to_list:
        if not isinstance(addr, str):
            continue
        addr_l = addr.lower()
        if 'thompson' in addr_l:
            return True
    return False


def is_sent_email(email):
    # Must be marked sent and not a draft/spam/trash
    if not isinstance(email, dict):
        return False
    if email.get('sent') is not True:
        return False
    if email.get('draft') is True:
        return False
    if email.get('spam') is True:
        return False
    if email.get('trash') is True:
        return False
    return True


def main():
    # Strategy in code comments:
    # 1) Gather all added emails from differences and initialfinaldiff.
    # 2) For each, ensure it's sent and addressed to Thompson (recipient contains 'thompson').
    # 3) Verify subject or content mentions 'meeting' and includes a time/date intent word (e.g., 'when', 'date', 'schedule', 'time', 'day').
    # 4) If any email satisfies all conditions, print SUCCESS; else FAILURE.
    path = sys.argv[1]
    data = load_json(path)
    added_emails = get_added_emails(data)

    for e in added_emails:
        if not is_sent_email(e):
            continue
        if not to_includes_thompson(e.get('to')):
            continue
        if mentions_meeting_date(e.get('subject', ''), e.get('content', '')):
            print('SUCCESS')
            return

    print('FAILURE')

if __name__ == '__main__':
    main()