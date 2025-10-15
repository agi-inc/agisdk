import json, sys

# Verification script for task:
# "I have some unread messages to reply too. If they ask anything about any time frames, tell them tomorrow."
#
# Approach:
# - Look at newly added messages authored by "Sarah Johnson" in each chat.
# - For each new reply, inspect the immediate previous message in that chat (from the updated state) to see
#   if it contains time-related cues (e.g., when, timeline, schedule a call, kick off, etc.).
# - If the previous message is time-related, the agent's reply must contain the word "tomorrow" (case-insensitive).
# - If there are zero replies overall, mark FAILURE. Otherwise, SUCCESS only if all time-related prompts were answered with a "tomorrow" reply.

import os

def safe_get(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
        if cur is None:
            return None
    return cur

try:
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception:
    # If JSON cannot be read, fail
    print("FAILURE")
    sys.exit(0)

root = data.get('initialfinaldiff') or {}
added_contacts = safe_get(root, 'added', 'messages', 'contactList')
updated_contacts = safe_get(root, 'updated', 'messages', 'contactList')

if not isinstance(added_contacts, dict):
    added_contacts = {}
if not isinstance(updated_contacts, dict):
    updated_contacts = {}

# Patterns indicating time-related asks in the immediate previous message
TIME_KEYWORDS = [
    'when would',
    'when can',
    "what's your timeline",
    'timeline',
    'schedule a call',
    'project timeline',
    'good time for a call',
    'what time',
    'when would you be able',
    'when can we',
    'tomorrow at',
    'would tomorrow work',
    'kickoff',
    'kick off',
    'set up access',
    'start the analysis',
    'time for a call'
]

def is_time_related(text: str) -> bool:
    if not text:
        return False
    s = text.lower()
    return any(key in s for key in TIME_KEYWORDS)

# Iterate over newly added replies and validate
total_replies = 0
needed_time_replies = 0
correct_time_replies = 0

for idx, added_contact in added_contacts.items():
    if not isinstance(added_contact, dict):
        continue
    added_msgs = added_contact.get('messages')
    if not isinstance(added_msgs, dict):
        continue

    # Obtain the corresponding updated contact to fetch previous message
    upd_contact = updated_contacts.get(idx, {}) if isinstance(updated_contacts, dict) else {}
    upd_msgs = upd_contact.get('messages', {}) if isinstance(upd_contact, dict) else {}

    # Determine the previous message (max numeric key in updated messages)
    prev_text = None
    if isinstance(upd_msgs, dict) and upd_msgs:
        numeric_keys = []
        for k in upd_msgs.keys():
            try:
                numeric_keys.append(int(k))
            except Exception:
                pass
        if numeric_keys:
            prev_key = str(max(numeric_keys))
            prev_msg = upd_msgs.get(prev_key, {}) if isinstance(upd_msgs.get(prev_key), dict) else {}
            prev_text = str(prev_msg.get('message', '') or '').strip()

    # Process all new messages (usually there is one, but be robust)
    for k, new_msg in added_msgs.items():
        if not isinstance(new_msg, dict):
            continue
        author = str(new_msg.get('author', '') or '')
        message_text = str(new_msg.get('message', '') or '')
        if not message_text:
            continue
        # Count only replies authored by the agent
        if author.strip().lower() != 'sarah johnson':
            continue
        total_replies += 1

        # If previous message is time-related, require 'tomorrow' mention in reply
        if is_time_related(prev_text):
            needed_time_replies += 1
            if 'tomorrow' in message_text.lower():
                correct_time_replies += 1

# Decision logic
if total_replies == 0:
    print("FAILURE")
else:
    if needed_time_replies == correct_time_replies:
        print("SUCCESS")
    else:
        print("FAILURE")
