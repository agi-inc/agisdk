import json, sys

def get_nested(d, *keys):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def text_indicates_help_set_up(text: str) -> bool:
    if not isinstance(text, str):
        return False
    s = text.lower()
    # Require indication of willingness to help and setup
    has_help = "help" in s
    has_setup = ("set up" in s) or ("setup" in s)
    return has_help and has_setup


def any_added_msg_matches_for_alex(initialfinaldiff: dict) -> bool:
    added = initialfinaldiff.get('added', {}) or {}
    messages_root = added.get('messages', {}) or {}
    selected_chat_id = messages_root.get('selectedChatId')

    contact_list = get_nested(added, 'messages', 'contactList')
    if isinstance(contact_list, dict):
        for _, contact in contact_list.items():
            msgs = (contact or {}).get('messages') or {}
            if isinstance(msgs, dict):
                for _, m in msgs.items():
                    if not isinstance(m, dict):
                        continue
                    author = m.get('author')
                    msg_text = m.get('message')
                    if author == 'Sarah Johnson' and text_indicates_help_set_up(msg_text):
                        # Try to ensure this is to Alex Rodriguez by contact id or selected chat
                        contact_id = (contact or {}).get('id')
                        if contact_id == 'alexrodriguez' or selected_chat_id == 'alexrodriguez':
                            return True
    return False


def any_updated_last_message_matches_for_alex(initialfinaldiff: dict) -> bool:
    updated = initialfinaldiff.get('updated', {}) or {}
    # Check selected chat id if present anywhere in updated
    selected_chat_id = get_nested(updated, 'messages', 'selectedChatId')
    contact_list = get_nested(updated, 'messages', 'contactList')
    if not isinstance(contact_list, dict):
        return False

    for _, contact in contact_list.items():
        if not isinstance(contact, dict):
            continue
        last_author = contact.get('lastMessageAuthor')
        last_msg = contact.get('lastMessage')
        contact_id = contact.get('id')
        # We consider it Alex's chat if the contact id matches or the selectedChatId is alexrodriguez
        is_alex_chat = (contact_id == 'alexrodriguez') or (selected_chat_id == 'alexrodriguez')
        if is_alex_chat and last_author == 'Sarah Johnson' and text_indicates_help_set_up(last_msg):
            return True
    return False


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    initialfinaldiff = data.get('initialfinaldiff') or {}

    # Strategy:
    # 1) Look for added message authored by Sarah Johnson in Alex Rodriguez chat with content expressing help to get set up.
    # 2) If not found, check updated lastMessage for Alex chat with same content.
    success = False

    if any_added_msg_matches_for_alex(initialfinaldiff):
        success = True
    elif any_updated_last_message_matches_for_alex(initialfinaldiff):
        success = True

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()