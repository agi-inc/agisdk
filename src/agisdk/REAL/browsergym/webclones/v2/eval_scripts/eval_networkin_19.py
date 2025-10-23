import json, sys, re

def normalize(text: str) -> str:
    # Lowercase and strip non-alphanumeric except spaces for robust matching
    t = text.lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

# Verification logic:
# - Require a diff present
# - Find posts in updated.feedPosts that are self-posts by the user (author.id == 'divgarg')
#   whose description indicates finishing the internship at AGI INC.
#   We require: contains 'internship', contains 'agi inc', and a completion verb (finish*/complet*).
# - Exactly one such matching post => SUCCESS
# - If multiple matching posts or multiple user posts added in this session => FAILURE (duplicate posting)
# - If none match => FAILURE

def is_matching_post(post: dict) -> bool:
    if not isinstance(post, dict):
        return False
    if post.get('type') != 'self-post':
        return False
    author = post.get('author') or {}
    if not isinstance(author, dict) or author.get('id') != 'divgarg':
        return False
    desc = post.get('description')
    if not isinstance(desc, str):
        return False
    norm = normalize(desc)
    if not norm:
        return False
    # Must mention internship and AGI INC and have completion intent
    if 'internship' not in norm:
        return False
    if 'agi inc' not in norm:
        return False
    if not (re.search(r"\bfinish\w*\b", norm) or re.search(r"\bcomplet\w*\b", norm)):
        return False
    return True


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    idiff = data.get('initialfinaldiff')
    if not idiff or not isinstance(idiff, dict):
        print("FAILURE")
        return

    updated_posts = ((idiff.get('updated') or {}).get('feedPosts') or {})
    if not isinstance(updated_posts, dict):
        updated_posts = {}

    # Count matching posts
    match_count = 0
    for _, post in updated_posts.items():
        if is_matching_post(post):
            match_count += 1

    # Detect duplicates via added feedPosts authored by the user in this session
    added_fp = ((idiff.get('added') or {}).get('feedPosts') or {})
    if not isinstance(added_fp, dict):
        added_fp = {}
    user_added_count = 0
    for _, v in added_fp.items():
        if isinstance(v, dict) and v.get('authorId') == 'divgarg':
            user_added_count += 1

    # Decision
    if match_count == 1 and user_added_count <= 1:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == '__main__':
    main()
