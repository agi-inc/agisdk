import json
import sys

# Strategy in code comments:
# We determine success if a new text message authored by the agent was added to any chat.
# Primary check: added.ui.messaging.chatroomData.*.messages.* has a non-empty 'message' with type 'text' (if present),
# and the authorId matches the agent (prefer 'divgarg'), or matches updated lastMessageAuthorId, or the added message
# text matches updated lastMessage when lastMessageAuthorId is 'divgarg'.
# Fallback: If no added messages found, consider success when updated.ui.messaging.chatroomData shows
# lastMessageAuthorId == 'divgarg' with non-empty lastMessage and the chat appears in added typingIndicators.

def safe_get(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
        if cur is None:
            return None
    return cur


def ensure_dict(obj):
    return obj if isinstance(obj, dict) else {}


def iter_messages(messages_container):
    # messages_container may be a dict of id->obj or a list
    if isinstance(messages_container, dict):
        for msg in messages_container.values():
            yield msg
    elif isinstance(messages_container, list):
        for msg in messages_container:
            yield msg


def is_non_empty_text(s):
    return isinstance(s, str) and len(s.strip()) > 0


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    initdiff = ensure_dict(data.get('initialfinaldiff', {}))
    added = ensure_dict(initdiff.get('added', {}))
    updated = ensure_dict(initdiff.get('updated', {}))

    added_ui_messaging = ensure_dict(safe_get(added, 'ui', 'messaging'))
    updated_ui_messaging = ensure_dict(safe_get(updated, 'ui', 'messaging'))

    added_chat_data = ensure_dict(added_ui_messaging.get('chatroomData', {}))
    updated_chat_data = ensure_dict(updated_ui_messaging.get('chatroomData', {}))

    # Primary detection via added messages
    agent_ids = {'divgarg'}  # known agent id from examples; can expand if inferred elsewhere

    # Try to glean potential agent IDs from added messages or updated lastMessageAuthorId fields
    for chat_id, chat_obj in added_chat_data.items():
        msgs = chat_obj.get('messages')
        if isinstance(msgs, (dict, list)):
            for msg in iter_messages(msgs):
                a = msg.get('authorId')
                if isinstance(a, str) and a:
                    agent_ids.add(a)
    for chat_id, chat_obj in updated_chat_data.items():
        a = chat_obj.get('lastMessageAuthorId')
        if isinstance(a, str) and a:
            # Include as candidate; will be cross-validated against message content
            agent_ids.add(a)

    # Validate added messages
    for chat_id, chat_obj in added_chat_data.items():
        msgs = chat_obj.get('messages')
        if not isinstance(msgs, (dict, list)):
            continue
        upd_meta = ensure_dict(updated_chat_data.get(chat_id, {}))
        last_author = upd_meta.get('lastMessageAuthorId')
        last_message = upd_meta.get('lastMessage')
        for msg in iter_messages(msgs):
            if not isinstance(msg, dict):
                continue
            msg_text = msg.get('message')
            if not is_non_empty_text(msg_text):
                continue
            mtype = msg.get('type')
            if mtype is not None and mtype != 'text':
                continue
            author = msg.get('authorId')

            author_matches = False
            # Direct match to known agent ids
            if isinstance(author, str) and author in agent_ids:
                # Prefer matching to 'divgarg' if present; otherwise, still okay
                author_matches = True

            # Cross-check with updated metadata
            if not author_matches:
                if isinstance(author, str) and isinstance(last_author, str) and author == last_author:
                    author_matches = True
                elif isinstance(last_author, str) and last_author in agent_ids and is_non_empty_text(last_message):
                    # If updated shows agent as last author and messages match, accept
                    if last_message.strip() == str(msg_text).strip():
                        author_matches = True

            if author_matches:
                print("SUCCESS")
                return

    # Fallback: rely on updated metadata and typing indicators to strengthen signal
    typing_indicators = ensure_dict(added_ui_messaging.get('typingIndicators', {}))
    typing_chats = set(typing_indicators.keys()) if isinstance(typing_indicators, dict) else set()

    for chat_id, meta in updated_chat_data.items():
        if not isinstance(meta, dict):
            continue
        last_author = meta.get('lastMessageAuthorId')
        last_message = meta.get('lastMessage')
        if isinstance(last_author, str) and last_author in agent_ids and is_non_empty_text(last_message):
            # Require that the chat also appears in typing indicators added in this run
            if chat_id in typing_chats:
                print("SUCCESS")
                return

    print("FAILURE")

if __name__ == '__main__':
    main()
