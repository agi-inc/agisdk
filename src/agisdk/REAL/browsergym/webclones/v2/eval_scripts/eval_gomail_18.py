import json
import sys


def extract_added_emails(data):
    emails = []
    # Prefer differences.emails.added when available
    try:
        added = data.get("differences", {}).get("emails", {}).get("added", [])
        if isinstance(added, list):
            emails.extend(added)
    except Exception:
        pass
    # Fallback to initialfinaldiff.added.email.emails values
    try:
        iadd = data.get("initialfinaldiff", {}).get("added", {}).get("email", {}).get("emails", {})
        if isinstance(iadd, dict):
            emails.extend(list(iadd.values()))
        elif isinstance(iadd, list):
            emails.extend(iadd)
    except Exception:
        pass
    return emails


def is_success(data):
    # Strategy:
    # 1) Find any added, actually-sent email to brian.king@example.com.
    # 2) Ensure the message explicitly references meeting notes and makes a request (e.g., send/share/forward/provide), and is not trivial.
    target_email = "brian.king@example.com"
    added_emails = extract_added_emails(data)

    for em in added_emails:
        if not isinstance(em, dict):
            continue
        sent = bool(em.get("sent", False))
        # Exclude drafts/spam/trash if flagged
        if not sent or em.get("draft", False) or em.get("spam", False) or em.get("trash", False):
            continue
        # Collect recipients from to/cc/bcc
        recipients = []
        for k in ["to", "cc", "bcc"]:
            vals = em.get(k)
            if isinstance(vals, list):
                recipients.extend([str(v).lower() for v in vals])
            elif isinstance(vals, str):
                recipients.append(vals.lower())
        if target_email.lower() not in recipients:
            continue

        subject = str(em.get("subject", "") or "")
        content = str(em.get("content", "") or "")
        combined = (subject + " " + content).lower()

        # Ensure it references meeting notes
        topic_present = ("meeting notes" in combined) or (
            "meeting" in combined and "notes" in combined
        )

        # Ensure it contains a request verb indicating action from Brian
        request_keywords = ["send", "share", "forward", "provide"]
        request_present = any(kw in combined for kw in request_keywords)

        # Content should not be trivial (like '.')
        letters_count = sum(1 for c in content if c.isalpha())
        non_trivial = letters_count >= 3 and content.strip() != "."

        if topic_present and request_present and non_trivial:
            return True
    return False


def main():
    try:
        path = sys.argv[1]
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        print("SUCCESS" if is_success(data) else "FAILURE")
    except Exception:
        # On any unexpected parsing error, fail safe
        print("FAILURE")


if __name__ == "__main__":
    main()
