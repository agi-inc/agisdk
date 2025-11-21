import json
import re
import sys


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Strategy in code:
# - Collect newly added sent emails from both differences.emails.added and initialfinaldiff.added.email.emails
# - Validate: recipient is a proper email containing both 'alexa' and 'richardson'; subject is non-empty and not 'No Subject';
#             body text (HTML stripped) contains 'let me know' and mentions 'file'. If any email matches, print SUCCESS else FAILURE.


def strip_html(text):
    if not isinstance(text, str):
        return ""
    # remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_added_emails(data):
    emails = []
    # From differences.emails.added
    diffs = data.get("differences", {})
    emails_added = diffs.get("emails", {}).get("added", [])
    if isinstance(emails_added, list):
        for e in emails_added:
            if isinstance(e, dict):
                emails.append(e)
    # From initialfinaldiff.added.email.emails (object of id->email)
    if isinstance(data.get("initialfinaldiff"), dict):
        added = data["initialfinaldiff"].get("added", {})
        email_obj = added.get("email", {}).get("emails")
        if isinstance(email_obj, dict):
            for _, e in email_obj.items():
                if isinstance(e, dict):
                    emails.append(e)
    return emails


def is_valid_recipient(rec):
    # Must be a plausible email and contain both 'alexa' and 'richardson'
    if not isinstance(rec, str):
        return False
    r = rec.strip().lower()
    if "@" not in r or "." not in r:
        return False
    return "alexa" in r and "richardson" in r


def subject_ok(subj):
    if not isinstance(subj, str):
        return False
    s = subj.strip()
    if not s:
        return False
    return s.lower() != "no subject"


def content_ok(content):
    txt = strip_html(content).lower()
    if not txt:
        return False
    # Must contain the instruction to let me know and reference to files
    if "let me know" not in txt:
        return False
    if "file" not in txt:  # matches 'file' or 'files'
        return False
    return True


def check_success(data):
    emails = get_added_emails(data)
    for e in emails:
        if not isinstance(e, dict):
            continue
        if not e.get("sent", False):
            continue
        # recipients
        to_list = e.get("to", [])
        if isinstance(to_list, str):
            to_list = [to_list]
        valid_to = any(
            is_valid_recipient(t) for t in (to_list if isinstance(to_list, list) else [])
        )
        if not valid_to:
            continue
        # subject
        if not subject_ok(e.get("subject", "")):
            continue
        # content/body
        if not content_ok(e.get("content", "")):
            continue
        return True
    return False


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return
    try:
        data = load_json(path)
        result = check_success(data)
        print("SUCCESS" if result else "FAILURE")
    except Exception:
        print("FAILURE")


if __name__ == "__main__":
    main()
