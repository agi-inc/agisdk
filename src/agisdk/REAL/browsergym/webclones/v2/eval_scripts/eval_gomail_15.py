import json
import sys


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Verification logic for task:
# Goal: Ensure an email was sent to Danielle informing that a new system/software update has been launched/released.
# Strategy:
# 1) Look for any newly added email items (prefer differences.emails.added; fallback to initialfinaldiff.added.email.emails values).
# 2) Require recipient contains 'danielle' (to generalize addresses) and email marked sent (sent True if present).
# 3) Combine subject+content (lowercased) and verify it mentions an update (e.g., 'update' or typo 'uodate')
#    and indicates it went live (keywords like launched/released/deployed/rolled out/is out, etc.).
# 4) Print SUCCESS if any such email exists; else FAILURE.


def get_added_emails(data):
    emails = []
    try:
        added = data.get("differences", {}).get("emails", {}).get("added", [])
        if isinstance(added, list) and added:
            emails.extend([e for e in added if isinstance(e, dict)])
    except Exception:
        pass
    # Fallback to initialfinaldiff.added.email.emails dict values
    try:
        init_added = (
            data.get("initialfinaldiff", {}).get("added", {}).get("email", {}).get("emails", {})
        )
        if isinstance(init_added, dict) and init_added:
            for v in init_added.values():
                if isinstance(v, dict):
                    emails.append(v)
    except Exception:
        pass
    return emails


def text_mentions_update_and_launch(text: str) -> bool:
    t = (text or "").lower()
    # Must reference an update (allow common typo 'uodate')
    has_update = ("update" in t) or ("uodate" in t)
    # Must indicate launch/release/go-live
    launch_terms = [
        "launch",
        "launched",
        "release",
        "released",
        "deploy",
        "deployed",
        "rollout",
        "rolled out",
        "rolled-out",
        "roll out",
        "roll-out",
        "go live",
        "went live",
        "is live",
        "is out",
        "went-live",
        "go-live",
    ]
    has_launch_info = any(term in t for term in launch_terms)
    return has_update and has_launch_info


def is_email_to_danielle(email_obj: dict) -> bool:
    to_list = email_obj.get("to", [])
    if not isinstance(to_list, list):
        return False
    for addr in to_list:
        if isinstance(addr, str) and "danielle" in addr.lower():
            return True
    return False


def is_sent(email_obj: dict) -> bool:
    # Treat missing 'sent' as True to avoid false negatives if field is absent
    sent_flag = email_obj.get("sent")
    if sent_flag is None:
        return True
    return bool(sent_flag)


def verify(path):
    data = load_json(path)
    emails = get_added_emails(data)
    success = False
    for e in emails:
        if not isinstance(e, dict):
            continue
        if not is_email_to_danielle(e):
            continue
        if not is_sent(e):
            continue
        subject = e.get("subject", "") or ""
        content = e.get("content", "") or ""
        combined_text = f"{subject} {content}"
        if text_mentions_update_and_launch(combined_text):
            success = True
            break
    print("SUCCESS" if success else "FAILURE")


if __name__ == "__main__":
    verify(sys.argv[1])
