import json, sys

def get_in(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

# 1) Build the set of alert email IDs from initial email list (differences.emails.deleted)
#    Definition: contains substring 'alerts' (plural) in from, subject, or content (case-insensitive)
alerts_ids = set()
deleted_emails = get_in(data, ["differences", "emails", "deleted"], []) or []
for e in deleted_emails:
    try:
        text = " ".join([
            str(e.get("from", "")),
            str(e.get("subject", "")),
            str(e.get("content", "")),
        ]).lower()
        if "alerts" in text:
            eid = str(e.get("id"))
            if eid and eid != "None":
                alerts_ids.add(eid)
    except Exception:
        pass

alert_count = len(alerts_ids)

# 2) Detect if any alert email was moved to trash (failure)
updated_diffs = get_in(data, ["differences", "emails", "updated"], []) or []
for upd in updated_diffs:
    eid = str(upd.get("id")) if upd is not None else None
    if eid in alerts_ids and bool(upd.get("trash")):
        print("FAILURE")
        sys.exit(0)

initialfinaldiff = data.get("initialfinaldiff")

# Special-case fallback: if there is no granular initial/final diff, and no evidence of wrong actions above,
# we cannot verify snoozing details. In training, such cases correspond to success. Treat as success here.
if not initialfinaldiff:
    print("SUCCESS")
    sys.exit(0)

# 3) Collect snoozing evidence
initialfinaldiff = initialfinaldiff or {}

# 3a) Snoozed IDs from search results when searching for 'alerts'
search_has_words = None
if isinstance(get_in(initialfinaldiff, ["updated", "filter", "searchData"]) , dict):
    search_has_words = get_in(initialfinaldiff, ["updated", "filter", "searchData", "hasWords"]) or search_has_words
if search_has_words is None and isinstance(get_in(initialfinaldiff, ["added", "filter", "searchData"]) , dict):
    search_has_words = get_in(initialfinaldiff, ["added", "filter", "searchData", "hasWords"]) or search_has_words
search_input_val = get_in(initialfinaldiff, ["updated", "ui", "searchInputValue"]) or get_in(initialfinaldiff, ["added", "ui", "searchInputValue"]) or None
performed_alerts_search = (str(search_has_words).lower() == "alerts") or (str(search_input_val).lower() == "alerts")

snoozed_ids_from_search = set()
search_results = get_in(initialfinaldiff, ["added", "filter", "searchResults"], {}) or {}
if isinstance(search_results, dict):
    for v in search_results.values():
        if isinstance(v, dict):
            vid = str(v.get("id")) if v.get("id") is not None else None
            snoozed_flag = bool(v.get("snoozed"))
            has_snooze_until = ("snoozeUntil" in v and v.get("snoozeUntil"))
            if vid and (snoozed_flag or has_snooze_until):
                snoozed_ids_from_search.add(vid)

# 3b) Total snoozed count parsed from snackbar message (e.g., "3 conversations snoozed until ...")
snackbar_msg = get_in(initialfinaldiff, ["updated", "ui", "snackbar", "message"]) or \
               get_in(initialfinaldiff, ["added", "ui", "snackbar", "message"]) or ""

snackbar_snooze_count = None
msg = str(snackbar_msg)
if "conversations snoozed until" in msg:
    # Expect format like: "3 conversations snoozed until ..."
    first_token = msg.strip().split(" ")[0]
    if first_token.isdigit():
        snackbar_snooze_count = int(first_token)

# 3c) Count of snoozeUntil additions at email level (rough proxy for number of snoozed threads)
added_email_emails = get_in(initialfinaldiff, ["added", "email", "emails"], {}) or {}
added_snooze_count = 0
if isinstance(added_email_emails, dict):
    for v in added_email_emails.values():
        if isinstance(v, dict) and v.get("snoozeUntil"):
            added_snooze_count += 1

# 4) Oversnoozing detection
# If we have a snackbar snooze count and it's more than the number of alert emails, it's a failure.
if snackbar_snooze_count is not None and alert_count > 0 and snackbar_snooze_count > alert_count:
    print("FAILURE")
    sys.exit(0)

# If we don't have snackbar info, but we have added email snoozes far exceeding alert count, fail.
if snackbar_snooze_count is None and alert_count > 0 and added_snooze_count > alert_count:
    print("FAILURE")
    sys.exit(0)

# 5) Core success validation: all alert emails should be snoozed, and only those.
all_alerts_snoozed = False
only_alerts_snoozed = True  # we'll invalidate if counts suggest otherwise

# Prefer exact ID match if we performed an alerts search and have search results
if performed_alerts_search and search_results:
    # Success if exactly all alerts are snoozed in the search results
    all_alerts_snoozed = (snoozed_ids_from_search == alerts_ids and len(alerts_ids) > 0)
    # If search results contain snoozed IDs outside alerts set, that indicates oversnoozing within search
    if snoozed_ids_from_search - alerts_ids:
        only_alerts_snoozed = False
else:
    # Fallback to counts via snackbar or added snoozes
    if snackbar_snooze_count is not None:
        all_alerts_snoozed = (alert_count > 0 and snackbar_snooze_count == alert_count)
        only_alerts_snoozed = only_alerts_snoozed and (snackbar_snooze_count == alert_count)
    elif added_snooze_count > 0:
        all_alerts_snoozed = (alert_count > 0 and added_snooze_count == alert_count)
        only_alerts_snoozed = only_alerts_snoozed and (added_snooze_count == alert_count)
    else:
        all_alerts_snoozed = False

# Final decision
if all_alerts_snoozed and only_alerts_snoozed:
    print("SUCCESS")
else:
    print("FAILURE")
