import json
import sys


def get_in(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


# Strategy:
# - Inspect initialfinaldiff added/updated sections for user-authored self-posts.
# - Validate that any such post's description contains both 'summer' and 'intern' substrings (case-insensitive).
# - Check ui.feed.postDynamicData and feedPosts entries; require type 'self-post' or author id 'divgarg'.

try:
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

initialfinaldiff = data.get("initialfinaldiff")
if not isinstance(initialfinaldiff, dict):
    print("FAILURE")
    sys.exit(0)

USER_ID = "divgarg"


def text_matches(desc):
    if not isinstance(desc, str):
        return False
    t = desc.lower()
    return ("summer" in t) and ("intern" in t)


def is_user_post(post):
    if not isinstance(post, dict):
        return False
    ptype = post.get("type")
    author_id = post.get("authorId")
    if author_id is None:
        author = post.get("author")
        if isinstance(author, dict):
            author_id = author.get("id")
    return (ptype == "self-post") or (author_id == USER_ID)


def scan_posts(container):
    # container is a dict mapping keys to post dicts
    if not isinstance(container, dict):
        return False
    for _, post in container.items():
        if not isinstance(post, dict):
            continue
        desc = post.get("description")
        if is_user_post(post) and text_matches(desc):
            return True
    return False


success = False

# Check ui.feed.postDynamicData in added and updated
for section in ("added", "updated"):
    sec = initialfinaldiff.get(section)
    if not isinstance(sec, dict):
        continue
    ui = sec.get("ui")
    if isinstance(ui, dict):
        feed = ui.get("feed")
        if isinstance(feed, dict):
            pdd = feed.get("postDynamicData")
            if isinstance(pdd, dict):
                if scan_posts(pdd):
                    success = True
                    break
    # Check feedPosts in this section as well
    fp = sec.get("feedPosts")
    if isinstance(fp, dict):
        if scan_posts(fp):
            success = True
            break

print("SUCCESS" if success else "FAILURE")
