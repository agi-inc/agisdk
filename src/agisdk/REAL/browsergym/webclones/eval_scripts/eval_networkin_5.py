import json, sys

def get_path(d, path):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def merge_dicts(a, b):
    res = {}
    if isinstance(a, dict):
        res.update(a)
    if isinstance(b, dict):
        # values from b override a when same key, but keys are unique per contact/post
        res.update(b)
    return res


def count_outbound_accepts(chatrooms):
    # Count contacts where there is a system message indicating our outbound request was accepted
    count = 0
    if not isinstance(chatrooms, dict):
        return 0
    for chat in chatrooms.values():
        msgs = []
        if isinstance(chat, dict):
            msgs = chat.get('messages', [])
        accepted = False
        if isinstance(msgs, list):
            for m in msgs:
                if not isinstance(m, dict):
                    continue
                if m.get('authorId') == 'system':
                    msg_text = str(m.get('message', '')).lower()
                    if 'accepted your connection request' in msg_text:
                        accepted = True
                        break
        if accepted:
            count += 1
    return count


def count_likes(user_interactions):
    if not isinstance(user_interactions, dict):
        return 0
    likes = 0
    for v in user_interactions.values():
        if isinstance(v, dict) and v.get('liked') is True:
            likes += 1
    return likes


def main():
    # Strategy: require >=5 outbound connections (system acceptance messages in chatrooms)
    # and >=3 liked posts (liked: true in ui.feed.userInteractions). Merge data from added and updated for robustness.
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)
    diff = data.get('initialfinaldiff', {})
    added = diff.get('added', {})
    updated = diff.get('updated', {})

    # Gather chatroomData from both added and updated
    chat_added = get_path(added, ['ui', 'messaging', 'chatroomData'])
    chat_updated = get_path(updated, ['ui', 'messaging', 'chatroomData'])
    chatrooms = merge_dicts(chat_added, chat_updated)

    # Gather userInteractions from both added and updated
    ui_added = get_path(added, ['ui', 'feed', 'userInteractions'])
    ui_updated = get_path(updated, ['ui', 'feed', 'userInteractions'])
    interactions = merge_dicts(ui_added, ui_updated)

    outbound_accepts = count_outbound_accepts(chatrooms)
    liked_count = count_likes(interactions)

    if outbound_accepts >= 5 and liked_count >= 3:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
