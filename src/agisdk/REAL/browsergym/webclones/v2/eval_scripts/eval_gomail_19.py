import json
import sys

# Verification script for: GoMail: send an email to Angela White asking when she goes on FTA
# Strategy:
# - Look for newly added emails (differences.emails.added and initialfinaldiff.added.email.emails)
# - A success requires: recipient matches Angela White and the content/subject mentions 'FTA' with a query cue like 'when'/'what'/'date(s)'; and the email is sent (not draft)


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def collect_added_emails(data):
    added_emails = []
    # From differences.emails.added (list)
    try:
        diffs = data.get("differences", {})
        emails = diffs.get("emails", {})
        added = emails.get("added", [])
        if isinstance(added, list):
            for item in added:
                if isinstance(item, dict):
                    added_emails.append(item)
    except Exception:
        pass
    # From initialfinaldiff.added.email.emails (dict of objects)
    try:
        if isinstance(data.get("initialfinaldiff"), dict):
            added_root = data["initialfinaldiff"].get("added", {})
            email_block = added_root.get("email", {})
            emails_map = email_block.get("emails", {})
            if isinstance(emails_map, dict):
                for _, item in emails_map.items():
                    if isinstance(item, dict):
                        added_emails.append(item)
    except Exception:
        pass
    return added_emails


def is_angela_recipient(to_list):
    if not isinstance(to_list, list):
        return False
    for t in to_list:
        if not isinstance(t, str):
            continue
        low = t.lower().strip()
        if low == "angela.white@example.com":
            return True
        if "angela.white@" in low:
            return True
        if "angela white" in low:
            return True
    return False


def mentions_fta_with_question(text):
    if not isinstance(text, str):
        return False
    low = text.lower()
    if "fta" not in low:
        return False
    # question cue words
    cues = ["when", "what", "date", "dates"]
    return any(cue in low for cue in cues)


def main():
    path = sys.argv[1]
    data = load_json(path)
    added_emails = collect_added_emails(data)

    success = False
    for em in added_emails:
        # Ensure not a draft and optionally sent
        if em.get("draft") is True:
            continue
        if "sent" in em and not em.get("sent"):
            continue
        to_list = em.get("to", [])
        if not is_angela_recipient(to_list):
            continue
        content = em.get("content") or ""
        subject = em.get("subject") or ""
        text = f"{subject} {content}"
        if mentions_fta_with_question(text):
            success = True
            break

    print("SUCCESS" if success else "FAILURE")


if __name__ == "__main__":
    main()
