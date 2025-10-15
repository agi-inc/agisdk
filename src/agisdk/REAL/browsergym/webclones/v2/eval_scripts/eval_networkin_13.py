import sys, json

# Verification logic for task:
# Goal: Subscribe to newsletters (examples show success when at least one subscription is added).
# Strategy:
# - Recursively search the JSON diff for any 'subscribedNewsletters' objects.
# - Count newsletter keys whose value is True (also consider nested 'added' maps defensively).
# - If at least one true subscription is detected, print SUCCESS; else print FAILURE.


def collect_true_subscriptions(node, found):
    """Recursively collect newsletter keys marked True under any 'subscribedNewsletters' dict."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == 'subscribedNewsletters' and isinstance(v, dict):
                # Direct mappings like {"newsletter3": true}
                for nk, nv in v.items():
                    if isinstance(nv, bool) and nv is True and isinstance(nk, str):
                        found.add(nk)
                # Defensive: handle nested structure like {"added": {...}}
                added = v.get('added')
                if isinstance(added, dict):
                    for nk, nv in added.items():
                        if isinstance(nv, bool) and nv is True and isinstance(nk, str):
                            found.add(nk)
            # Recurse
            collect_true_subscriptions(v, found)
    elif isinstance(node, list):
        for item in node:
            collect_true_subscriptions(item, found)


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    found = set()
    collect_true_subscriptions(data, found)

    # Success if at least one newsletter subscription is detected in the diff
    if len(found) >= 1:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == '__main__':
    main()
