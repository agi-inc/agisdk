import json
import sys


def find_dicts_with_key(obj, target_key):
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == target_key and isinstance(v, dict):
                found.append(v)
            # Recurse into children
            found.extend(find_dicts_with_key(v, target_key))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(find_dicts_with_key(item, target_key))
    return found


def count_acceptances_from_chatrooms(added_section):
    accepted_users = set()
    if not isinstance(added_section, (dict, list)):
        return 0
    chatroom_dicts = find_dicts_with_key(added_section, "chatroomData")
    for crd in chatroom_dicts:
        if not isinstance(crd, dict):
            continue
        for user_key, chatroom in crd.items():
            if not isinstance(chatroom, dict):
                continue
            msgs = chatroom.get("messages")
            if not isinstance(msgs, list):
                continue
            for m in msgs:
                if not isinstance(m, dict):
                    continue
                msg_txt = m.get("message")
                if (
                    isinstance(msg_txt, str)
                    and "accepted your connection request" in msg_txt.lower()
                ):
                    accepted_users.add(user_key)
                    break  # count each user once
    return len(accepted_users)


def count_new_contacts_from_contactlists(added_section):
    contacts = set()
    if not isinstance(added_section, (dict, list)):
        return 0
    contact_lists = find_dicts_with_key(added_section, "contactList")
    for cl in contact_lists:
        if isinstance(cl, dict):
            for _, v in cl.items():
                # Values appear to be username strings
                if isinstance(v, str) and v.strip():
                    contacts.add(v)
    return len(contacts)


def main():
    try:
        path = sys.argv[1]
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    diff = data.get("initialfinaldiff")
    if not isinstance(diff, dict):
        print("FAILURE")
        return

    added = diff.get("added", {})

    accepted_count = count_acceptances_from_chatrooms(added)
    contact_count = count_new_contacts_from_contactlists(added)

    connected_count = max(accepted_count, contact_count)

    if connected_count >= 3:
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
