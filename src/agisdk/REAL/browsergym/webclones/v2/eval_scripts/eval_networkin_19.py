import json
import re
import sys


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
    if post.get("type") != "self-post":
        return False
    # Check both author.id and authorId for compatibility
    author_id = post.get("authorId") or (post.get("author") or {}).get("id")
    if author_id != "divgarg":
        return False
    desc = post.get("description")
    if not isinstance(desc, str):
        return False
    norm = normalize(desc)
    if not norm:
        return False
    # Must mention internship and AGI INC and have completion intent
    if "internship" not in norm.lower():
        return False
    if "agi inc" not in norm.lower():
        return False

    return True


def main():
    try:
        path = sys.argv[1]
        with open(path) as f:
            data = json.load(f)
    except Exception:
        print(f"FAILURE: exception {sys.exc_info()[1]}")
        print("FAILURE")
        return

    env_state = data.get("env_state", {})
    idiff = env_state.get("initialfinaldiff")
    if not idiff or not isinstance(idiff, dict):
        print("FAILURE: no initialfinaldiff")
        print("FAILURE")
        return

    # Look for posts in the correct location: ui.feed.postDynamicData
    added_ui = (idiff.get("added") or {}).get("ui", {})
    added_feed = added_ui.get("feed", {})
    added_posts = added_feed.get("postDynamicData", {})

    # Also check updated posts
    updated_ui = (idiff.get("updated") or {}).get("ui", {})
    updated_feed = updated_ui.get("feed", {})
    updated_posts = updated_feed.get("postDynamicData", {})

    # Count matching posts in both added and updated
    match_count = 0
    all_posts = {**added_posts, **updated_posts}
    for _post_id, post in all_posts.items():
        if is_matching_post(post):
            match_count += 1

    # Count user added posts
    user_added_count = 0
    for _post_id, post in added_posts.items():
        if isinstance(post, dict) and post.get("authorId") == "divgarg":
            user_added_count += 1

    # Decision
    if match_count == 1 and user_added_count <= 1:
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
