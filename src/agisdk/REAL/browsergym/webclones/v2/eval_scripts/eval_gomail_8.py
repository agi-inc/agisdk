import json
import sys

# Verification script for: Write an email to Kevin Moore to ask for the project details
# Strategy:
# 1) Find a newly added sent email addressed ONLY to kevin.moore@example.com (no CC/BCC).
# 2) Ensure the email body (not just subject) is non-empty and mentions both 'project' and 'detail' (case-insensitive).


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def strip_html(text):
    if not isinstance(text, str):
        return ""
    out = []
    in_tag = False
    for ch in text:
        if ch == "<":
            in_tag = True
            continue
        if ch == ">":
            in_tag = False
            continue
        if not in_tag:
            out.append(ch)
    return "".join(out)


def norm_email(val):
    if not isinstance(val, str):
        return ""
    return val.strip().lower()


def extract_added_emails(data):
    emails = []
    # From differences.emails.added
    try:
        added = data.get("differences", {}).get("emails", {}).get("added", [])
        if isinstance(added, list):
            emails.extend([e for e in added if isinstance(e, dict)])
    except Exception:
        pass
    # From initialfinaldiff.added.email.emails (dict)
    try:
        init_added = (
            data.get("initialfinaldiff", {}).get("added", {}).get("email", {}).get("emails", {})
        )
        if isinstance(init_added, dict):
            for _, v in init_added.items():
                if isinstance(v, dict):
                    emails.append(v)
    except Exception:
        pass
    return emails


def listify_recipients(val):
    # Normalize recipients to a list of non-empty, lowercased emails
    recips = []
    if isinstance(val, list):
        for x in val:
            if isinstance(x, str):
                s = norm_email(x)
                if s:
                    recips.append(s)
    elif isinstance(val, str):
        s = norm_email(val)
        if s:
            recips.append(s)
    return recips


def is_empty_cc_bcc(val):
    # Consider empty if missing, empty string, or list with only empty/whitespace strings
    if val is None:
        return True
    if isinstance(val, str):
        return val.strip() == ""
    if isinstance(val, list):
        for x in val:
            if isinstance(x, str) and x.strip() == "":
                continue
            # any non-empty entry counts as not empty
            if isinstance(x, str):
                return False
            else:
                return False
        return True
    # Any other type treat as not empty
    return False


def qualifies(email_obj):
    if not isinstance(email_obj, dict):
        return False
    # Must be sent
    if not email_obj.get("sent", False):
        return False
    # TO must be exactly Kevin Moore and only him
    to_recipients = listify_recipients(email_obj.get("to"))
    if len(to_recipients) != 1 or to_recipients[0] != "kevin.moore@example.com":
        return False
    # CC and BCC must be empty if present
    if not is_empty_cc_bcc(email_obj.get("cc")):
        return False
    if not is_empty_cc_bcc(email_obj.get("bcc")):
        return False
    # Content must meaningfully request project details
    content = email_obj.get("content") or ""
    content_text = strip_html(content).strip()
    if not content_text:
        return False
    low_body = content_text.lower()
    if ("project" not in low_body) or ("detail" not in low_body):
        return False
    return True


def main():
    path = sys.argv[1]
    data = load_json(path)
    emails = extract_added_emails(data)
    for e in emails:
        if qualifies(e):
            print("SUCCESS")
            return
    print("FAILURE")


if __name__ == "__main__":
    main()
