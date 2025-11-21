import json
import sys

# Verification script for: Invite someone looking for work who has experience in Python to my project.
# Strategy:
# 1) Find any message authored by "Client" that clearly contains an invitation (look for 'invite').
# 2) For the invitee (the contact), verify Python experience by either:
#    a) Their ID appears among applicants to any job whose title/skills suggest Python; OR
#    b) Their contact 'job' field contains Python-relevant keywords (python, backend, data, machine learning, ai, ml).
# 3) If at least one such invite exists, print SUCCESS; otherwise, print FAILURE.


def get_nested(dct, *keys):
    cur = dct
    for k in keys:
        if cur is None:
            return None
        cur = cur.get(k) if isinstance(cur, dict) else None
    return cur


def is_python_job(job):
    if not isinstance(job, dict):
        return False
    title = (job.get("title") or "").lower()
    skills = job.get("skills") or []
    if any(isinstance(s, str) and "python" in s.lower() for s in skills):
        return True
    if "python" in title:
        return True
    return False


def collect_python_freelancers(root):
    py_ids = set()
    # Jobs can appear under added.jobs.jobs or updated.jobs.jobs
    jobs_sources = []
    added_jobs = get_nested(root, "added", "jobs", "jobs")
    if isinstance(added_jobs, dict):
        jobs_sources.append(added_jobs)
    updated_jobs = get_nested(root, "updated", "jobs", "jobs")
    if isinstance(updated_jobs, dict):
        jobs_sources.append(updated_jobs)
    for jobs_map in jobs_sources:
        for _, job in jobs_map.items():
            if not isinstance(job, dict):
                continue
            if is_python_job(job):
                apps = job.get("applications") or []
                if isinstance(apps, list):
                    for app in apps:
                        fid = (app or {}).get("freelancerId")
                        if isinstance(fid, str) and fid:
                            py_ids.add(fid)
    return py_ids


def iter_contacts(root):
    # Contacts may appear under updated.messages.contactList and added.messages.contactList
    for section in ("updated", "added"):
        clist = get_nested(root, section, "messages", "contactList")
        if isinstance(clist, dict):
            for _, contact in clist.items():
                if isinstance(contact, dict):
                    yield contact


def extract_messages(contact):
    msgs = []
    # Primary: contact['messages'] may be dict of index->message or list
    raw = contact.get("messages")
    if isinstance(raw, dict):
        for _, v in raw.items():
            if isinstance(v, dict):
                msgs.append(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        msgs.append(item)
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                msgs.append(item)
    # Also consider lastMessage/lastMessageAuthor as a synthetic message
    lm = contact.get("lastMessage")
    lma = contact.get("lastMessageAuthor")
    if isinstance(lm, str) and isinstance(lma, str):
        msgs.append({"author": lma, "message": lm})
    return msgs


def is_invite_message(msg):
    if not isinstance(msg, dict):
        return False
    author = (msg.get("author") or "").strip()
    if author != "Client":
        return False
    text = msg.get("message") or ""
    if not isinstance(text, str):
        return False
    # Look for invitation intent
    return "invite" in text.lower()


def has_python_experience(contact, python_applicants):
    # Check by freelancerId membership from Python-related job applications
    cid = contact.get("id")
    if isinstance(cid, str) and cid in python_applicants:
        return True
    # Check by job title keywords
    job_title = contact.get("job") or ""
    jt = job_title.lower()
    keywords = ["python", "backend", "data", "machine learning", "ml", "ai"]
    return any(k in jt for k in keywords)


def main():
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    root = data.get("initialfinaldiff") or {}

    python_applicants = collect_python_freelancers(root)

    success = False
    for contact in iter_contacts(root):
        # Skip contacts that only have offer type messages without invite text
        msgs = extract_messages(contact)
        invited_here = any(is_invite_message(m) for m in msgs)
        if not invited_here:
            continue
        if has_python_experience(contact, python_applicants):
            success = True
            break

    print("SUCCESS" if success else "FAILURE")


if __name__ == "__main__":
    main()
