import json
import sys


def iter_contacts(cl):
    if not isinstance(cl, dict):
        return []
    return list(cl.values())


def iter_messages(msgs):
    # msgs can be a list or a dict with numeric keys
    if msgs is None:
        return []
    if isinstance(msgs, list):
        return msgs
    if isinstance(msgs, dict):
        return list(msgs.values())
    return []


def contains_availability_intent(text: str) -> bool:
    if not text:
        return False
    t = text.strip().lower()
    # Core availability/meeting intent keywords
    keywords = [
        "free",
        "available",
        "availability",
        "schedule",
        "scheduled",
        "scheduling",
        "meet",
        "meeting",
        "call",
        "chat",
        "interview",
        "time",
        "slot",
        "connect",
        "today",
        "tomorrow",
        "tonight",
        "morning",
        "afternoon",
        "evening",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "this week",
        "next week",
    ]
    return any(k in t for k in keywords)


def find_success(diff: dict) -> bool:
    # Strategy in code:
    # 1) Look for any contact where the last message is authored by the employer (Sarah Johnson)
    # 2) Ensure the message content indicates asking about availability (keywords)
    # 3) Check both updated and added contact lists; handle dict/list shapes robustly

    def check_contact(contact) -> bool:
        # Check lastMessageAuthor + lastMessage first
        last_author = str(contact.get("lastMessageAuthor", "")).strip().lower()
        last_msg = contact.get("lastMessage")
        if last_author == "sarah johnson" and contains_availability_intent(
            str(last_msg) if last_msg is not None else ""
        ):
            return True
        # Then inspect individual messages for a new outgoing authored by Sarah Johnson
        msgs = iter_messages(contact.get("messages"))
        for m in msgs:
            author = str(m.get("author", "")).strip().lower()
            msg_text = str(m.get("message", "") if m.get("message") is not None else "")
            if author == "sarah johnson" and contains_availability_intent(msg_text):
                return True
        return False

    updated_contacts = []
    added_contacts = []
    try:
        updated_contacts = iter_contacts(
            diff.get("updated", {}).get("messages", {}).get("contactList", {})
        )
    except Exception:
        updated_contacts = []
    try:
        added_contacts = iter_contacts(
            diff.get("added", {}).get("messages", {}).get("contactList", {})
        )
    except Exception:
        added_contacts = []

    for c in updated_contacts:
        if check_contact(c):
            return True
    for c in added_contacts:
        if check_contact(c):
            return True
    return False


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return
    diff = data.get("initialfinaldiff", {})
    if find_success(diff):
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
