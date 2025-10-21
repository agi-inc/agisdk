import sys, json

def get_in(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

# Determine if a job post is data-related based on multiple signals
STRONG_KEYWORDS = [
    'data science', 'data analyst', 'data analysis', 'analytics',
    'machine learning', 'deep learning', 'statistical', 'statistics', 'etl',
    'data engineer', 'business intelligence', 'visualization'
]
# Single-word tokens to check carefully (as standalone or clear substring)
SINGLE_TOKENS = ['data', 'ai', 'ml', 'sql']


def is_data_related(job: dict) -> bool:
    # Category/Subcategory signals
    for key in ('category', 'subcategory'):
        val = (job.get(key) or '')
        if isinstance(val, str) and 'data' in val.lower():
            return True
    # Skills signals
    skills = job.get('skills')
    if isinstance(skills, list):
        for s in skills:
            s_low = str(s).lower()
            if 'data' in s_low:
                return True
            if any(kw in s_low for kw in ['analytics', 'data analysis', 'machine learning', 'etl', 'statistics', 'visualization', 'business intelligence']):
                return True
            # cautious match for common DS tools
            if s_low.strip() in {'sql', 'ml', 'ai', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'pytorch', 'tensorflow'}:
                return True
    # Title/Description keyword fallback (strong keywords only)
    text = ' '.join([str(job.get('title') or ''), str(job.get('description') or '')]).lower()
    if any(kw in text for kw in STRONG_KEYWORDS):
        return True
    # cautious single tokens: ensure bounded by non-letters to reduce false positives
    for token in SINGLE_TOKENS:
        idx = text.find(token)
        if idx != -1:
            left_ok = (idx == 0) or not text[idx-1].isalpha()
            right_ok = (idx + len(token) == len(text)) or not text[idx+len(token)].isalpha()
            if left_ok and right_ok:
                return True
    return False


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    removed = get_in(data, ['initialfinaldiff', 'added', 'jobs', 'removedJobPosts'], [])

    if not isinstance(removed, list) or len(removed) == 0:
        print('FAILURE')
        return

    # Success if any removed job is data-related
    for job in removed:
        if isinstance(job, dict) and is_data_related(job):
            print('SUCCESS')
            return

    print('FAILURE')

if __name__ == '__main__':
    # Strategy: Check removedJobPosts for data-related postings via category/subcategory/skills/title/description.
    # Success if at least one data-related job was removed; otherwise failure.
    main()
