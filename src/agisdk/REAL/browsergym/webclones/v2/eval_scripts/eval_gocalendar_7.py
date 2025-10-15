import sys, json

# Verification script for GoCalendar reminder: "Add a reminder anytime on Thursday to remind me to wish my Aunt happy birthday"
# Strategy:
# 1) Find any added/updated event that includes keywords for Aunt and Birthday in title/description.
# 2) Ensure it's scheduled on a Thursday by parsing date fields (start/end/date/dateTime) and computing weekday via Zeller's congruence.
#    If no parsable dates are present, accept textual mention of "Thursday" as fallback. Print SUCCESS if a match is found, else FAILURE.


def safe_lower(s):
    return s.lower() if isinstance(s, str) else ""


def collect_events(diffs):
    events = []
    for section in ("events", "joinedEvents"):
        sec = diffs.get(section, {})
        if not isinstance(sec, dict):
            continue
        for typ in ("added", "updated"):
            v = sec.get(typ, {})
            if isinstance(v, dict):
                # values can be event dicts or lists
                for _, val in v.items():
                    if isinstance(val, dict):
                        events.append(val)
                    elif isinstance(val, list):
                        for item in val:
                            if isinstance(item, dict):
                                events.append(item)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        events.append(item)
    return events


def get_text_fields(ev):
    texts = []
    # Common title/name fields
    for k in ("title", "name", "summary", "eventTitle", "text", "subject"):
        val = ev.get(k)
        if isinstance(val, str):
            texts.append(val)
    # Description-like fields
    for k in ("description", "details", "notes", "body", "comment"):
        val = ev.get(k)
        if isinstance(val, str):
            texts.append(val)
    # Possible nested content holder
    c = ev.get("content")
    if isinstance(c, dict):
        for k in ("text", "description"):
            val = c.get(k)
            if isinstance(val, str):
                texts.append(val)
    return " ".join(texts)


def contains_keywords(text):
    t = text.lower()
    aunt_words = ["aunt", "aunty", "auntie"]
    bday_words = ["birthday", "b-day", "bday", "happy birthday"]
    if not any(w in t for w in aunt_words):
        return False
    if not any(w in t for w in bday_words):
        return False
    return True


def mentions_thursday(text):
    t = text.lower()
    if "thursday" in t:
        return True
    # cover common abbreviations
    if " thur" in " " + t or " thurs" in " " + t or " thu" in " " + t:
        return True
    return False


def extract_date_strings_from_value(val, dates):
    # Extract ISO-like YYYY-MM-DD date strings from various value forms
    if isinstance(val, str):
        s = val.strip()
        s2 = s.replace("/", "-")
        if "T" in s2:
            s2 = s2.split("T")[0]
        if len(s2) >= 10 and len(s2) >= 10 and s2[4:5] == "-" and s2[7:8] == "-":
            y, m, d = s2[:4], s2[5:7], s2[8:10]
            if y.isdigit() and m.isdigit() and d.isdigit():
                dates.add(f"{y}-{m}-{d}")
    elif isinstance(val, dict):
        # Prioritized keys
        for k in ("date", "dateTime", "start", "end", "startDate", "endDate", "startDateTime", "endDateTime", "when"):
            if k in val:
                extract_date_strings_from_value(val.get(k), dates)
        # Also scan any keys hinting at date/time
        for k, v in val.items():
            lk = k.lower()
            if any(t in lk for t in ("date", "time", "start", "end", "when", "day")):
                extract_date_strings_from_value(v, dates)
    elif isinstance(val, list):
        for item in val:
            extract_date_strings_from_value(item, dates)


def extract_dates(ev):
    dates = set()
    for k in ("start", "end", "startDate", "endDate", "startDateTime", "endDateTime", "date", "dateTime", "when"):
        if k in ev:
            extract_date_strings_from_value(ev.get(k), dates)
    # Fallback: limited recursive scan for any hints
    for k, v in ev.items():
        lk = str(k).lower()
        if any(t in lk for t in ("date", "time", "start", "end", "when", "day")):
            extract_date_strings_from_value(v, dates)
    return list(dates)


def is_thursday(date_str):
    # Zeller's congruence for Gregorian calendar
    try:
        y = int(date_str[0:4])
        m = int(date_str[5:7])
        d = int(date_str[8:10])
    except Exception:
        return False
    if m <= 2:
        m += 12
        y -= 1
    K = y % 100
    J = y // 100
    h = (d + (13 * (m + 1)) // 5 + K + K // 4 + J // 4 + 5 * J) % 7
    # h: 0=Sat, 1=Sun, 2=Mon, 3=Tue, 4=Wed, 5=Thu, 6=Fri
    return h == 5


def event_on_thursday(ev, combined_text):
    dates = extract_dates(ev)
    for dt in dates:
        if is_thursday(dt):
            return True
    if mentions_thursday(combined_text):
        return True
    return False


def verify(data):
    diffs = data.get("differences", {})
    events = collect_events(diffs)
    for ev in events:
        text = get_text_fields(ev)
        if not text:
            continue
        if contains_keywords(text) and event_on_thursday(ev, text):
            return True
    return False


def main():
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    result = verify(data)
    print("SUCCESS" if result else "FAILURE")

if __name__ == "__main__":
    main()
