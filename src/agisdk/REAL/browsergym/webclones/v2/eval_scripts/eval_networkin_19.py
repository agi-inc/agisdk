import json, sys

def get(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def collect_post_dynamic_data(data):
    posts = {}
    for section in ("added", "updated"):
        pdd = get(data, ["initialfinaldiff", section, "ui", "feed", "postDynamicData"], {})
        if isinstance(pdd, dict):
            posts.update(pdd)
    return posts


def text_matches_excited_aginc(title, desc):
    t = (title or "") + " " + (desc or "")
    t = t.lower()
    return ("excited" in t) and ("agi inc" in t)


def find_excited_self_post_ids(data):
    posts = collect_post_dynamic_data(data)
    ids = set()
    for pid, p in posts.items():
        if not isinstance(p, dict):
            continue
        title = p.get("title") or ""
        desc = p.get("description") or ""
        if not text_matches_excited_aginc(title, desc):
            continue
        ptype = p.get("type")
        author_ok = (p.get("authorId") == "divgarg")
        # Prefer self-authored posts; allow if type is self-post or author is the user
        if (ptype == "self-post") or (ptype is None and author_ok) or author_ok:
            ids.add(p.get("id") or pid)
    return ids


def iterate_messages_container(messages):
    if isinstance(messages, list):
        for m in messages:
            yield m
    elif isinstance(messages, dict):
        for m in messages.values():
            yield m


def collect_recipients_for_post_ids(data, valid_post_ids):
    recipients = set()
    for section in ("added", "updated"):
        chatrooms = get(data, ["initialfinaldiff", section, "ui", "messaging", "chatroomData"], {})
        if not isinstance(chatrooms, dict):
            continue
        for room_key, room_val in chatrooms.items():
            if not isinstance(room_val, dict):
                continue
            msgs = room_val.get("messages")
            if msgs is None:
                continue
            for msg in iterate_messages_container(msgs):
                if not isinstance(msg, dict):
                    continue
                if msg.get("type") != "post":
                    continue
                pd = msg.get("postData") or {}
                pid = pd.get("id")
                if pid in valid_post_ids:
                    recipients.add(room_key)
                    break  # Count each chatroom at most once
    return recipients


def main():
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    excited_post_ids = find_excited_self_post_ids(data)
    if not excited_post_ids:
        print("FAILURE")
        return

    recipients = collect_recipients_for_post_ids(data, excited_post_ids)

    # Must be exactly 5 unique recipients
    if len(recipients) == 5:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    main()
