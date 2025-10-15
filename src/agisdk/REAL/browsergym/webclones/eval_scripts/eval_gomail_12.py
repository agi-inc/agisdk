import sys, json

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Simple HTML tag stripper without regex (only stdlib json/sys allowed)
# Removes everything between '<' and '>'
def strip_html(text):
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

# Normalize text: strip HTML, collapse whitespace, lowercase
def normalize_text(text):
    cleaned = strip_html(text or '')
    # collapse whitespace
    cleaned = ' '.join(cleaned.split())
    return cleaned.lower()

# Extract newly added emails from various possible locations in the diff
def extract_added_emails(data):
    emails = []
    try:
        diff_added = data.get('differences', {}).get('emails', {}).get('added', [])
        if isinstance(diff_added, list):
            emails.extend(diff_added)
    except Exception:
        pass
    # Fallback: sometimes present under initialfinaldiff.added.email.emails as a dict
    try:
        init_added_emails = (
            data.get('initialfinaldiff', {})
                .get('added', {})
                .get('email', {})
                .get('emails', {})
        )
        if isinstance(init_added_emails, dict):
            for _, v in init_added_emails.items():
                emails.append(v)
        elif isinstance(init_added_emails, list):
            emails.extend(init_added_emails)
    except Exception:
        pass
    return emails

# Verification logic for the task:
# Task: Write an email to Kevin Moore to ask for the project details
# We confirm SUCCESS if there exists at least one newly added email that:
# - was sent (sent == True)
# - has exactly one recipient in the 'to' field, and it is kevin.moore@example.com (case-insensitive)
# - has a non-empty content/body after stripping tags and whitespace, and mentions project details
# - has a subject indicating project details (contains both 'project' and 'detail') and is not 'no subject'
# Additionally, we consider adding extra recipients in cc/bcc as failure for that email

def email_matches(e):
    # Must be sent
    if not e or not isinstance(e, dict):
        return False
    if not e.get('sent', False):
        return False
    # Validate recipients in 'to'
    to_list = e.get('to')
    if not isinstance(to_list, list) or len(to_list) != 1:
        return False
    to_addr = (to_list[0] or '').strip().lower()
    if to_addr != 'kevin.moore@example.com':
        return False
    # Ensure no extra recipients via cc/bcc if present
    cc = e.get('cc', [])
    bcc = e.get('bcc', [])
    if cc and isinstance(cc, list) and len(cc) > 0:
        return False
    if bcc and isinstance(bcc, list) and len(bcc) > 0:
        return False
    # Subject check
    subject = (e.get('subject') or '').strip()
    subject_norm = subject.lower()
    if subject_norm in ('', 'no subject'):
        return False
    if ('project' not in subject_norm) or ('detail' not in subject_norm):
        return False
    # Content/body check
    content_norm = normalize_text(e.get('content', ''))
    if not content_norm:
        return False
    # Must mention project details in body
    if ('project' not in content_norm) or ('detail' not in content_norm):
        return False
    # Should not be marked as draft/spam/trash
    if e.get('draft') is True:
        return False
    if e.get('spam') is True or e.get('trash') is True:
        return False
    return True


def main():
    path = sys.argv[1]
    data = load_json(path)
    added_emails = extract_added_emails(data)
    # Evaluate all added emails; success if any matches
    for e in added_emails:
        if email_matches(e):
            print('SUCCESS')
            return
    print('FAILURE')

if __name__ == '__main__':
    main()
