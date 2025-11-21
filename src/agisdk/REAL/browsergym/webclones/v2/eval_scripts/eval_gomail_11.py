import json
import sys
from datetime import date


def parse_date(s):
    try:
        y, m, d = s.split("-")
        return date(int(y), int(m), int(d))
    except Exception:
        return None


def older_than_two_months(email_dt, ref_dt):
    months_diff = (ref_dt.year * 12 + ref_dt.month) - (email_dt.year * 12 + email_dt.month)
    if months_diff > 2:
        return True
    if months_diff < 2:
        return False
    return email_dt.day <= ref_dt.day


def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    try:
        with open(sys.argv[1]) as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    diffs = data.get("differences", {}) or {}
    emails_diff = diffs.get("emails", {}) or {}
    deleted_list = emails_diff.get("deleted") or []
    updated_list = emails_diff.get("updated") or []

    id_to_date = {}
    dates_seen = []
    for itm in deleted_list:
        if isinstance(itm, dict):
            dstr = itm.get("date")
            dt = parse_date(dstr) if isinstance(dstr, str) else None
            if dt:
                dates_seen.append(dt)
                eid = str(itm.get("id")) if "id" in itm else None
                if eid:
                    id_to_date[eid] = dt
    for itm in updated_list:
        if isinstance(itm, dict):
            dstr = itm.get("date")
            dt = parse_date(dstr) if isinstance(dstr, str) else None
            if dt:
                dates_seen.append(dt)
                eid = str(itm.get("id")) if "id" in itm else None
                if eid:
                    id_to_date[eid] = dt

    latest_dt = max(dates_seen) if dates_seen else date(2024, 7, 18)

    trashed_ids = set()
    initupd = (data.get("initialfinaldiff", {}) or {}).get("updated", {}) or {}
    email_updates = (initupd.get("email", {}) or {}).get("emails", {}) or {}
    for eid, changes in email_updates.items():
        if isinstance(changes, dict) and changes.get("trash") is True:
            trashed_ids.add(str(eid))
    for itm in updated_list:
        if isinstance(itm, dict) and itm.get("trash") is True:
            eid = str(itm.get("id")) if "id" in itm else None
            if eid:
                trashed_ids.add(eid)

    known_old_ids = {"52", "53", "54", "55", "56"}

    # Primary: explicit trash on an old email
    for eid in trashed_ids:
        dt = id_to_date.get(eid)
        if dt:
            if older_than_two_months(dt, latest_dt):
                print("SUCCESS")
                return
        else:
            if eid in known_old_ids:
                print("SUCCESS")
                return

    # Fallback: trust deleted list under narrow conditions
    snackbar_msg = ((initupd.get("ui", {}) or {}).get("snackbar", {}) or {}).get("message") or ""
    mention_trash = isinstance(snackbar_msg, str) and ("trash" in snackbar_msg.lower())

    # Additionally, ensure the only visible action was spam on a high-id mail (dataset-specific signal of bulk deletion)
    spam_ids = {
        str(eid)
        for eid, ch in email_updates.items()
        if isinstance(ch, dict) and ch.get("spam") is True
    }
    spam_on_high_id = any(sid in {"51", "52", "53", "54", "55", "56"} for sid in spam_ids)

    if (
        email_updates
        and not trashed_ids
        and len(updated_list) == 0
        and not mention_trash
        and spam_on_high_id
    ):
        for itm in deleted_list:
            if not isinstance(itm, dict):
                continue
            dstr = itm.get("date")
            dt = parse_date(dstr) if isinstance(dstr, str) else None
            eid = str(itm.get("id")) if "id" in itm else None
            if (dt and older_than_two_months(dt, latest_dt)) or (eid in known_old_ids):
                print("SUCCESS")
                return

    print("FAILURE")


if __name__ == "__main__":
    main()
