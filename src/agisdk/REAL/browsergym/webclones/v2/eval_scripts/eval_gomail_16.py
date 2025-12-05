import json
import sys

# Task: Verify that a label named "Support Emails" was created in GoMail
# Strategy:
# - Load final_state_diff.json and scan the `initialfinaldiff` section for any
#   settings.customLabels entries added/updated whose 'label' equals "Support Emails" (case-insensitive, trimmed).
# - We recursively search for any 'customLabels' collections (dict or list),
#   extract their items, and check the 'label' field. If found, print SUCCESS; else FAILURE.


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def collect_labels_from_custom_labels_node(node):
    """
    Given a node that is the value of a 'customLabels' key, return all label values found within.
    The node can be a dict with numeric keys or a list of label objects.
    """
    labels = []
    if isinstance(node, dict):
        # Values may be objects representing labels
        for v in node.values():
            if isinstance(v, dict):
                lbl = v.get("label")
                if isinstance(lbl, str):
                    labels.append(lbl)
            elif isinstance(v, list):
                # In case nested list under dict
                for item in v:
                    if isinstance(item, dict):
                        lbl = item.get("label")
                        if isinstance(lbl, str):
                            labels.append(lbl)
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, dict):
                lbl = item.get("label")
                if isinstance(lbl, str):
                    labels.append(lbl)
    return labels


def recursive_find_custom_labels(root):
    """
    Recursively traverse the JSON structure to find all 'label' values under any 'customLabels' key.
    Returns a list of strings (label names).
    """
    found = []
    if isinstance(root, dict):
        for k, v in root.items():
            if k == "customLabels":
                found.extend(collect_labels_from_custom_labels_node(v))
            # Recurse into all values to be robust to structure variations
            found.extend(recursive_find_custom_labels(v))
    elif isinstance(root, list):
        for item in root:
            found.extend(recursive_find_custom_labels(item))
    return found


def has_target_label(data, target):
    # Focus primarily on initialfinaldiff where additions/updates are recorded
    if not isinstance(data, dict):
        return False
    diff_root = data.get("initialfinaldiff", {})

    # Consider both 'added' and 'updated' to be robust (some systems may record as updated)
    search_scopes = []
    if isinstance(diff_root, dict):
        for scope_key in ("added", "updated"):
            scope = diff_root.get(scope_key)
            if scope is not None:
                search_scopes.append(scope)

    # If no scopes found, quick fail
    if not search_scopes:
        return False

    target_norm = target.strip().lower()

    for scope in search_scopes:
        labels = recursive_find_custom_labels(scope)
        for lbl in labels:
            if isinstance(lbl, str) and lbl.strip().lower() == target_norm:
                return True
    return False


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return

    try:
        data = load_json(path)
    except Exception:
        print("FAILURE")
        return

    target_label = "Support Emails"
    if has_target_label(data, target_label):
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
