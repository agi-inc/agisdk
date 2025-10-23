import json
import sys

# Verification script for: Go Mail: Write an email to Barbara Thomas regarding the project plan
# Strategy:
# 1) Extract all newly added emails from both `differences.emails.added` and `initialfinaldiff.added.email.emails`.
# 2) Declare SUCCESS if there exists a sent email to barbara.thomas@example.com whose subject or content mentions "project plan" (case-insensitive). Otherwise, FAILURE.

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_added_emails(data):
    emails_by_id = {}

    # From differences.emails.added (preferred aggregated diff)
    diffs = data.get('differences', {})
    emails_diff = diffs.get('emails', {}) if isinstance(diffs, dict) else {}
    added_list = emails_diff.get('added', []) if isinstance(emails_diff, dict) else []
    if isinstance(added_list, list):
        for e in added_list:
            if isinstance(e, dict):
                eid = str(e.get('id', ''))
                emails_by_id[eid] = e

    # From initialfinaldiff.added.email.emails (raw additions map)
    ifd = data.get('initialfinaldiff', {})
    added_ifd = ifd.get('added', {}) if isinstance(ifd, dict) else {}
    email_section = added_ifd.get('email', {}) if isinstance(added_ifd, dict) else {}
    emails_map = email_section.get('emails', {}) if isinstance(email_section, dict) else {}
    if isinstance(emails_map, dict):
        for k, e in emails_map.items():
            if isinstance(e, dict):
                eid = str(e.get('id', ''))
                emails_by_id[eid] = e

    return list(emails_by_id.values())


def contains_project_plan(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return "project plan" in t


def to_contains_barbara(to_field) -> bool:
    target = "barbara.thomas@example.com"
    # to_field expected to be a list; handle strings defensively
    if isinstance(to_field, list):
        for item in to_field:
            if isinstance(item, str) and target in item.lower():
                return True
    elif isinstance(to_field, str):
        return target in to_field.lower()
    return False


def main():
    path = sys.argv[1]
    data = load_json(path)

    added_emails = extract_added_emails(data)

    success = False
    for e in added_emails:
        sent = bool(e.get('sent'))
        if not sent:
            continue
        if not to_contains_barbara(e.get('to')):
            continue
        subject = e.get('subject') or ''
        content = e.get('content') or ''
        combined = f"{subject}\n{content}"
        if contains_project_plan(combined):
            success = True
            break

    print("SUCCESS" if success else "FAILURE")

if __name__ == "__main__":
    main()
