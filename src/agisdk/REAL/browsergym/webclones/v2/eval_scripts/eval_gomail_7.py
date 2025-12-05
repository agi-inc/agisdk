import json
import sys


def strip_tags(s: str) -> str:
    out = []
    in_tag = False
    for ch in s:
        if ch == "<":
            in_tag = True
            continue
        if ch == ">":
            in_tag = False
            continue
        if not in_tag:
            out.append(ch)
    return "".join(out)


def normalize_text(s):
    if not isinstance(s, str):
        return ""
    return strip_tags(s).lower().strip()


def split_recipients(to_field):
    # Return a list of lowercased trimmed recipient emails
    recips = []
    if isinstance(to_field, list):
        for v in to_field:
            if isinstance(v, str):
                recips.append(v.strip().lower())
    elif isinstance(to_field, str):
        # Split by comma if necessary
        parts = [p.strip() for p in to_field.split(",")]
        recips = [p.lower() for p in parts if p]
    return [r for r in recips if r]


def mentions_team_dinner_and_asking(text):
    t = normalize_text(text)
    if not t:
        return False
    # Require mention of team and dinner (or the phrase team dinner)
    has_team_dinner = ("team dinner" in t) or ("team" in t and "dinner" in t)
    if not has_team_dinner:
        return False
    # Indication of asking about attendance
    ask_tokens = [
        "come",
        "coming",
        "attend",
        "attending",
        "join",
        "joining",
        "able to make",
        "are you",
        "rsvp",
    ]
    return any(tok in t for tok in ask_tokens)


def is_valid_sent_email(email_obj):
    # Must be a sent email (if 'sent' exists it must be True). Not a draft/spam/trash.
    if isinstance(email_obj, dict):
        if "sent" in email_obj and not email_obj.get("sent", False):
            return False
        if email_obj.get("draft") is True:
            return False
        if email_obj.get("spam") is True:
            return False
        if email_obj.get("trash") is True:
            return False
        # To must be exactly and only Ashley
        to_list = split_recipients(email_obj.get("to"))
        target = "ashley.campbell@example.com"
        if len(to_list) != 1 or to_list[0] != target:
            return False
        # Content or subject must indicate asking about team dinner
        content = email_obj.get("content") or ""
        subject = email_obj.get("subject") or ""
        if mentions_team_dinner_and_asking(content) or mentions_team_dinner_and_asking(subject):
            return True
    return False


def main():
    try:
        path = sys.argv[1]
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        # Navigate to differences.emails.added
        diffs = data.get("differences") or {}
        emails = diffs.get("emails") or {}
        added = emails.get("added") or []
        # Ensure added is a list
        if not isinstance(added, list):
            added = []
        success = any(is_valid_sent_email(e) for e in added)
        print("SUCCESS" if success else "FAILURE")
    except Exception:
        # On any error, fail safely
        print("FAILURE")


if __name__ == "__main__":
    main()
