import json
import sys


def get_in(data, path, default=None):
    cur = data
    for key in path:
        if isinstance(cur, dict):
            if key in cur:
                cur = cur[key]
            else:
                return default
        else:
            return default
    return cur


# Determine if a message text is an invite to view/apply for a job
def is_invite_message(text):
    if not isinstance(text, str):
        return False
    t = text.strip().lower()
    # Consider common invite phrasing; require an invite keyword and mention of job/application context
    has_invite_keyword = ("invite" in t) or ("invited" in t) or ("invitation" in t)
    mentions_context = ("job" in t) or ("apply" in t) or ("proposal" in t) or ("position" in t)
    return has_invite_keyword and mentions_context


# Determine if contact's job indicates full-stack
def is_fullstack_job(job_str):
    if not isinstance(job_str, str):
        return False
    norm = job_str.lower().replace("-", " ")
    return "full stack" in norm


# Analyze a single contact to determine if they were invited and whether they are full-stack
# Returns (invited_bool, fullstack_bool)


def analyze_contact(contact):
    invited = False
    # Check messages block
    msgs = contact.get("messages")
    if isinstance(msgs, dict):
        for m in msgs.values():
            if (
                isinstance(m, dict)
                and m.get("author") == "Client"
                and is_invite_message(m.get("message"))
            ):
                invited = True
                break
    elif isinstance(msgs, list):
        for m in msgs:
            if (
                isinstance(m, dict)
                and m.get("author") == "Client"
                and is_invite_message(m.get("message"))
            ):
                invited = True
                break

    # Fallback to lastMessage if messages block didn't conclusively show an invite
    if not invited:
        if contact.get("lastMessageAuthor") == "Client" and is_invite_message(
            contact.get("lastMessage")
        ):
            invited = True

    fullstack = is_fullstack_job(contact.get("job"))
    return invited, fullstack


def main():
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)

    root = data
    if "initialfinaldiff" in root:
        root = root["initialfinaldiff"]

    total_invited_contacts = 0
    fullstack_invited_contacts = 0

    for section in ("updated", "added"):
        contacts_parent = get_in(root, [section, "messages", "contactList"])
        if isinstance(contacts_parent, dict):
            for _idx, contact in contacts_parent.items():
                if not isinstance(contact, dict):
                    continue
                invited, fullstack = analyze_contact(contact)
                if invited:
                    total_invited_contacts += 1
                    if fullstack:
                        fullstack_invited_contacts += 1

    # Success criteria: exactly one invite sent in this run and the invited contact is a full-stack developer
    if total_invited_contacts == 1 and fullstack_invited_contacts == 1:
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
