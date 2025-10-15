import sys, json
from datetime import date

def get_nested(dct, *keys):
    cur = dct
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
        if cur is None:
            return None
    return cur


def to_list_from_deleted(deleted):
    if isinstance(deleted, dict):
        # dict mapping id -> event objects
        return list(deleted.values())
    if isinstance(deleted, list):
        return deleted
    return []


def extract_start_string(ev):
    # Try common possible keys for start time
    for k in ["start", "startDate", "date", "start_time", "startTime", "startsAt"]:
        v = ev.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def is_wednesday_from_start(start_str):
    if not isinstance(start_str, str) or not start_str:
        return False
    # Use the date portion prior to 'T' to avoid timezone complications
    ds = start_str.split('T')[0]
    try:
        d = date.fromisoformat(ds)
        return d.weekday() == 2  # Monday=0, Wednesday=2
    except Exception:
        # Fallback: try to clean 'Z' or offset and extract again
        try:
            ds2 = ds.replace('Z', '')
            if ds2:
                d = date.fromisoformat(ds2)
                return d.weekday() == 2
        except Exception:
            return False
    return False


def title_matches(title):
    if not isinstance(title, str):
        return False
    return title.strip().lower() == "project sync"


def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    deleted = get_nested(data, "differences", "events", "deleted")
    deleted_events = to_list_from_deleted(deleted)

    success = False
    for ev in deleted_events:
        if not isinstance(ev, dict):
            continue
        if not title_matches(ev.get("title")):
            continue
        start_str = extract_start_string(ev)
        if is_wednesday_from_start(start_str):
            success = True
            break

    print("SUCCESS" if success else "FAILURE")

if __name__ == "__main__":
    main()
