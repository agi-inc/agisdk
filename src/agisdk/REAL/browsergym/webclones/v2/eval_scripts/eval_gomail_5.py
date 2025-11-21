import json
import sys


def normalize_str(s):
    return (s or "").strip().lower()


# Expected starred email IDs based on the dataset pattern
EXPECTED_STARRED_IDS = {"2", "6", "10", "14", "16", "21", "26", "28", "31", "37", "47", "49", "53"}

# Strategy:
# 1) Check that ONLY the expected starred emails were cleared: updated entries with trash==True must exactly match EXPECTED_STARRED_IDS.
# 2) Check that a sent email exists to alexa.richardson@example.com with subject containing 'work permit' and non-empty content.

try:
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

# Navigate to differences.emails safely
differences = data.get("differences") or {}
emails_diff = differences.get("emails") or {}
added = emails_diff.get("added") or []
updated = emails_diff.get("updated") or []

# Condition 1: Verify starred emails cleared precisely
trashed_ids = set()
for u in updated:
    # updated entries are objects like {"id": "2", "trash": true, ...}
    if isinstance(u, dict) and u.get("trash") is True:
        uid = str(u.get("id")) if "id" in u else None
        if uid is not None:
            trashed_ids.add(uid)

starred_cleared_ok = trashed_ids == EXPECTED_STARRED_IDS

# Condition 2: Verify the email to Alexa about work permit was sent
email_to_alexa_ok = False
for msg in added:
    if not isinstance(msg, dict):
        continue
    if not msg.get("sent"):
        continue
    # recipients
    to_list = msg.get("to") or []
    to_list_norm = [normalize_str(x) for x in to_list if isinstance(x, str)]
    if "alexa.richardson@example.com" not in to_list_norm:
        continue
    # subject contains 'work permit'
    subject_ok = "work permit" in normalize_str(msg.get("subject"))
    # content non-empty (string with non-whitespace after strip)
    content = msg.get("content")
    content_ok = isinstance(content, str) and len(content.strip()) > 0
    if subject_ok and content_ok:
        email_to_alexa_ok = True
        break

if starred_cleared_ok and email_to_alexa_ok:
    print("SUCCESS")
else:
    print("FAILURE")
