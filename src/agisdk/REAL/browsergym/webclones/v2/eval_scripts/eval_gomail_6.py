import json, sys

# Verification script for task:
# "Go Mail: Write an email to Barbara Thomas regarding the project plan"
#
# Strategy:
# - Look for at least one newly added email (differences.emails.added) sent to barbara.thomas@example.com
# - Ensure the email is actually sent (sent==True if present, and not a draft)
# - Confirm the topic by checking the phrase "project plan" (case-insensitive) in subject or content
# - If such an email exists, print SUCCESS; otherwise, print FAILURE

def safe_lower(s):
    try:
        return str(s).lower()
    except Exception:
        return ""

def is_sent_email(email_obj):
    # If 'sent' is present, require it to be True.
    sent = email_obj.get('sent')
    if sent is not None and sent is not True:
        return False
    # If 'draft' is present and True, it's not sent.
    if email_obj.get('draft') is True:
        return False
    # Otherwise consider it sent
    return True

def recipient_includes_barbara(email_obj):
    to_field = email_obj.get('to', [])
    recipients = []
    if isinstance(to_field, list):
        recipients = to_field
    elif to_field is None:
        recipients = []
    else:
        recipients = [to_field]
    recipients_lower = [safe_lower(r).strip() for r in recipients]
    return 'barbara.thomas@example.com' in recipients_lower

def about_project_plan(email_obj):
    subject = safe_lower(email_obj.get('subject', ''))
    content = safe_lower(email_obj.get('content', ''))
    # Check contiguous phrase in either subject or content
    return ('project plan' in subject) or ('project plan' in content)


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    emails_added = (
        data.get('differences', {})
            .get('emails', {})
            .get('added', [])
    )

    success = False
    if isinstance(emails_added, list):
        for email in emails_added:
            if not isinstance(email, dict):
                continue
            if not is_sent_email(email):
                continue
            if not recipient_includes_barbara(email):
                continue
            if not about_project_plan(email):
                continue
            success = True
            break

    print("SUCCESS" if success else "FAILURE")

if __name__ == '__main__':
    main()
