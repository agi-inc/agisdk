import sys, json

def get_nested(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


def iter_contacts(data):
    initialfinaldiff = data.get('initialfinaldiff', {})
    for section in ('updated', 'added'):
        sec = initialfinaldiff.get(section, {})
        messages = sec.get('messages', {})
        contact_list = messages.get('contactList')
        if isinstance(contact_list, dict):
            for _, contact in contact_list.items():
                if isinstance(contact, dict):
                    yield contact


def collect_jobs(data):
    jobs_info = []
    initialfinaldiff = data.get('initialfinaldiff', {})
    for section in ('updated', 'added'):
        sec = initialfinaldiff.get(section, {})
        jobs_root = sec.get('jobs', {})
        jobs_dict = jobs_root.get('jobs', {})
        if isinstance(jobs_dict, dict):
            for _, job in jobs_dict.items():
                if isinstance(job, dict):
                    jobs_info.append(job)
    return jobs_info


def contact_has_invite(contact):
    # Check last message
    last_author = str(contact.get('lastMessageAuthor', '')).strip().lower()
    last_msg = str(contact.get('lastMessage', '')).strip().lower()
    if last_author == 'client' and ('invite' in last_msg and 'job' in last_msg):
        return True
    # Check individual messages in the thread
    msgs = contact.get('messages')
    if isinstance(msgs, dict):
        it = msgs.values()
    elif isinstance(msgs, list):
        it = msgs
    else:
        it = []
    for m in it:
        if not isinstance(m, dict):
            continue
        author = str(m.get('author', '')).strip().lower()
        text = str(m.get('message', '')).strip().lower()
        mtype = str(m.get('type', '')).strip().lower()
        # Ignore non-text offers or other types
        if mtype == 'offer':
            continue
        if author == 'client' and ('invite' in text and 'job' in text):
            return True
    return False


def contact_has_python_exp(contact, all_jobs):
    # Heuristics based on title
    title = str(contact.get('job', '')).strip().lower()
    if any(kw in title for kw in ('python', 'backend')):
        return True
    # Try to infer from applications across jobs
    cid = contact.get('id')
    for job in all_jobs:
        applications = job.get('applications', [])
        if not isinstance(applications, list):
            continue
        # Job-level hints for Python
        job_skills = [str(s).lower() for s in job.get('skills', []) if isinstance(s, (str, int, float))]
        job_title = str(job.get('title', '')).lower()
        job_desc = str(job.get('description', '')).lower()
        for app in applications:
            if not isinstance(app, dict):
                continue
            if app.get('freelancerId') == cid:
                cover = str(app.get('coverLetter', '')).lower()
                # Strong signals of Python experience
                if 'python' in cover:
                    return True
                if 'python' in job_title or 'python' in job_desc:
                    return True
                if 'python' in job_skills:
                    return True
    return False


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    contacts = list(iter_contacts(data))
    jobs = collect_jobs(data)

    success = False
    for c in contacts:
        if contact_has_invite(c) and contact_has_python_exp(c, jobs):
            success = True
            break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()