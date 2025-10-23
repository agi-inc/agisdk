import sys, json

def to_number(x):
    try:
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            # Remove currency symbols or commas if any
            s = x.strip().replace(',', '').replace('$','')
            return float(s)
    except Exception:
        return None
    return None


def iter_jobs(data):
    # Yield job dicts from possible locations in the diff structure
    if not isinstance(data, dict):
        return
    initialfinaldiff = data.get('initialfinaldiff') or {}
    # added.jobs.jobs
    added = initialfinaldiff.get('added') or {}
    jobs_added_container = (((added.get('jobs') or {}).get('jobs')) or {})
    if isinstance(jobs_added_container, dict):
        for _, job in jobs_added_container.items():
            if isinstance(job, dict):
                yield job
    # updated.jobs.jobs (if present)
    updated = initialfinaldiff.get('updated') or {}
    jobs_updated_container = (((updated.get('jobs') or {}).get('jobs')) or {})
    if isinstance(jobs_updated_container, dict):
        for _, job in jobs_updated_container.items():
            if isinstance(job, dict):
                yield job


def job_matches(job):
    # Strategy: Match title containing 'financial analyst' (case-insensitive)
    # and hourlyRateFrom >= 45 and hourlyRateTo <= 65, with from <= to.
    title = job.get('title')
    if not isinstance(title, str):
        return False
    if 'financial analyst' not in title.strip().lower():
        return False

    hr_from = to_number(job.get('hourlyRateFrom'))
    hr_to = to_number(job.get('hourlyRateTo'))
    if hr_from is None or hr_to is None:
        return False
    # Sanity: from should not exceed to
    if hr_from > hr_to:
        return False
    # Required bounds inclusive
    if hr_from < 45 or hr_to > 65:
        return False

    # Optional: if status exists, ensure it's not an obvious non-posted state
    status = job.get('status')
    if status is not None and isinstance(status, str):
        st = status.strip().lower()
        # Consider obvious non-announced states as failure
        if st in {'draft', 'archived', 'closed'}:
            return False

    return True


def main():
    if len(sys.argv) < 2:
        print('FAILURE')
        return
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    found = False
    for job in iter_jobs(data):
        if job_matches(job):
            found = True
            break

    print('SUCCESS' if found else 'FAILURE')

if __name__ == '__main__':
    main()