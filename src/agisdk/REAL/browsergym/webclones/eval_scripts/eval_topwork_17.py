import json, sys

def get_nested(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

# Strategy in code:
# - Parse initialfinaldiff.updated/added.messages.contactList entries.
# - A run is SUCCESS if any contact has a lastMessage authored by the employer
#   (i.e., lastMessageAuthor != contact's name) and the lastMessage contains
#   availability/scheduling keywords (free, available, meet, discuss, call, schedule, etc).
# - This focuses on the 'lastMessage' (most recent) to avoid false positives from older messages.

keywords = [
    "free", "available", "availability", "meet", "meeting", "call", "discuss",
    "schedule", "chat", "talk", "time", "tomorrow", "today", "this week", "soon"
]


def collect_contacts(section):
    contacts = []
    if not isinstance(section, dict):
        return contacts
    msg = section.get("messages", {})
    cl = msg.get("contactList", {})
    if isinstance(cl, dict):
        for _, v in cl.items():
            if isinstance(v, dict):
                contacts.append(v)
    return contacts


def message_indicates_availability(text: str) -> bool:
    if not isinstance(text, str):
        return False
    t = text.strip().lower()
    return any(k in t for k in keywords)


def is_outgoing(contact: dict) -> bool:
    # Consider it outgoing if lastMessageAuthor exists and is not the contact's name
    last_author = contact.get("lastMessageAuthor")
    name = contact.get("name")
    if isinstance(last_author, str) and isinstance(name, str):
        if last_author.strip() and name.strip() and last_author.strip() != name.strip():
            return True
    return False


def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    diff = data.get("initialfinaldiff", {})

    success = False

    # Gather contacts from updated and added sections
    for section_name in ("updated", "added"):
        section = diff.get(section_name, {})
        contacts = collect_contacts(section)
        for c in contacts:
            last_msg = c.get("lastMessage")
            if last_msg and is_outgoing(c) and message_indicates_availability(last_msg):
                success = True
                break
        if success:
            break

    print("SUCCESS" if success else "FAILURE")

if __name__ == "__main__":
    main()
