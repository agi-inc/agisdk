import json, sys, re

def find_post_dynamic_maps(node):
    """Recursively find all dicts that look like postDynamicData maps (id -> post dict)."""
    found = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == 'postDynamicData' and isinstance(v, dict):
                found.append(v)
            else:
                found.extend(find_post_dynamic_maps(v))
    elif isinstance(node, list):
        for item in node:
            found.extend(find_post_dynamic_maps(item))
    return found


def text_mentions_summer_internship(text):
    if not isinstance(text, str):
        return False
    s = text.lower()
    if 'summer' not in s:
        return False
    # match intern, internship, interned, interning, etc.
    return re.search(r"\bintern\w*", s) is not None


def main():
    # Strategy: Look for newly added posts in added.ui.feed.postDynamicData.
    # Success if any added post is a self-post and its description mentions both "summer" and an intern* term.
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    initialfinaldiff = data.get('initialfinaldiff', {})
    added = initialfinaldiff.get('added', {})

    # Collect candidate posts only from the 'added' section to ensure they were created in this run.
    post_maps = find_post_dynamic_maps(added)

    success = False
    for pm in post_maps:
        for pid, post in pm.items():
            if not isinstance(post, dict):
                continue
            desc = post.get('description')
            ptype = post.get('type')
            # Require self-post to ensure it's a user-created post
            if ptype != 'self-post':
                continue
            if text_mentions_summer_internship(desc):
                success = True
                break
        if success:
            break

    print("SUCCESS" if success else "FAILURE")

if __name__ == "__main__":
    main()
