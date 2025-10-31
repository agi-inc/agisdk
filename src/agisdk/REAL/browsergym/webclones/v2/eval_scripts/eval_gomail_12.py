import json, sys

def strip_tags(s: str) -> str:
    # Simple HTML tag stripper without regex
    res = []
    in_tag = False
    for ch in s:
        if ch == '<':
            in_tag = True
        elif ch == '>':
            in_tag = False
        else:
            if not in_tag:
                res.append(ch)
    return ''.join(res)


def get_added_emails(state: dict):
    emails = []
    # Path 1: differences.emails.added (list)
    try:
        added_list = state.get('differences', {}).get('emails', {}).get('added', [])
        if isinstance(added_list, list):
            emails.extend([e for e in added_list if isinstance(e, dict)])
    except Exception:
        pass
    # Path 2: initialfinaldiff.added.email.emails (dict of emails)
    try:
        added_block = state.get('initialfinaldiff', {}).get('added', {}).get('email', {}).get('emails', {})
        if isinstance(added_block, dict):
            for v in added_block.values():
                if isinstance(v, dict):
                    emails.append(v)
    except Exception:
        pass
    return emails


def has_keywords(subject: str, content: str) -> bool:
    subj = (subject or '').strip().lower()
    body = strip_tags(content or '').strip().lower()
    # Require both 'new' and 'client' to appear in either subject or body
    def contains_both(txt: str) -> bool:
        return ('new' in txt) and ('client' in txt)
    return contains_both(subj) or contains_both(body)


def main():
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        state = json.load(f)

    added_emails = get_added_emails(state)
    target_email = 'charles.davis@example.com'
    success = False

    for e in added_emails:
        to_list = e.get('to') or []
        if not isinstance(to_list, list):
            continue
        to_lower = [str(x).strip().lower() for x in to_list]
        if target_email not in to_lower:
            continue
        # Ensure email was sent (if field exists, it must be True)
        if 'sent' in e and not e.get('sent', False):
            continue
        subject = e.get('subject') or ''
        # Subject must be present and not a default placeholder like 'No Subject'
        if subject.strip() == '' or subject.strip().lower() == 'no subject':
            continue
        content = e.get('content') or ''
        # Ensure the message discusses new clients in subject or body
        if not has_keywords(subject, content):
            continue
        # All conditions satisfied
        success = True
        break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
