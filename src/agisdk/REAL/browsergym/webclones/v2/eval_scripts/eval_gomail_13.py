import json, sys

# Verification script for task: "Write an email to alexa richardson and ask to let me know when the files come in."
# Strategy:
# - Identify any newly added, sent email addressed to Alexa Richardson (recipient contains "alexa.richardson").
# - Validate subject is present and not "No Subject".
# - Validate body requests notification about files: must contain both "let me know" and the word "file" (case-insensitive).
# - Aggregate added emails from both differences.emails.added and initialfinaldiff.added.email.emails, handling None safely.

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def safe_get_map(obj, key):
    if isinstance(obj, dict):
        val = obj.get(key)
        return val if isinstance(val, dict) else ({} if val is None else {})
    return {}

def gather_added_emails(data):
    added = []
    # From differences
    diff = data.get('differences') or {}
    emails_section = (diff.get('emails') or {}) if isinstance(diff, dict) else {}
    diff_added = emails_section.get('added') or []
    if isinstance(diff_added, list):
        added.extend(diff_added)

    # From initialfinaldiff added structure (dict of emails)
    if isinstance(data.get('initialfinaldiff'), dict):
        init_add = data['initialfinaldiff'].get('added') or {}
        email_block = init_add.get('email') or {}
        emails_dict = email_block.get('emails') or {}
        if isinstance(emails_dict, dict):
            added.extend(list(emails_dict.values()))

    # Deduplicate by id if present
    seen = set()
    deduped = []
    for e in added:
        if not isinstance(e, dict):
            continue
        eid = e.get('id')
        key = ('id', eid) if eid is not None else ('obj', json.dumps(e, sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(e)
    return deduped

def is_email_to_alexa(to_list):
    if not isinstance(to_list, list):
        return False
    for addr in to_list:
        if not isinstance(addr, str):
            continue
        a = addr.strip().lower()
        if 'alexa.richardson' in a:
            return True
    return False

def content_mentions_files_and_notify(content):
    if not isinstance(content, str):
        return False
    text = content.strip().lower()
    if not text:
        return False
    return ('let me know' in text) and ('file' in text)


def subject_is_valid(subj):
    if not isinstance(subj, str):
        return False
    s = subj.strip()
    if not s:
        return False
    if s.lower() == 'no subject':
        return False
    return True


def main():
    path = sys.argv[1]
    data = load_json(path)

    added_emails = gather_added_emails(data)
    success = False

    for em in added_emails:
        if not isinstance(em, dict):
            continue
        if not em.get('sent', False):
            continue
        if not is_email_to_alexa(em.get('to')):
            continue
        if not subject_is_valid(em.get('subject')):
            continue
        if not content_mentions_files_and_notify(em.get('content', '')):
            continue
        success = True
        break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
