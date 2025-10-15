import json, sys

# Verification criteria:
# 1) The message must be sent to the chatroom for 'alexarichardson' (recipient correctness)
# 2) There must be at least one message of type 'post' in that chatroom
# 3) The shared post must be about something new (e.g., contains 'new features', 'something new', or 'new' as a standalone word)
# 4) Ignore feed/self posts and posts sent to other contacts


def extract_chatroom_messages(section):
    messages = []
    if not isinstance(section, dict):
        return messages
    ui = section.get('ui', {}) if isinstance(section, dict) else {}
    messaging = ui.get('messaging', {}) if isinstance(ui, dict) else {}
    chatrooms = messaging.get('chatroomData', {}) if isinstance(messaging, dict) else {}

    chat = None
    if isinstance(chatrooms, dict):
        chat = chatrooms.get('alexarichardson')
    # If no chatroom for the target contact, return empty
    if not isinstance(chat, dict):
        return messages

    msgs = chat.get('messages', {})
    if isinstance(msgs, dict):
        iterable = msgs.values()
    elif isinstance(msgs, list):
        iterable = msgs
    else:
        iterable = []

    for m in iterable:
        if isinstance(m, dict):
            messages.append(m)
    return messages


def is_new_related(post_data):
    if not isinstance(post_data, dict):
        return False
    title = str(post_data.get('title', '') or '')
    desc = str(post_data.get('description', '') or '')
    text = (title + ' ' + desc).lower()
    text = ' '.join(text.split())  # normalize whitespace

    # Strong signals
    strong_phrases = [
        'new feature',
        'new features',
        'something new',
        'brand new',
    ]
    if any(p in text for p in strong_phrases):
        return True

    # Fallback: presence of 'new' as a standalone word
    # Avoid importing regex; approximate by tokenizing on spaces and punctuation
    cleaned = text
    for ch in ['!', '.', ',', '?', ';', ':', '\n', '\t', '(', ')', '[', ']', '{', '}', '"', '\'']:
        cleaned = cleaned.replace(ch, ' ')
    tokens = [tok for tok in cleaned.split(' ') if tok]
    if 'new' in tokens:
        return True

    return False


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print('FAILURE')
        return

    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    diff = data.get('initialfinaldiff', {})

    messages = []
    for sec_name in ['added', 'updated']:
        sec = diff.get(sec_name)
        messages.extend(extract_chatroom_messages(sec))

    success = False
    for m in messages:
        if isinstance(m, dict) and m.get('type') == 'post':
            if is_new_related(m.get('postData', {})):
                success = True
                break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
