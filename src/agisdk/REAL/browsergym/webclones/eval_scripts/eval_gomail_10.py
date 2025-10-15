import json, sys

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Extract all emails that appear as newly added (i.e., sent by the agent during this task)

def get_added_emails(data):
    added = []
    # From differences.emails.added (list)
    try:
        diff_added = data.get('differences', {}).get('emails', {}).get('added', [])
        if isinstance(diff_added, list):
            added.extend(diff_added)
    except Exception:
        pass

    # From initialfinaldiff.added.email.emails (dict of emails)
    try:
        if isinstance(data.get('initialfinaldiff'), dict):
            emails_dict = (
                data['initialfinaldiff']
                .get('added', {})
                .get('email', {})
                .get('emails', {})
            )
            if isinstance(emails_dict, dict):
                for v in emails_dict.values():
                    # Some states may include the same items also in differences; duplication is fine
                    added.append(v)
    except Exception:
        pass

    return added


def str_or_empty(x):
    return x if isinstance(x, str) else ''


def normalize_addr(addr):
    return addr.strip().lower()


def is_sent_email(email_obj):
    # Determine if this object represents an outgoing sent email
    # Prefer explicit sent flag when present
    if isinstance(email_obj, dict):
        sent = email_obj.get('sent')
        if sent is not None:
            return bool(sent)
        # If no sent flag, infer from typical fields: from our account and not draft/spam/trash
        from_addr = str_or_empty(email_obj.get('from')).lower()
        # Common sender in these tasks
        likely_sender = 'fede.lopez@gmail.com'
        not_draft = email_obj.get('draft') is False or email_obj.get('draft') is None
        not_spam = email_obj.get('spam') is False or email_obj.get('spam') is None
        not_trash = email_obj.get('trash') is False or email_obj.get('trash') is None
        to_list = email_obj.get('to') or []
        return (from_addr == likely_sender and not_draft and not_spam and not_trash and isinstance(to_list, list) and len(to_list) > 0)
    return False


def content_text(email_obj):
    # Return combined textual content for simple substring checks
    subject = str_or_empty(email_obj.get('subject'))
    content = str_or_empty(email_obj.get('content'))
    # Keep HTML; we will do substring checks in lowercase which still works
    return subject, content


def mentions_team_dinner(subject_l, content_l):
    # Consider it a mention if either subject or content conveys "team dinner"
    # Accept either exact phrase or both words present
    def has_team_dinner(txt):
        return ('team dinner' in txt) or ('team' in txt and 'dinner' in txt)
    return has_team_dinner(subject_l) or has_team_dinner(content_l)


def asks_about_attendance(content_l):
    # Look for common attendance inquiry patterns
    keywords = [
        'coming', 'attending', 'join', 'rsvp', 'confirm', 'able to make', 'make it', 'be there', "are you in"
    ]
    if any(k in content_l for k in keywords):
        return True
    # Fallback: if content includes a question mark and references dinner/team context
    if '?' in content_l and ('dinner' in content_l or 'team' in content_l):
        return True
    return False


def verify(data):
    # Strategy:
    # 1) Find at least one newly added, sent email whose sole recipient is Ashley Campbell
    # 2) Ensure the message asks about attendance and references the team dinner (in subject or body)
    target_email = 'ashley.campbell@example.com'
    added_emails = get_added_emails(data)

    for em in added_emails:
        if not isinstance(em, dict):
            continue
        if not is_sent_email(em):
            continue
        to_list = em.get('to') or []
        if not isinstance(to_list, list) or len(to_list) == 0:
            continue
        # Ensure exactly and only Ashley is the recipient (avoid multiple recipients per task requirements)
        normalized_to = [normalize_addr(t) for t in to_list if isinstance(t, str)]
        if len(normalized_to) != 1:
            continue
        if normalized_to[0] != normalize_addr(target_email):
            continue

        subject, content = content_text(em)
        subject_l = subject.lower()
        content_l = content.lower()

        # Must reference the team dinner (subject or body)
        if not mentions_team_dinner(subject_l, content_l):
            continue
        # Must ask about attendance
        if not asks_about_attendance(content_l):
            continue

        # If all checks pass for any one email, declare success
        return True

    return False


def main():
    try:
        path = sys.argv[1]
        data = load_json(path)
        if verify(data):
            print("SUCCESS")
        else:
            print("FAILURE")
    except Exception:
        # Any parsing/runtime error should be treated as failure per verification requirement
        print("FAILURE")

if __name__ == '__main__':
    main()
