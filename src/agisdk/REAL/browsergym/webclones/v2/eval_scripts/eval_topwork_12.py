import json, sys

def get_nested(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k, None)
        if cur is None:
            return None
    return cur

# Verification logic:
# - Success requires evidence of replies sent by the agent (author "Sarah Johnson").
# - Among the new replies, at least one must explicitly mention "tomorrow" (case-insensitive),
#   aligning with the instruction to respond with a time frame of tomorrow when asked.
# - Primary source: initialfinaldiff.added.messages.contactList (newly added outgoing messages)
# - Fallback: if no added messages detected, check updated contact lastMessage fields for agent replies and presence of "tomorrow".

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

added_contact_list = get_nested(data, 'initialfinaldiff', 'added', 'messages', 'contactList')
count_out = 0
count_tomorrow = 0

if isinstance(added_contact_list, dict):
    for contact_idx, contact_val in added_contact_list.items():
        msgs = contact_val.get('messages', {}) if isinstance(contact_val, dict) else {}
        if isinstance(msgs, dict):
            for msg_idx, msg_obj in msgs.items():
                if not isinstance(msg_obj, dict):
                    continue
                author = str(msg_obj.get('author', '')).strip()
                message = str(msg_obj.get('message', '')).lower()
                if author.lower() == 'sarah johnson':
                    count_out += 1
                    if 'tomorrow' in message:
                        count_tomorrow += 1

# Fallback: if no added outgoing messages found, inspect updated lastMessage fields
if count_out == 0:
    updated_contact_list = get_nested(data, 'initialfinaldiff', 'updated', 'messages', 'contactList')
    if isinstance(updated_contact_list, dict):
        for k, v in updated_contact_list.items():
            if not isinstance(v, dict):
                continue
            last_author = str(v.get('lastMessageAuthor', '')).strip().lower()
            last_msg = str(v.get('lastMessage', '')).lower()
            if last_author == 'sarah johnson' and last_msg:
                count_out += 1
                if 'tomorrow' in last_msg:
                    count_tomorrow += 1

if count_out >= 1 and count_tomorrow >= 1:
    print("SUCCESS")
else:
    print("FAILURE")
