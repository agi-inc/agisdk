import json, sys

# Strategy in code:
# 1) Detect a self-authored post by 'divgarg' whose description is non-empty and mentions a networking event and asks to DM.
#    - Search in initialfinaldiff.updated.feedPosts and any postDynamicData under ui.feed.
# 2) Confirm it was sent to a couple people by either:
#    - Finding chat messages of type 'post' authored by 'divgarg' (ideally referencing the created post), OR
#    - Presence of at least two entries in added.contactList (proxy for having connections to send to).
# 3) Print SUCCESS only if both (valid post) and (sent/share evidence) are satisfied.

def safe_get(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def gather_self_posts(data):
    posts = []  # list of tuples (post_id, description)

    # From updated.feedPosts
    feed_posts = safe_get(data, 'initialfinaldiff', 'updated', 'feedPosts')
    if isinstance(feed_posts, dict):
        for _, v in feed_posts.items():
            if not isinstance(v, dict):
                continue
            ptype = v.get('type')
            author = v.get('author', {}) if isinstance(v.get('author'), dict) else {}
            author_id = author.get('id') or v.get('authorId')
            desc = v.get('description')
            pid = v.get('id')
            if ptype == 'self-post' and author_id == 'divgarg' and isinstance(desc, str):
                posts.append((str(pid) if pid is not None else None, desc))

    # From any postDynamicData under ui.feed (may appear under added or updated)
    for section in ('added', 'updated'):
        pdd = safe_get(data, 'initialfinaldiff', section, 'ui', 'feed', 'postDynamicData')
        if isinstance(pdd, dict):
            for _, v in pdd.items():
                if not isinstance(v, dict):
                    continue
                ptype = v.get('type')
                author_id = v.get('authorId')
                desc = v.get('description')
                pid = v.get('id')
                if ptype == 'self-post' and author_id == 'divgarg' and isinstance(desc, str):
                    posts.append((str(pid) if pid is not None else None, desc))

    return posts


def is_valid_post_description(desc):
    if not isinstance(desc, str):
        return False
    text = desc.strip()
    # Must have some meaningful length and alphanumeric content
    if len(text) < 5:
        return False
    if not any(ch.isalnum() for ch in text):
        return False
    lower = text.lower()
    # Must mention networking (networking/network)
    mentions_network = 'network' in lower  # covers network, networking, networker
    # Must invite DMs - look for common patterns while avoiding false positives like 'random'
    dm_patterns = [
        ' dm', 'dm ', 'dm.', 'dm,', 'dm!', 'dm?',  # dm as a separate token-ish
        'dm me', 'please dm', 'pls dm', 'direct message', 'message me', 'msg me', 'inbox me', 'pm me'
    ]
    invites_dm = lower.startswith('dm') or any(pat in lower for pat in dm_patterns)
    return mentions_network and invites_dm


def find_share_evidence(data, valid_post_ids):
    # A) Check chatroom messages of type 'post' by divgarg, ideally referencing one of the valid posts
    chatroot = safe_get(data, 'initialfinaldiff', 'added', 'ui', 'messaging', 'chatroomData')
    share_count = 0
    if isinstance(chatroot, dict):
        for _, chat in chatroot.items():
            if not isinstance(chat, dict):
                continue
            msgs = chat.get('messages')
            # messages can be dict or list
            if isinstance(msgs, dict):
                msg_iter = msgs.values()
            elif isinstance(msgs, list):
                msg_iter = msgs
            else:
                msg_iter = []
            for m in msg_iter:
                if not isinstance(m, dict):
                    continue
                if m.get('type') == 'post' and m.get('authorId') == 'divgarg':
                    pd = m.get('postData') or {}
                    pid = str(pd.get('id')) if pd.get('id') is not None else None
                    # Count it as a share if it either matches a valid post id or no id provided (fallback)
                    if (valid_post_ids and pid in valid_post_ids) or (not valid_post_ids):
                        share_count += 1
                        break  # count per chatroom at most once
    # Consider shared to a couple people if at least 2 chatrooms contain such a message
    if share_count >= 2:
        return True

    # B) Alternatively, presence of at least two contacts in added.contactList
    cl = safe_get(data, 'initialfinaldiff', 'added', 'contactList')
    if isinstance(cl, dict) and len(cl) >= 2:
        return True

    return False


def main():
    if len(sys.argv) < 2:
        print('FAILURE')
        return
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    if not isinstance(data, dict) or not data.get('initialfinaldiff'):
        print('FAILURE')
        return

    posts = gather_self_posts(data)
    # Filter valid posts by description content
    valid_posts = [(pid, desc) for pid, desc in posts if is_valid_post_description(desc)]
    valid_post_ids = set(pid for pid, _ in valid_posts if pid)

    has_valid_post = len(valid_posts) > 0
    has_share = find_share_evidence(data, valid_post_ids)

    if has_valid_post and has_share:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
