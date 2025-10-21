import json, sys

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

# Task: GoMail: Inform Danielle that the new system update has been launched
# Verification strategy:
# - Find any newly added email (differences.emails.added) that was sent to Danielle (any recipient containing 'danielle')
# - Ensure the email communicates a new update by checking that the combined subject+content includes both 'new' and 'update' (case-insensitive)
# - Prefer emails with sent == True; if 'sent' field exists and is False, do not count it
# - If such an email exists, print SUCCESS, else FAILURE

def normalize_text(s):
    if not isinstance(s, str):
        return ""
    return s.lower()

def recipient_includes_danielle(recipients):
    if not isinstance(recipients, list):
        return False
    for r in recipients:
        if isinstance(r, str) and 'danielle' in r.lower():
            return True
    return False


def main():
    path = sys.argv[1]
    data = load_json(path)
    diffs = data.get('differences', {})
    emails = diffs.get('emails', {})
    added = emails.get('added', [])

    success = False
    for e in added:
        # Validate recipient Danielle
        if not recipient_includes_danielle(e.get('to', [])):
            continue
        # Must be sent if field present
        if 'sent' in e and not e.get('sent', False):
            continue
        # Combine subject and content for message intent
        subj = normalize_text(e.get('subject', ''))
        content = normalize_text(e.get('content', ''))
        combined = subj + ' ' + content
        # Require that both 'new' and 'update' appear somewhere
        if ('new' in combined) and ('update' in combined):
            success = True
            break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()