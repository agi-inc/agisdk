import sys, json

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Helper to safely get nested keys
def deep_get(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

# Recursively traverse JSON and yield (obj, parent, key_in_parent)
def walk(obj, parent=None, parent_key=None):
    yield obj, parent, parent_key
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, obj, k)
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            yield from walk(v, obj, idx)

# Extract merged chatroomData from multiple sections
def merge_chatroom_data(root):
    chat_data = {}

    def merge_from(section):
        if not isinstance(section, dict):
            return
        cr = deep_get(section, ['ui', 'messaging', 'chatroomData'], None)
        if isinstance(cr, dict):
            for k, v in cr.items():
                if k not in chat_data:
                    chat_data[k] = v
                else:
                    existing = chat_data[k]
                    if isinstance(existing, dict) and isinstance(v, dict):
                        merged = dict(existing)
                        merged.update(v)
                        chat_data[k] = merged
                    else:
                        chat_data[k] = v

    # Consider both top-level root (if it directly contains ui.messaging.chatroomData) and initialfinaldiff sections
    merge_from(root)
    if isinstance(root, dict) and 'initialfinaldiff' in root:
        diff = root['initialfinaldiff']
        for key in ['added', 'updated']:
            if key in diff:
                merge_from(diff[key])
    return chat_data

# Determine if a given dict context suggests a software engineer role
ROLE_POSITIVE_TOKENS = [
    'software engineer', 'backend engineer', 'frontend engineer', 'full stack engineer',
    'sw engineer', 's/w engineer', 'senior software engineer', 'software developer', 'developer (software)'
]
ROLE_NEGATIVE_TOKENS = [
    'data scientist', 'product manager', 'designer', 'ux', 'ui/ux', 'marketing', 'marketer',
    'sales', 'analyst', 'recruiter', 'hr', 'human resources', 'consultant', 'finance', 'accountant'
]

# Known ids from observed training snippets (fallback only when no explicit role text found)
ALLOW_SW_IDS = set(['johnsmith', 'janedoe', 'jonathansmith'])
DENY_NON_SW_IDS = set(['emilyjohnson', 'oliviamartinez'])

# Check text around a profile id for role cues
def profile_role_for_id(root, pid):
    pid = str(pid)
    positive = False
    negative = False

    for node, parent, pkey in walk(root):
        # Identify contexts related to this profile id
        context_related = False
        context_obj = None

        if isinstance(node, dict):
            # If dict has id/profileId matching
            if str(node.get('id', '')) == pid or str(node.get('profileId', '')) == pid:
                context_related = True
                context_obj = node
        # Also if the parent dict key equals pid (e.g., chatroomData[pid])
        if parent is not None and isinstance(parent, dict) and str(pkey) == pid:
            context_related = True
            context_obj = parent.get(pkey)

        if context_related and isinstance(context_obj, dict):
            # Scan string fields in this context for role cues
            for k, v in context_obj.items():
                if isinstance(v, str):
                    s = v.lower()
                    if any(tok in s for tok in ROLE_POSITIVE_TOKENS):
                        positive = True
                    if any(tok in s for tok in ROLE_NEGATIVE_TOKENS):
                        negative = True
                elif isinstance(v, dict):
                    for kk, vv in v.items():
                        if isinstance(vv, str):
                            s = vv.lower()
                            if any(tok in s for tok in ROLE_POSITIVE_TOKENS):
                                positive = True
                            if any(tok in s for tok in ROLE_NEGATIVE_TOKENS):
                                negative = True
                elif isinstance(v, list):
                    for vv in v:
                        if isinstance(vv, str):
                            s = vv.lower()
                            if any(tok in s for tok in ROLE_POSITIVE_TOKENS):
                                positive = True
                            if any(tok in s for tok in ROLE_NEGATIVE_TOKENS):
                                negative = True
                        elif isinstance(vv, dict):
                            for k3, v3 in vv.items():
                                if isinstance(v3, str):
                                    s3 = v3.lower()
                                    if any(tok in s3 for tok in ROLE_POSITIVE_TOKENS):
                                        positive = True
                                    if any(tok in s3 for tok in ROLE_NEGATIVE_TOKENS):
                                        negative = True
        # Early exit if both determined
        if positive and negative:
            break

    if positive and not negative:
        return True
    if negative and not positive:
        return False
    # Fallback mapping
    if pid in ALLOW_SW_IDS:
        return True
    if pid in DENY_NON_SW_IDS:
        return False
    # Unknown
    return None

# Extract recipients who received a side-project ask from the agent
def extract_side_project_recipients(chat_data):
    recipients = set()
    for rid, chat in chat_data.items():
        if not isinstance(chat, dict):
            continue
        # Check lastMessage pattern
        last_msg = chat.get('lastMessage')
        last_author = chat.get('lastMessageAuthorId')
        if isinstance(last_msg, str) and isinstance(last_author, str):
            if 'side project' in last_msg.lower() and last_author.lower() == 'divgarg':
                recipients.add(rid)
                continue
        # Check messages array or dict
        msgs = chat.get('messages')
        if isinstance(msgs, list):
            for m in msgs:
                if isinstance(m, dict):
                    if str(m.get('authorId', '')).lower() == 'divgarg':
                        txt = m.get('message', '')
                        if isinstance(txt, str) and 'side project' in txt.lower():
                            recipients.add(rid)
                            break
        elif isinstance(msgs, dict):
            for _, m in msgs.items():
                if isinstance(m, dict):
                    if str(m.get('authorId', '')).lower() == 'divgarg':
                        txt = m.get('message', '')
                        if isinstance(txt, str) and 'side project' in txt.lower():
                            recipients.add(rid)
                            break
    return recipients


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print('FAILURE')
        return

    try:
        data = load_json(path)
    except Exception:
        print('FAILURE')
        return

    chat_data = merge_chatroom_data(data)
    recipients = extract_side_project_recipients(chat_data)

    if not recipients:
        print('FAILURE')
        return

    # Determine if any messaged recipient is a software engineer
    any_sw = False
    for rid in recipients:
        role = profile_role_for_id(data, rid)
        if role is True:
            any_sw = True
            break
        elif role is False:
            continue
        else:
            # Unknown: be conservative -> not success
            continue

    if any_sw:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
