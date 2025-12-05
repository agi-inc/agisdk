import json
import sys


def contains_help_setup(text: str) -> bool:
    if not isinstance(text, str):
        return False
    t = text.lower().strip()
    # Core intent: communicate willingness to help get set up
    return ("get set up" in t) and ("help" in t)


def iter_added_messages(added):
    try:
        contact_list = added.get("messages", {}).get("contactList", {})
        if isinstance(contact_list, dict):
            for conv in contact_list.values():
                msgs = conv.get("messages", {})
                if isinstance(msgs, dict):
                    for m in msgs.values():
                        if isinstance(m, dict):
                            yield m
    except Exception:
        return


def find_updated_conv(updated, target_id: str):
    # Find a conversation by id or name in updated contactList
    contact_list = updated.get("messages", {}).get("contactList", {})
    if not isinstance(contact_list, dict):
        return None
    for conv in contact_list.values():
        if not isinstance(conv, dict):
            continue
        cid = conv.get("id")
        cname = conv.get("name")
        if cid == target_id or cname == "Alex Rodriguez":
            return conv
    return None


def main():
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    root = data.get("initialfinaldiff", {})
    added = root.get("added", {})
    updated = root.get("updated", {})

    selected_chat_id = None
    try:
        selected_chat_id = added.get("messages", {}).get("selectedChatId")
    except Exception:
        selected_chat_id = None

    # Strategy A: Check newly added message in the currently selected chat is to Alex Rodriguez and contains intent
    success_a = False
    if selected_chat_id == "alexrodriguez":
        for m in iter_added_messages(added):
            author = m.get("author")
            msg_text = m.get("message")
            if author == "Sarah Johnson" and contains_help_setup(msg_text):
                success_a = True
                break

    # Strategy B: Fallback - Check updated conversation for Alex Rodriguez reflects the correct last message by Sarah Johnson
    success_b = False
    conv = find_updated_conv(updated, "alexrodriguez")
    if isinstance(conv, dict):
        last_author = conv.get("lastMessageAuthor")
        last_msg = conv.get("lastMessage")
        if last_author == "Sarah Johnson" and contains_help_setup(last_msg):
            success_b = True

    if success_a or success_b:
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
