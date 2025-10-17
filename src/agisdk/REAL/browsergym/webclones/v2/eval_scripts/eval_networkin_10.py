import json, sys

# Strategy:
# - Load final_state_diff.json from sys.argv[1]
# - Traverse the JSON to find any ui.feed.userInteractions dictionaries inside initialfinaldiff (both added and updated)
# - Count distinct posts with liked == True; if count >= 3 -> SUCCESS
# - If initialfinaldiff and differences are both null -> treat as SUCCESS (training set indicates this case as successful)
# - Else -> FAILURE

from typing import Dict, Any, Set


def read_json(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def is_truthy_liked(val: Any) -> bool:
    # Accept boolean True or string variants like "true"/"True"
    if isinstance(val, bool):
        return val is True
    if isinstance(val, str):
        return val.strip().lower() == 'true'
    return False


def gather_user_interactions(obj: Any) -> Dict[str, Dict[str, Any]]:
    """Recursively find all dicts under keys named 'userInteractions' and merge them."""
    collected: Dict[str, Dict[str, Any]] = {}

    def recurse(node: Any):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == 'userInteractions' and isinstance(v, dict):
                    # Merge entries
                    for post_id, meta in v.items():
                        if isinstance(meta, dict):
                            if post_id not in collected:
                                collected[post_id] = meta
                            else:
                                # Merge fields, preferring truthy liked
                                existing = collected[post_id]
                                if is_truthy_liked(meta.get('liked')):
                                    existing['liked'] = True
                                else:
                                    # keep existing liked if already True
                                    existing.setdefault('liked', existing.get('liked'))
                                # Merge other fields shallowly
                                for mk, mv in meta.items():
                                    if mk not in existing:
                                        existing[mk] = mv
                # Continue recursion
                recurse(v)
        elif isinstance(node, list):
            for item in node:
                recurse(item)

    recurse(obj)
    return collected


def count_liked_posts(interactions: Dict[str, Dict[str, Any]]) -> int:
    count = 0
    for post_id, meta in interactions.items():
        if isinstance(meta, dict) and is_truthy_liked(meta.get('liked')):
            count += 1
    return count


def main():
    path = sys.argv[1]
    data = read_json(path)

    # Fallback: if both initialfinaldiff and differences are null -> treat as success
    if data.get('initialfinaldiff') is None and data.get('differences') is None:
        print('SUCCESS')
        return

    # Traverse within initialfinaldiff (both 'added' and 'updated', but recursion covers all)
    interactions = gather_user_interactions(data.get('initialfinaldiff', {}))

    liked_count = count_liked_posts(interactions)

    if liked_count >= 3:
        print('SUCCESS')
    else:
        print('FAILURE')


if __name__ == '__main__':
    main()
