import json, sys

# Strategy in code comments:
# - Load the JSON and look into initialfinaldiff.added.jobs.jobs for created/visible job postings
# - Find at least one job with title containing 'Personal Assistant' (case-insensitive)
# - Validate key fields: estimateLevelExperience == 'entry', estimateTime == 'More than 6 months',
#   and hourlyRateFrom/hourlyRateTo within 30-35 with from <= to; status should be 'published' if present.
# - If a matching job exists, print SUCCESS; otherwise print FAILURE.


def to_lower(s):
    return s.lower() if isinstance(s, str) else ""


def get_num(val):
    # Convert to float if possible, else return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.strip())
        except Exception:
            return None
    return None


def iter_job_entries(data):
    # Safely iterate over jobs in the expected path
    jobs = []
    root = data.get('initialfinaldiff', {})
    added = root.get('added', {})
    jobs_container = added.get('jobs', {})
    job_entries = jobs_container.get('jobs', {})

    # job_entries is typically a dict with index keys -> job objects
    if isinstance(job_entries, dict):
        for v in job_entries.values():
            if isinstance(v, dict):
                jobs.append(v)
    elif isinstance(job_entries, list):
        for v in job_entries:
            if isinstance(v, dict):
                jobs.append(v)

    return jobs


def job_matches(job):
    title = to_lower(job.get('title', ''))
    if 'personal assistant' not in title:
        return False

    # Experience level: must be entry
    level = to_lower(job.get('estimateLevelExperience', ''))
    if level != 'entry':
        return False

    # Duration: More than 6 months
    time = to_lower(job.get('estimateTime', ''))
    if time != 'more than 6 months':
        return False

    # Rates: within 30-35 and from <= to
    r_from = get_num(job.get('hourlyRateFrom'))
    r_to = get_num(job.get('hourlyRateTo'))
    if r_from is None or r_to is None:
        return False
    if r_from > r_to:
        return False
    if r_from < 30 or r_to > 35:
        return False

    # If status exists, ensure it's published (do not fail if missing)
    status = to_lower(job.get('status', 'published'))  # default assume published if not present
    if status and status != 'published':
        return False

    return True


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print('FAILURE')
        return

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    jobs = iter_job_entries(data)
    success = any(job_matches(j) for j in jobs)

    print('SUCCESS' if success else 'FAILURE')


if __name__ == '__main__':
    main()
