import json, sys, re

def walk_collect(dict_or_list, target_keys):
    """Recursively collect values for any of the target_keys found in nested dicts."""
    found = {k: [] for k in target_keys}
    def _walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in target_keys:
                    found[k].append(v)
                _walk(v)
        elif isinstance(obj, list):
            for it in obj:
                _walk(it)
    _walk(dict_or_list)
    return found


def normalize_text(s):
    if not isinstance(s, str):
        return ""
    return s.strip().lower()


def content_mentions_network_and_dm(text):
    s = normalize_text(text)
    if not s:
        return False
    # Must mention DM explicitly and something about networking
    dm_flag = bool(re.search(r"\bdm\b", s)) or ("direct message" in s) or ("message me" in s)
    network_flag = ("network" in s)  # covers network, networking, networker, etc.
    return dm_flag and network_flag


def extract_candidate_posts(data):
    # Gather potential self-posts created by the user (divgarg)
    candidates = []  # list of dicts with keys: id, description
    collectors = walk_collect(data, {"postDynamicData", "feedPosts"})

    # From postDynamicData
    for pdd in collectors.get("postDynamicData", []):
        if isinstance(pdd, dict):
            for pid, pobj in pdd.items():
                if not isinstance(pobj, dict):
                    continue
                p_type = pobj.get("type")
                author_id = pobj.get("authorId")
                desc = pobj.get("description")
                if p_type == "self-post" and author_id == "divgarg" and isinstance(desc, str):
                    candidates.append({"id": str(pobj.get("id", pid)), "description": desc})

    # From feedPosts (sometimes used instead of UI feed dynamic data)
    for fp in collectors.get("feedPosts", []):
        if isinstance(fp, dict):
            for _, post in fp.items():
                if not isinstance(post, dict):
                    continue
                p_type = post.get("type")
                # author could be nested as dict or as authorId
                author_info = post.get("author")
                author_id = None
                if isinstance(author_info, dict):
                    author_id = author_info.get("id")
                if author_id is None:
                    author_id = post.get("authorId")
                desc = post.get("description")
                if p_type == "self-post" and author_id == "divgarg" and isinstance(desc, str):
                    pid = str(post.get("id", "")) or None
                    if pid:
                        candidates.append({"id": pid, "description": desc})
    return candidates


def count_unique_shares_for_post(data, post_id):
    # Count unique chatrooms (recipients) that received a post message referencing this post_id
    recipients = set()
    collectors = walk_collect(data, {"chatroomData"})
    for crd in collectors.get("chatroomData", []):
        if not isinstance(crd, dict):
            continue
        for chat_id, chat in crd.items():
            if not isinstance(chat, dict):
                continue
            messages = chat.get("messages")
            if isinstance(messages, dict):
                iterable = messages.values()
            elif isinstance(messages, list):
                iterable = messages
            else:
                iterable = []
            for msg in iterable:
                if not isinstance(msg, dict):
                    continue
                if msg.get("type") == "post":
                    pd = msg.get("postData", {})
                    if isinstance(pd, dict) and str(pd.get("id")) == str(post_id):
                        recipients.add(chat_id)
                        break  # count each chatroom once
    return len(recipients)


def main():
    # Strategy: find a self-post by divgarg that mentions both DM and a networking event, then verify it was shared to >=2 contacts.
    # If any qualifying post satisfies both content and share-count conditions, declare SUCCESS; else FAILURE.
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    root = data.get("initialfinaldiff") or data

    candidates = extract_candidate_posts(root)

    # Evaluate each candidate for content and share criteria
    for cand in candidates:
        desc = cand.get("description", "")
        pid = cand.get("id")
        if not pid:
            continue
        if not content_mentions_network_and_dm(desc):
            continue
        share_count = count_unique_shares_for_post(root, pid)
        if share_count >= 2:
            print("SUCCESS")
            return

    print("FAILURE")

if __name__ == "__main__":
    main()
