import json, sys

def text_matches_goal(text: str) -> bool:
    if not text or not isinstance(text, str):
        return False
    t = text.strip().lower()
    if len(t) < 5:
        return False
    # Must reference the internship and AGI INC and indicate completion
    if 'internship' not in t:
        return False
    if 'agi inc' not in t:
        return False
    completion_markers = [
        'finish', 'finished', 'finishing',
        'complete', 'completed', 'completing',
        'done', 'ended', 'conclude', 'concluded'
    ]
    if not any(marker in t for marker in completion_markers):
        return False
    return True


def collect_matching_posts(diff: dict):
    matching = []  # list of tuples (unique_key, id, description)
    seen_keys = set()

    def add_post(post_obj, source):
        if not isinstance(post_obj, dict):
            return
        p_type = post_obj.get('type')
        if p_type != 'self-post':
            return
        # Author can be under authorId or author.id
        author_id = post_obj.get('authorId')
        if not author_id:
            author = post_obj.get('author') or {}
            author_id = author.get('id')
        if author_id != 'divgarg':
            return
        desc = post_obj.get('description')
        if not text_matches_goal(desc):
            return
        pid = post_obj.get('id')
        # Build unique key: prefer id if present, else fallback to (source, desc, timestamp)
        if isinstance(pid, str) and pid:
            key = ('id', pid)
        else:
            ts = post_obj.get('timestamp') or ''
            key = (source, (desc or '').strip().lower(), str(ts))
        if key in seen_keys:
            return
        seen_keys.add(key)
        matching.append((key, pid, desc))

    # From updated.feedPosts
    updated = (diff.get('updated') or {})
    feed_posts_updated = (updated.get('feedPosts') or {})
    if isinstance(feed_posts_updated, dict):
        for v in feed_posts_updated.values():
            add_post(v, 'feedPosts.updated')

    # From added.ui.feed.postDynamicData
    added = (diff.get('added') or {})
    ui_added = (added.get('ui') or {})
    feed_added = (ui_added.get('feed') or {})
    pdd_added = (feed_added.get('postDynamicData') or {})
    if isinstance(pdd_added, dict):
        for v in pdd_added.values():
            add_post(v, 'ui.added.postDynamicData')

    # From updated.ui.feed.postDynamicData (in case)
    ui_updated = (updated.get('ui') or {})
    feed_updated = (ui_updated.get('feed') or {})
    pdd_updated = (feed_updated.get('postDynamicData') or {})
    if isinstance(pdd_updated, dict):
        for v in pdd_updated.values():
            add_post(v, 'ui.updated.postDynamicData')

    return matching


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

    diff = data.get('initialfinaldiff')
    if not diff:
        print('FAILURE')
        return

    matching = collect_matching_posts(diff)

    # Exactly one matching self-post should be created
    if len(matching) == 1:
        print('SUCCESS')
    else:
        # len == 0 -> no correct post; len > 1 -> posted it twice
        print('FAILURE')

if __name__ == '__main__':
    main()
